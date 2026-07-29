"""Dispatcher for chunking strategies.

Basic algorithms live in ``core`` and Markdown hierarchy handling in ``markdown``.
"""
from __future__ import annotations

from .core import (
    EmbedFn,
    chunk_dynamic,
    chunk_semantic,
    chunk_sentence,
    chunk_static,
    cosine,
    split_sentences,
)
from .markdown import (
    chunk_heading,
    frontmatter_title as _frontmatter_title,
    markdown_sections as _markdown_sections,
)

STRATEGIES = ("static", "dynamic", "heading", "sentence", "semantic")


def chunk(
    text: str,
    strategy: str,
    *,
    size: int,
    overlap: int,
    per_chunk: int,
    threshold: float,
    embed_fn: EmbedFn | None = None,
    document_title: str | None = None,
) -> list[str]:
    text = text.strip()
    if not text:
        return []

    match strategy:
        case "static":
            return chunk_static(text, size, overlap)
        case "sentence":
            return chunk_sentence(text, per_chunk)
        case "dynamic":
            return chunk_dynamic(text, size, overlap)
        case "heading":
            return chunk_heading(text, size, overlap, document_title)
        case "semantic":
            if embed_fn is None:
                raise ValueError(
                    "Semantic chunking requires an embedding function."
                )
            return chunk_semantic(text, threshold, embed_fn)
        case _:
            available = ", ".join(sorted(STRATEGIES))
            raise ValueError(
                f"Unknown strategy '{strategy}'. "
                f"Expected one of: {available}."
            )


__all__ = [
    "EmbedFn",
    "STRATEGIES",
    "chunk",
    "chunk_dynamic",
    "chunk_heading",
    "chunk_semantic",
    "chunk_sentence",
    "chunk_static",
    "cosine",
    "split_sentences",
]
