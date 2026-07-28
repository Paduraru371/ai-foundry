"""Reusable primitives and non-Markdown chunking strategies."""
from __future__ import annotations

import math
import re
from typing import Callable

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")

EmbedFn = Callable[[list[str]], list[list[float]]]


def split_sentences(text: str) -> list[str]:
    parts = [sentence.strip() for sentence in SENTENCE_END.split(text)]
    return [sentence for sentence in parts if sentence]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def chunk_static(text: str, size: int, overlap: int) -> list[str]:
    """Use fixed character windows, even when they cut through words."""
    step = max(1, size - overlap)
    return [
        text[index:index + size].strip()
        for index in range(0, len(text), step)
        if text[index:index + size].strip()
    ]


def chunk_sentence(text: str, per_chunk: int) -> list[str]:
    """Group every N sentences into one chunk."""
    sentences = split_sentences(text)
    size = max(1, per_chunk)
    return [
        " ".join(sentences[index:index + size])
        for index in range(0, len(sentences), size)
    ]


def chunk_dynamic(text: str, size: int, overlap: int) -> list[str]:
    """Pack complete sentences into a size budget with sentence-tail overlap."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            tail: list[str] = []
            tail_len = 0
            for sentence in reversed(current):
                if tail_len + len(sentence) > overlap:
                    break
                tail.insert(0, sentence)
                tail_len += len(sentence) + 1
            current = tail
            current_len = tail_len

    for paragraph in PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        for sentence in split_sentences(paragraph):
            if len(sentence) > size:
                flush()
                chunks.extend(chunk_static(sentence, size, overlap))
                current, current_len = [], 0
                continue
            if current_len + len(sentence) + 1 > size:
                flush()
            current.append(sentence)
            current_len += len(sentence) + 1
        if current_len > size * 0.7:
            flush()
    if current:
        chunks.append(" ".join(current))
    return [
        chunk
        for index, chunk in enumerate(chunks)
        if not (index > 0 and chunk and chunk in chunks[index - 1])
    ]


def chunk_semantic(
    text: str,
    threshold: float,
    embed_fn: EmbedFn,
) -> list[str]:
    """Start a new chunk when adjacent sentence similarity drops."""
    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return sentences
    vectors = embed_fn(sentences)
    chunks: list[list[str]] = [[sentences[0]]]
    for index in range(1, len(sentences)):
        if cosine(vectors[index - 1], vectors[index]) < threshold:
            chunks.append([sentences[index]])
        else:
            chunks[-1].append(sentences[index])
    return [" ".join(chunk) for chunk in chunks]
