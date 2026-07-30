"""Schemas for chunking, ingestion, retrieval, and vector collection state."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Strategy = Literal["static", "dynamic", "heading", "sentence", "semantic"]


class ChunkRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Libra Bank blocks a card after three failed PIN attempts. "
                "A blocked card can be unblocked in the branch after identity verification. "
                "Mortgage early repayment is free of charge in the variable-rate period.",
        "strategy": "dynamic",
        "chunk_size": 120,
        "chunk_overlap": 30,
    }]}}

    text: str = Field(..., description="Raw text to split", min_length=1)
    strategy: Optional[Strategy] = Field(None, description="Defaults to CHUNK_STRATEGY from .env")
    chunk_size: Optional[int] = Field(None, ge=50, description="Target size, characters (≥ 50)")
    chunk_overlap: Optional[int] = Field(None, ge=0, description="Overlap, characters")
    sentences_per_chunk: Optional[int] = Field(None, ge=1, description="'sentence' strategy only")
    semantic_threshold: Optional[float] = Field(
        None,
        gt=0,
        le=1,
        description="'semantic' strategy only — 0 < t ≤ 1",
    )
    document_title: Optional[str] = Field(
        None,
        min_length=1,
        description="'heading' strategy context; frontmatter title is used when omitted",
    )


class ChunkInfo(BaseModel):
    index: int
    text: str
    chars: int
    approx_tokens: int = Field(description="chars / 4 — a rough but honest estimate")


class ChunkResponse(BaseModel):
    strategy: Strategy
    params_used: dict
    count: int
    chunks: list[ChunkInfo]


class IngestRequest(ChunkRequest):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Libra Bank blocks a card after three failed PIN attempts. "
                "A blocked card can be unblocked in the branch after identity verification. "
                "Mortgage early repayment is free of charge in the variable-rate period.",
        "strategy": "dynamic",
        "source": "retail-faq",
    }]}}

    source: Optional[str] = Field(
        None,
        description="Label stored with every chunk (e.g. 'cards-faq')",
    )


class IngestResponse(BaseModel):
    status: Literal["indexed", "unchanged"] = "indexed"
    fingerprint: Optional[str] = None
    strategy: Strategy
    count: int
    vector_dimension: int
    embedding_preview: list[float] = Field(
        description="First 8 dimensions of chunk #0 — meaning as numbers"
    )
    embedding_model: dict
    point_ids: list[str]
    chunks: list[ChunkInfo]


class SearchRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "query": "my card got frozen, what do I do?",
        "top_k": 3,
    }]}}

    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)
    min_score: Optional[float] = Field(
        None,
        ge=-1,
        le=1,
        description="Minimum cosine similarity; defaults to RETRIEVAL_SCORE_THRESHOLD",
    )


class SearchHit(BaseModel):
    score: float = Field(description="Cosine similarity — 1.0 is identical direction")
    text: str
    index: Optional[int] = None
    strategy: Optional[str] = None
    source: Optional[str] = None
    lexical_score: Optional[float] = Field(
        None,
        description="Fraction of meaningful query terms found in this passage",
    )
    rerank_score: Optional[float] = Field(
        None,
        description="Combined semantic and lexical score used for final ordering",
    )
    id: str


class SearchResponse(BaseModel):
    query: str
    top_k: int
    embedding_model: dict
    query_embedding_preview: list[float]
    hits: list[SearchHit]
    message: Optional[str] = None


class CollectionInfo(BaseModel):
    exists: bool
    name: str
    points_count: int
    vector_dimension: Optional[int] = None
    distance: Optional[str] = None
