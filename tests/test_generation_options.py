from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.agents.local_agent import AgentReply
from backend.api.routers.generation import _analysis_task, ask
from backend.schemas import AskRequest
from backend.memory.store import SessionStore


class GenerationOptionTests(unittest.TestCase):
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

    def test_json_format_demands_json_only(self) -> None:
        task = _analysis_task(AskRequest(
            question="Summarize",
            response_format="json",
        ))

        self.assertIn("valid JSON only", task)

    def test_recent_conversation_is_included_before_current_message(self) -> None:
        task = _analysis_task(AskRequest(
            question="What should I do next?",
            history=[
                {"role": "user", "content": "Review the migration plan."},
                {"role": "assistant", "content": "The database step is risky."},
            ],
        ))

        self.assertIn("CONVERSATION HISTORY", task)
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


if __name__ == "__main__":
    unittest.main()
