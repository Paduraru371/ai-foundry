"""LLM re-ranking for /ask, with a deterministic retrieval-order fallback."""
from __future__ import annotations

import json
import re

from .llm import get_llm

RANKING_ARRAY = re.compile(r"\[[\d,\s]*\]")
SYSTEM_PROMPT = (
    "You are a retrieval re-ranker. Select only passages that help answer the "
    "question. Return one JSON array of passage numbers in best-first order, "
    "with no explanation."
)


def ranking_prompt(question: str, hits: list[dict], top_k: int) -> str:
    passages = "\n\n".join(
        f"[{index}] source={hit.get('source', 'unknown')} "
        f"cosine={hit.get('score', 0)}\n{hit.get('text', '')[:1500]}"
        for index, hit in enumerate(hits, start=1)
    )
    return (
        f"QUESTION:\n{question}\n\n"
        f"Choose at most {top_k} passages from:\n\n{passages}"
    )


def parse_ranking(text: str, hit_count: int, top_k: int) -> list[int]:
    """Parse a model's one-based passage numbers into zero-based indexes."""
    match = RANKING_ARRAY.search(text)
    if not match:
        return []
    try:
        values = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    result: list[int] = []
    for value in values:
        if not isinstance(value, int):
            continue
        index = value - 1
        if 0 <= index < hit_count and index not in result:
            result.append(index)
        if len(result) == top_k:
            break
    return result


def rerank_with_llm(
    question: str,
    hits: list[dict],
    top_k: int,
    *,
    llm=None,
) -> list[dict]:
    """Ask the configured model to choose the final context passages.

    Provider errors or malformed model output fall back to the already improved
    deterministic order, so retrieval remains available.
    """
    if len(hits) <= top_k:
        return hits
    try:
        model = llm or get_llm()
        result = model.chat(
            system=SYSTEM_PROMPT,
            user=ranking_prompt(question, hits, top_k),
            temperature=0,
            max_tokens=150,
        )
        indexes = parse_ranking(result.text, len(hits), top_k)
    except Exception:
        indexes = []
    if not indexes:
        return hits[:top_k]
    selected = [hits[index] for index in indexes]
    if len(selected) < top_k:
        selected_ids = {item["id"] for item in selected}
        selected.extend(
            hit for hit in hits
            if hit["id"] not in selected_ids
        )
    return selected[:top_k]
