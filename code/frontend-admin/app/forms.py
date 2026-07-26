"""Helpers for translating HTML data into API payloads"""
from typing import Any


def chunk_payload(
    text: str,
    strategy: str,
    chunk_size: int,
    chunk_overlap: int,
    source: str | None = None,
) -> dict[str, Any]:
    """Build the JSON body shared by the chunk and ingest endpoints"""
    payload: dict[str, Any] = {
        "text": text.strip(),
        "strategy": strategy,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    
    # missing source is treated as None
    # empty string is not allowed
    if source and source.strip():
        payload["source"] = source.strip()
        
    return payload


def form_values(
    text: str = "",
    strategy: str = "dynamic",
    chunk_size: int = 200,
    chunk_overlap: int = 30,
    source: str = "proceduri-libra",
) -> dict[str, Any]:
    """Values returned to the form after a request"""
    return {
        "text": text,
        "strategy": strategy,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "source": source,
    }
