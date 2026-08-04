from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend.agents.local_agent import AgentReply
from backend.agents.persona import load_persona
from backend.api.routers.generation import (
    _analysis_task,
    _apply_grounding_guardrail,
    _retrieval_queries,
    _unsupported_answer,
    ask,
    generation_cancel,
)
from backend.schemas import AskRequest
from backend.memory.store import SessionStore


class GenerationOptionTests(unittest.TestCase):
    def test_cancelled_generation_stops_before_model_and_is_not_persisted(self) -> None:
        generation_id = "cancel-test-generation"
        generation_cancel(generation_id)

        with tempfile.TemporaryDirectory() as temporary:
            store = SessionStore(Path(temporary) / "sessions.sqlite3")
            session_id = store.create()["session_id"]
            with (
                patch("backend.memory.service.session_store", store),
                patch("backend.api.routers.generation.local_agent.run") as run,
                self.assertRaises(HTTPException) as raised,
            ):
                ask(AskRequest(
                    question="Do not finish this answer",
                    use_rag=False,
                    session_id=session_id,
                    generation_id=generation_id,
                ))

            detail = store.get(session_id)

        self.assertEqual(raised.exception.status_code, 409)
        run.assert_not_called()
        self.assertEqual(detail["messages"], [])

    def test_document_is_delimited_and_named(self) -> None:
        task = _analysis_task(AskRequest(
            question="Assess the risks",
            document_text="Risk register contents",
            document_name="risks.docx",
            response_format="technical_report",
        ))

        self.assertIn("risks.docx", task)
        self.assertIn("<document>", task)
        self.assertIn("technical report", task)

    def test_attached_questions_are_used_as_individual_retrieval_queries(self) -> None:
        queries = _retrieval_queries(
            "Răspunde la întrebările din PDF.",
            [],
            (
                "1) Care sunt documentele necesare?\n"
                "2) Ce verificări se fac înainte de activare?\n"
                "3) Care sunt etapele onboardingului digital?"
            ),
        )

        self.assertEqual(len(queries), 4)
        self.assertIn("Care sunt documentele necesare?", queries)
        self.assertIn("Ce verificări se fac înainte de activare?", queries)

    def test_document_generation_prompt_forbids_confirmation_loop(self) -> None:
        task = _analysis_task(AskRequest(
            question="Generează un PDF cu răspunsuri în bullet points.",
            document_text="1) Care sunt documentele necesare?",
            document_name="questions.pdf",
            response_format="bullet_list",
            delivery="document",
        ))

        self.assertIn("ATTACHED-QUESTION MODE", task)
        self.assertIn("DOCUMENT DELIVERY", task)
        self.assertIn("Do not ask the user to confirm", task)

    def test_speech_delivery_prompt_forbids_tts_disclaimer(self) -> None:
        task = _analysis_task(AskRequest(
            question="Răspunde vocal.",
            delivery="speech",
        ))

        self.assertIn("SPEECH DELIVERY", task)
        self.assertIn("Never say that you cannot create or play audio", task)

    def test_json_format_demands_json_only(self) -> None:
        task = _analysis_task(AskRequest(
            question="Summarize",
            response_format="json",
        ))

        self.assertIn("valid JSON only", task)

    def test_motrun_unsupported_answer_uses_safe_human_handoff(self) -> None:
        answer = _unsupported_answer(
            "Care sunt documentele pentru acest caz?",
            "motrun-onboarding",
            0.7,
        )
        prompt = load_persona("motrun-onboarding").system_prompt(grounded=True)

        self.assertIn("sucursală", answer)
        self.assertNotIn("not found", answer.casefold())
        self.assertIn("Never invent a telephone number", prompt)
        self.assertIn("Un scor de similaritate nu este dovadă factuală", prompt)
        self.assertIn("motrun-onboarding.md", str(
            load_persona("motrun-onboarding").summary()["policy_file"]
        ))
        self.assertNotIn("say so explicitly", prompt)

    def test_motrun_grounding_guardrail_accepts_valid_citations(self) -> None:
        answer, result = _apply_grounding_guardrail(
            "Care sunt documentele?",
            "- Este necesar actul de identitate. [1]",
            "motrun-onboarding",
            2,
        )

        self.assertIn("actul de identitate", answer)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["citations"], [1])

    def test_motrun_guardrail_reviews_missing_but_rejects_invalid_citations(self) -> None:
        missing_answer, missing = _apply_grounding_guardrail(
            "Care sunt documentele?",
            "Este necesar un document special.",
            "motrun-onboarding",
            2,
        )
        invalid_answer, invalid = _apply_grounding_guardrail(
            "Care sunt documentele?",
            "Este necesar actul de identitate. [7]",
            "motrun-onboarding",
            2,
        )

        self.assertEqual(missing_answer, "Este necesar un document special.")
        self.assertEqual(missing["status"], "review_required")
        self.assertEqual(missing["reason"], "missing_grounding_citations")
        self.assertIn("coleg al băncii", invalid_answer)
        self.assertEqual(invalid["invalid_citations"], [7])

    def test_motrun_grounding_guardrail_allows_managed_handoff(self) -> None:
        answer, result = _apply_grounding_guardrail(
            "Care sunt documentele?",
            "Cazul trebuie confirmat de un angajat al băncii.",
            "motrun-onboarding",
            2,
        )

        self.assertEqual(answer, "Cazul trebuie confirmat de un angajat al băncii.")
        self.assertEqual(result["reason"], "managed_handoff")

    def test_recent_conversation_is_included_before_current_message(self) -> None:
        task = _analysis_task(AskRequest(
            question="What should I do next?",
            history=[
                {"role": "user", "content": "Review the migration plan."},
                {"role": "assistant", "content": "The database step is risky."},
            ],
        ))

        self.assertIn("CONVERSATION HISTORY", task)
        self.assertIn("same language as the current question", task)
        self.assertIn("The database step is risky.", task)
        self.assertLess(
            task.index("CONVERSATION HISTORY"),
            task.index("CURRENT USER MESSAGE"),
        )

    @patch("backend.api.routers.generation.local_agent.run")
    def test_ask_returns_usage_cost_and_selected_format(self, run) -> None:
        run.return_value = AgentReply(
            text='{"answer": "ok"}',
            mode="local",
            persona="default",
            system_prompt="system",
            prompt_sent="user",
            provider="azure",
            model="gpt-5-mini",
            prompt_tokens=1000,
            completion_tokens=100,
        )

        response = ask(AskRequest(
            question="Summarize",
            use_rag=False,
            agent="default",
            agent_mode="local",
            response_format="json",
        ))

        self.assertEqual(response.response_format, "json")
        self.assertEqual(response.usage.total_tokens, 1100)
        self.assertIsNotNone(response.usage.estimated_cost_usd)
        self.assertIn("answer", response.usage.phases)

    @patch("backend.api.routers.generation.local_agent.run")
    def test_empty_model_answer_is_reported_honestly(self, run) -> None:
        run.return_value = AgentReply(
            text="   ",
            mode="local",
            persona="default",
            system_prompt="system",
            prompt_sent="user",
            provider="azure",
            model="gpt-5-mini",
            prompt_tokens=10,
            completion_tokens=0,
        )

        response = ask(AskRequest(
            question="Can you answer?",
            use_rag=False,
            agent="default",
        ))

        self.assertIn("returned no text", response.answer)

    @patch("backend.api.routers.generation.local_agent.run")
    def test_ask_persists_session_history_and_usage(self, run) -> None:
        run.return_value = AgentReply(
            text="Persistent answer",
            mode="local",
            persona="default",
            system_prompt="system",
            prompt_sent="user",
            provider="azure",
            model="gpt-5-mini",
            prompt_tokens=120,
            completion_tokens=30,
        )
        with tempfile.TemporaryDirectory() as temporary:
            store = SessionStore(Path(temporary) / "sessions.sqlite3")
            session_id = store.create()["session_id"]
            with patch("backend.memory.service.session_store", store):
                response = ask(AskRequest(
                    question="Remember this preference",
                    use_rag=False,
                    agent="default",
                    session_id=session_id,
                ))
                detail = store.get(session_id)

        self.assertEqual(response.session_id, session_id)
        self.assertEqual(
            [message["role"] for message in detail["messages"]],
            ["user", "assistant"],
        )
        self.assertEqual(
            detail["messages"][-1]["metadata"]["usage"]["total_tokens"],
            150,
        )
        self.assertIn("memory", detail["messages"][-1]["metadata"])
        self.assertEqual(
            detail["messages"][-1]["metadata"]["memory"]["shared_sessions_used"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
