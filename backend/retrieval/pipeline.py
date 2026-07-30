"""Post-retrieval quality controls: thresholding, re-ranking, and diversity."""
from __future__ import annotations

import re

TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "of", "on", "or", "the", "to",
    "what", "when", "where", "which", "who", "why", "with",
    "ai", "ale", "ca", "care", "ce", "cu", "de", "din", "este", "la",
    "o", "pe", "pentru", "sau", "si", "sunt", "un",
}


def content_tokens(text: str) -> set[str]:
    """Return normalized content words used by the transparent lexical scorer."""
    return {
        token.casefold()
        for token in TOKEN.findall(text)
        if len(token) > 1 and token.casefold() not in STOP_WORDS
    }


def lexical_coverage(query: str, text: str) -> float:
    """Fraction of meaningful query terms present in a candidate passage."""
    query_terms = content_tokens(query)
    if not query_terms:
        return 0.0
    return len(query_terms & content_tokens(text)) / len(query_terms)


def rerank(
    query: str,
    hits: list[dict],
    *,
    vector_weight: float = 0.75,
) -> list[dict]:
    """Re-rank candidates using cosine similarity plus exact term coverage.

    Cosine similarity remains the dominant signal. The lexical component helps
    exact policy terms, dates, amounts, and product names that embeddings can
    otherwise order too loosely.
    """
    ranked: list[dict] = []
    for hit in hits:
        item = dict(hit)
        lexical_score = lexical_coverage(query, item.get("text", ""))
        cosine_score = max(-1.0, min(1.0, float(item.get("score", 0.0))))
        normalized_cosine = (cosine_score + 1.0) / 2.0
        item["lexical_score"] = round(lexical_score, 4)
        item["rerank_score"] = round(
            vector_weight * normalized_cosine
            + (1.0 - vector_weight) * lexical_score,
            4,
        )
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda hit: (hit["rerank_score"], hit.get("score", 0.0)),
        reverse=True,
    )


def text_similarity(left: str, right: str) -> float:
    """Jaccard similarity used to identify substantially repeated passages."""
    left_tokens = content_tokens(left)
    right_tokens = content_tokens(right)
    union = left_tokens | right_tokens
    if not union:
        return 1.0 if left.strip() == right.strip() else 0.0
    return len(left_tokens & right_tokens) / len(union)


def diversify(
    hits: list[dict],
    top_k: int,
    *,
    duplicate_threshold: float = 0.82,
    diversity_penalty: float = 0.15,
    max_per_source: int = 2,
) -> list[dict]:
    """Select relevant but non-repetitive passages with a small MMR-style penalty."""
    remaining = [dict(hit) for hit in hits]
    selected: list[dict] = []
    while remaining and len(selected) < top_k:
        candidates: list[tuple[float, dict]] = []
        for hit in remaining:
            source = str(hit.get("source") or "")
            same_source = sum(
                str(chosen.get("source") or "") == source
                for chosen in selected
            )
            if source and same_source >= max_per_source:
                continue
            similarities = [
                text_similarity(hit.get("text", ""), chosen.get("text", ""))
                for chosen in selected
            ]
            nearest = max(similarities, default=0.0)
            if nearest >= duplicate_threshold:
                continue
            quality = float(hit.get("rerank_score", hit.get("score", 0.0)))
            source_penalty = 0.04 * same_source
            candidates.append((
                quality - diversity_penalty * nearest - source_penalty,
                hit,
            ))
        if not candidates:
            break
        _, best = max(
            candidates,
            key=lambda pair: (
                pair[0],
                pair[1].get("rerank_score", pair[1].get("score", 0.0)),
            ),
        )
        selected.append(best)
        remaining.remove(best)
    return selected


def improve_retrieval(
    query: str,
    hits: list[dict],
    top_k: int,
    *,
    min_score: float,
    vector_weight: float = 0.75,
    duplicate_threshold: float = 0.82,
    max_per_source: int = 2,
) -> list[dict]:
    """Apply the three Part 5 improvements in a stable, testable pipeline."""
    relevant = [
        hit for hit in hits if float(hit.get("score", -1.0)) >= min_score
    ]
    ranked = rerank(query, relevant, vector_weight=vector_weight)
    return diversify(
        ranked,
        top_k,
        duplicate_threshold=duplicate_threshold,
        max_per_source=max_per_source,
    )
