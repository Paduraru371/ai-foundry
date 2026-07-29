"""Chunking, ingestion, collection, and retrieval endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import (
    chunk_infos,
    do_chunk,
    embed,
    embedder,
    require_qdrant,
    retrieve,
    store,
)
from ...core.config import settings
from ...schemas import (
    ChunkRequest,
    ChunkResponse,
    CollectionInfo,
    IngestRequest,
    IngestResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from ...retrieval.vectorstore import DimensionMismatch

router = APIRouter()


@router.post("/chunk", response_model=ChunkResponse, tags=["1 · chunking"])
def chunk_only(req: ChunkRequest) -> ChunkResponse:
    """Split text and expose the boundaries without storing anything."""
    pieces, params = do_chunk(req)
    return ChunkResponse(
        strategy=params["strategy"],
        params_used=params,
        count=len(pieces),
        chunks=chunk_infos(pieces),
    )


@router.post("/ingest", response_model=IngestResponse, tags=["2 · ingestion"])
def ingest(req: IngestRequest) -> IngestResponse:
    """Chunk, embed, and store a document in Qdrant."""
    require_qdrant()
    pieces, params = do_chunk(req)
    if not pieces:
        raise HTTPException(
            status_code=422,
            detail="No chunks produced — is the text empty?",
        )
    vectors = embed(pieces)
    dimension = len(vectors[0])
    try:
        store.ensure_collection(dimension)
    except DimensionMismatch as error:
        raise HTTPException(status_code=409, detail=str(error))
    ids = store.upsert(pieces, vectors, params["strategy"], req.source)
    return IngestResponse(
        strategy=params["strategy"],
        count=len(pieces),
        vector_dimension=dimension,
        embedding_preview=[round(value, 5) for value in vectors[0][:8]],
        embedding_model=embedder().describe(),
        point_ids=ids,
        chunks=chunk_infos(pieces),
    )


@router.get("/collection", response_model=CollectionInfo, tags=["2 · ingestion"])
def collection_info() -> CollectionInfo:
    require_qdrant()
    return CollectionInfo(**store.info())


@router.delete("/collection", tags=["2 · ingestion"])
def collection_reset() -> dict:
    """Wipe everything — the clean slate between demos."""
    require_qdrant()
    return {"deleted": store.reset(), "collection": settings.qdrant_collection}


@router.post("/search", response_model=SearchResponse, tags=["3 · retrieval"])
def search(req: SearchRequest) -> SearchResponse:
    """Embed a query and return the nearest chunks with cosine scores."""
    require_qdrant()
    if not store.info()["exists"]:
        raise HTTPException(
            status_code=404,
            detail="Collection is empty — POST /ingest first.",
        )
    top_k = req.top_k or settings.top_k
    query_vector = embed([req.query])[0]
    min_score = (
        req.min_score
        if req.min_score is not None
        else settings.retrieval_score_threshold
    )
    hits = retrieve(req.query, top_k, min_score, query_vector)
    return SearchResponse(
        query=req.query,
        top_k=top_k,
        embedding_model=embedder().describe(),
        query_embedding_preview=[round(value, 5) for value in query_vector[:8]],
        hits=[SearchHit(**hit) for hit in hits],
        message=(
            None
            if hits
            else f"Nothing relevant found at or above score {min_score:.2f}."
        ),
    )
