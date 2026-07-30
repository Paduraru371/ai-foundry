from __future__ import annotations

import unittest

from backend.core.token_usage import count_text, usage_details


class TokenUsageTests(unittest.TestCase):
    def test_counts_non_empty_text(self) -> None:
        self.assertGreater(count_text("A short prompt"), 0)

    def test_estimates_gpt5_mini_input_and_output_cost_separately(self) -> None:
        usage = usage_details(
            provider="azure",
            model="gpt-5-mini",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            cached_input_tokens=100_000,
            estimated_prompt_tokens=999_000,
            estimated_max_completion_tokens=2_500,
        )

        self.assertAlmostEqual(usage["input_cost_usd"], 0.2275)
        self.assertAlmostEqual(usage["output_cost_usd"], 2.0)
        self.assertAlmostEqual(usage["estimated_cost_usd"], 2.2275)
        self.assertEqual(usage["total_tokens"], 2_000_000)

    def test_non_target_model_does_not_claim_azure_cost(self) -> None:
        usage = usage_details(
            provider="anthropic",
            model="claude",
            prompt_tokens=100,
            completion_tokens=20,
            estimated_prompt_tokens=100,
            estimated_max_completion_tokens=100,
        )

        self.assertIsNone(usage["estimated_cost_usd"])


if __name__ == "__main__":
    unittest.main()
