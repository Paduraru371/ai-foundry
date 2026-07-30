"""Token counting and transparent Azure GPT-5-mini cost estimates."""
from __future__ import annotations

import math
from typing import Iterable

from .config import settings

try:
    import tiktoken
except ImportError:  # pragma: no cover - requirements install it in production
    tiktoken = None


def count_text(text: str) -> int:
    """Count with the GPT-5-family tokenizer, falling back to chars/4."""
    if not text:
        return 0
    if tiktoken is not None:
        try:
            return len(tiktoken.get_encoding("o200k_base").encode(text))
        except Exception:
            pass
    return max(1, math.ceil(len(text) / 4))


def estimate_messages(parts: Iterable[str]) -> int:
    """Approximate chat framing plus the supplied system/user content."""
    values = list(parts)
    return 2 + sum(4 + count_text(value) for value in values)


def usage_details(
    *,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    cached_input_tokens: int | None = None,
    reasoning_tokens: int | None = None,
    estimated_prompt_tokens: int,
    estimated_max_completion_tokens: int,
) -> dict:
    actual_input = prompt_tokens if prompt_tokens is not None else estimated_prompt_tokens
    actual_output = completion_tokens
    cached = min(actual_input, max(0, cached_input_tokens or 0))
    billable_input = max(0, actual_input - cached)

    is_azure_gpt5_mini = (
        provider in {"azure", "azure-foundry-agent"}
        and model.lower().startswith("gpt-5-mini")
    )
    input_rate = settings.azure_gpt5_mini_input_price if is_azure_gpt5_mini else None
    cached_rate = (
        settings.azure_gpt5_mini_cached_input_price if is_azure_gpt5_mini else None
    )
    output_rate = settings.azure_gpt5_mini_output_price if is_azure_gpt5_mini else None

    input_cost = (
        (billable_input * input_rate + cached * cached_rate) / 1_000_000
        if input_rate is not None and cached_rate is not None
        else None
    )
    output_cost = (
        actual_output * output_rate / 1_000_000
        if actual_output is not None and output_rate is not None
        else None
    )
    total_cost = (
        input_cost + output_cost
        if input_cost is not None and output_cost is not None
        else None
    )

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        ),
        "cached_input_tokens": cached_input_tokens,
        "reasoning_tokens": reasoning_tokens,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "estimated_max_completion_tokens": estimated_max_completion_tokens,
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "estimated_cost_usd": total_cost,
        "pricing": {
            "model": "gpt-5-mini" if is_azure_gpt5_mini else model,
            "currency": "USD",
            "unit": "1M tokens",
            "input": input_rate,
            "cached_input": cached_rate,
            "output": output_rate,
            "is_estimate": True,
        },
    }
