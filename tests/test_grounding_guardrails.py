from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.core.config import settings
from backend.core.llm import ChatResult
from backend.services import grounding_guardrails


CHUNKS = [
    {
        "source": "documents.md",
        "text": "Pentru deschiderea contului este necesar actul de identitate.",
    },
    {
        "source": "verification.md",
        "text": "Identitatea clientului este verificată înainte de activare.",
    },
]
HANDOFF = "Cazul trebuie confirmat de un angajat al băncii."


class _FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    def chat(self, **_kwargs) -> ChatResult:
        return ChatResult(
            text=self.text,
            provider="azure",
            model="gpt-5-mini",
            prompt_tokens=100,
            completion_tokens=20,
        )


class _CapturingLLM(_FakeLLM):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.kwargs = {}

    def chat(self, **kwargs) -> ChatResult:
        self.kwargs = kwargs
        return super().chat(**kwargs)


class GroundingGuardrailTests(unittest.TestCase):
    def _review(self, payload: str):
        with patch.object(
            grounding_guardrails,
            "get_llm",
            return_value=_FakeLLM(payload),
        ):
            return grounding_guardrails.review(
                "Care sunt documentele?",
                "Este necesar actul de identitate. [1]",
                CHUNKS,
                HANDOFF,
            )

    def test_pass_preserves_grounded_answer(self) -> None:
        review = self._review(
            '{"action":"pass","reason":"entailed","unsupported_claims":[]}'
        )

        self.assertEqual(review.answer, "Este necesar actul de identitate. [1]")
        self.assertEqual(review.details["status"], "passed")
        self.assertTrue(review.details["audited"])
        self.assertIsNotNone(review.result)

    def test_auditor_forces_compact_json_with_minimal_reasoning(self) -> None:
        llm = _CapturingLLM(
            '{"action":"pass","reason":"entailed","unsupported_claims":[]}'
        )
        with patch.object(grounding_guardrails, "get_llm", return_value=llm):
            grounding_guardrails.review(
                "Care sunt documentele?",
                "Este necesar actul de identitate. [1]",
                CHUNKS,
                HANDOFF,
            )

        self.assertEqual(llm.kwargs["extras"]["reasoning_effort"], "minimal")
        self.assertEqual(
            llm.kwargs["extras"]["response_format"],
            {"type": "json_object"},
        )

    def test_valid_rewrite_replaces_only_the_answer(self) -> None:
        review = self._review(
            '{"action":"rewrite","answer":"- Act de identitate. [1]",'
            '"reason":"removed_extra_claim","unsupported_claims":["taxă"]}'
        )

        self.assertEqual(review.answer, "- Act de identitate. [1]")
        self.assertEqual(review.details["status"], "passed")
        self.assertEqual(review.details["action"], "rewrite")
        self.assertEqual(review.details["unsupported_claims"], ["taxă"])

    def test_invalid_rewrite_preserves_answer_when_fail_open(self) -> None:
        review = self._review(
            '{"action":"rewrite","answer":"Este necesar un formular special. [9]",'
            '"reason":"rewrite","unsupported_claims":[]}'
        )

        self.assertEqual(review.answer, "Este necesar actul de identitate. [1]")
        self.assertEqual(review.details["status"], "audit_failed")
        self.assertEqual(
            review.details["reason"],
            "auditor_rewrite_failed_validation",
        )

    def test_refusal_action_uses_controlled_handoff(self) -> None:
        review = self._review(
            '{"action":"regulated_refusal","reason":"individual_kyc_decision",'
            '"unsupported_claims":[]}'
        )

        self.assertEqual(review.answer, HANDOFF)
        self.assertEqual(review.details["status"], "regulated_refusal")

    def test_malformed_auditor_output_fails_open(self) -> None:
        review = self._review("not-json")

        self.assertEqual(review.answer, "Este necesar actul de identitate. [1]")
        self.assertEqual(review.details["status"], "audit_failed")
        self.assertEqual(review.details["reason"], "auditor_invalid_output")

    def test_auditor_failure_is_reported_and_fails_open(self) -> None:
        with patch.object(
            grounding_guardrails,
            "get_llm",
            side_effect=RuntimeError("offline"),
        ):
            review = grounding_guardrails.review(
                "Care sunt documentele?",
                "Este necesar actul de identitate. [1]",
                CHUNKS,
                HANDOFF,
            )

        self.assertEqual(review.answer, "Este necesar actul de identitate. [1]")
        self.assertEqual(review.details["status"], "audit_failed")
        self.assertEqual(review.details["reason"], "auditor_unavailable")

    def test_fail_closed_remains_available_as_an_option(self) -> None:
        with (
            patch.object(settings, "grounding_guardrail_fail_closed", True),
            patch.object(
                grounding_guardrails,
                "get_llm",
                side_effect=RuntimeError("offline"),
            ),
        ):
            review = grounding_guardrails.review(
                "Care sunt documentele?",
                "Este necesar actul de identitate. [1]",
                CHUNKS,
                HANDOFF,
            )

        self.assertEqual(review.answer, HANDOFF)
        self.assertEqual(review.details["status"], "handoff")
        self.assertTrue(review.details["fail_closed"])


if __name__ == "__main__":
    unittest.main()
