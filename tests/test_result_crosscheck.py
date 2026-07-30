from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.evaluation.crosscheck import (
    evaluate_retrieval,
    judge_answer_with_llm,
    semantic_answer_check,
)
from backend.retrieval.reranker import rerank_with_llm


class _KeywordEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            lowered = text.casefold()
            if "identity" in lowered or "document" in lowered:
                result.append([1.0, 0.0])
            else:
                result.append([0.0, 1.0])
        return result


class ResultCrosscheckTests(unittest.TestCase):
    def test_retrieval_metrics_report_hit_at_k_and_mrr(self) -> None:
        result = evaluate_retrieval([
            {
                "id": "one",
                "question": "documents",
                "expected_sources": ["10_required_company_documents"],
                "hits": [
                    {"source": "other.md"},
                    {"source": "10_required_company_documents.md"},
                ],
            },
            {
                "id": "two",
                "question": "fees",
                "expected_sources": ["13_business_onboarding_fees_2026"],
                "hits": [{"source": "unrelated.md"}],
            },
        ])

        self.assertEqual(result["hit_at_k"], 0.5)
        self.assertEqual(result["mrr"], 0.25)
        self.assertEqual(result["failed_case_ids"], ["two"])

    def test_semantic_check_finds_unsupported_claim(self) -> None:
        result = semantic_answer_check(
            "Which identity document is needed?",
            "An identity document is needed. The weather is warm.",
            ["The customer supplies an identity document."],
            embedder=_KeywordEmbedder(),
            min_question_evidence=0.5,
            min_claim_evidence=0.5,
        )

        self.assertFalse(result["passed"])
        self.assertFalse(result["claims"][1]["passed"])

    def test_llm_judge_validates_strict_json(self) -> None:
        class Judge:
            def chat(self, **_kwargs):
                return SimpleNamespace(text=(
                    '{"passed":true,"relevance":1,"groundedness":0.95,'
                    '"completeness":0.9,"refusal_correct":true,'
                    '"reason":"supported","unsupported_claims":[]}'
                ))

        result = judge_answer_with_llm(
            "Which document?",
            "Identity document. [1]",
            ["An identity document is required."],
            llm=Judge(),
        )

        self.assertTrue(result["available"])
        self.assertTrue(result["passed"])

    def test_llm_reranker_does_not_fill_unselected_slots(self) -> None:
        class Reranker:
            def chat(self, **_kwargs):
                return SimpleNamespace(text="[2]")

        hits = [
            {"id": "a", "text": "weak", "source": "a", "score": 0.8},
            {"id": "b", "text": "relevant", "source": "b", "score": 0.7},
            {"id": "c", "text": "weak", "source": "c", "score": 0.6},
        ]
        selected = rerank_with_llm(
            "question",
            hits,
            top_k=2,
            llm=Reranker(),
        )

        self.assertEqual([hit["id"] for hit in selected], ["b"])

    def test_llm_reranker_can_reject_all_candidates(self) -> None:
        class Reranker:
            def chat(self, **_kwargs):
                return SimpleNamespace(text="[]")

        selected = rerank_with_llm(
            "unrelated question",
            [
                {"id": "a", "text": "weak", "source": "a", "score": 0.4},
                {"id": "b", "text": "weak", "source": "b", "score": 0.3},
            ],
            top_k=1,
            llm=Reranker(),
        )

        self.assertEqual(selected, [])


if __name__ == "__main__":
    unittest.main()
