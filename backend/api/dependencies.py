"""Shared RAG pipeline dependencies used by multiple API routers."""
from __future__ import annotations

from fastapi import HTTPException

from ..core.config import settings
from ..core.embeddings import get_embedder
from ..ingestion import chunking
from ..retrieval.pipeline import improve_retrieval
from ..retrieval.vectorstore import VectorStore
from ..schemas import ChunkInfo, ChunkRequest

store = VectorStore()


def chunk_params(req: ChunkRequest) -> dict:
    return {
        "strategy": (req.strategy or settings.chunk_strategy).lower(),
        "size": req.chunk_size or settings.chunk_size,
        "overlap": (
            req.chunk_overlap
            if req.chunk_overlap is not None
            else settings.chunk_overlap
        ),
        "per_chunk": req.sentences_per_chunk or settings.sentences_per_chunk,
        "threshold": req.semantic_threshold or settings.semantic_threshold,
        "min_size": min(settings.chunk_min_size, req.chunk_size or settings.chunk_size),
    }


def do_chunk(req: ChunkRequest) -> tuple[list[str], dict]:
    params = chunk_params(req)
    embed_fn = embedder().embed if params["strategy"] == "semantic" else None
    try:
        pieces = chunking.chunk(
            req.text,
            params["strategy"],
            size=params["size"],
            overlap=params["overlap"],
            per_chunk=params["per_chunk"],
            threshold=params["threshold"],
            embed_fn=embed_fn,
            document_title=req.document_title,
            min_size=params["min_size"],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return pieces, params


def chunk_infos(pieces: list[str]) -> list[ChunkInfo]:
    return [
        ChunkInfo(
            index=index,
            text=text,
            chars=len(text),
            approx_tokens=max(1, round(len(text) / 4)),
        )
        for index, text in enumerate(pieces)
    ]


def embedder():
    try:
        return get_embedder()
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding provider not usable: {error}",
        )


def embed(texts: list[str]) -> list[list[float]]:
    try:
        return embedder().embed(texts)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Embedding call failed ({settings.embedding_provider}): {error}",
        )


def require_qdrant() -> None:
    if not store.ping():
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant is not reachable at {settings.qdrant_url} — "
                   "start the Docker services with the platform-specific "
                   "start-backend script",
        )


def retrieve(
    query: str,
    top_k: int,
    min_score: float | None = None,
    query_vector: list[float] | None = None,
) -> list[dict]:
    """Retrieve a broad pool, then threshold, re-rank, and diversify it."""
    threshold = (
        min_score
        if min_score is not None
        else settings.retrieval_score_threshold
    )
    candidate_limit = min(
        50,
        max(top_k, settings.retrieval_candidate_pool, top_k * 3),
    )
    query_vector = query_vector or embed([query])[0]
    candidates = store.search(query_vector, candidate_limit)
    return improve_retrieval(
        query,
        candidates,
        top_k,
        min_score=threshold,
        vector_weight=settings.retrieval_vector_weight,
        duplicate_threshold=settings.retrieval_duplicate_threshold,
        max_per_source=settings.retrieval_max_per_source,
    )
