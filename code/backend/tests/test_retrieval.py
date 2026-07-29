from __future__ import annotations

import unittest
from unittest.mock import patch

from app.retrieval import diversify, improve_retrieval, rerank
from app.reranker import parse_ranking, rerank_with_llm
from app.routers.generation import ask
from app.schema_agents import AskRequest


def hit(identifier: str, score: float, text: str) -> dict:
    return {
        "id": identifier,
        "score": score,
        "text": text,
        "index": 0,
        "strategy": "heading",
        "source": identifier,
    }


class RetrievalImprovementTests(unittest.TestCase):
    def test_score_threshold_removes_weak_hits(self) -> None:
        hits = [
            hit("relevant", 0.61, "Personal onboarding costs 10 lei."),
            hit("weak", 0.29, "The weather is warm."),
        ]

        result = improve_retrieval(
            "personal onboarding fee",
            hits,
            top_k=3,
            min_score=0.30,
        )

        self.assertEqual([item["id"] for item in result], ["relevant"])

    def test_reranking_can_promote_exact_policy_terms(self) -> None:
        hits = [
            hit("semantic-only", 0.60, "General account information."),
            hit("exact-terms", 0.58, "The business onboarding fee is 50 lei."),
        ]

        result = rerank("business onboarding fee", hits)

        self.assertEqual(result[0]["id"], "exact-terms")
        self.assertGreater(
            result[0]["rerank_score"],
            result[1]["rerank_score"],
        )

    def test_diversity_removes_near_duplicate_passages(self) -> None:
        hits = rerank("application expiry", [
            hit("first", 0.80, "An incomplete application expires after 30 days."),
            hit("duplicate", 0.79, "An incomplete application expires after 30 days."),
            hit("different", 0.70, "A rejected application may be submitted again."),
        ])

        result = diversify(hits, top_k=3)

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["id"] for item in result},
            {"first", "different"},
        )

    def test_llm_reranker_uses_model_order(self) -> None:
        class FakeResult:
            text = "[2, 1]"

        class FakeLLM:
            def chat(self, **_kwargs):
                return FakeResult()

        hits = [
            hit("first", 0.80, "General application information."),
            hit("second", 0.75, "The application expires after 30 days."),
            hit("third", 0.70, "Complaints can be submitted online."),
        ]

        result = rerank_with_llm(
            "When does the application expire?",
            hits,
            top_k=2,
            llm=FakeLLM(),
        )

        self.assertEqual([item["id"] for item in result], ["second", "first"])
        self.assertEqual(parse_ranking("answer: [3, 1]", 3, 2), [2, 0])

    @patch("app.routers.generation.local_agent.run")
    @patch("app.routers.generation.retrieve", return_value=[])
    @patch("app.routers.generation.store.info", return_value={"exists": True})
    @patch("app.routers.generation.require_qdrant")
    def test_ask_stops_before_llm_when_threshold_removes_everything(
        self,
        _require_qdrant,
        _store_info,
        _retrieve,
        agent_run,
    ) -> None:
        response = ask(AskRequest(
            question="What is the weather in Cluj?",
            use_rag=True,
            min_score=0.90,
            agent="default",
        ))

        self.assertEqual(response.provider, "retrieval")
        self.assertEqual(response.retrieved, [])
        self.assertIn("Nothing relevant", response.answer)
        agent_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
