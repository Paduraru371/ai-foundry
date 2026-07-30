"""Chunking, ingestion, collection, and retrieval endpoints."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..dependencies import (
    chunk_infos,
    chunk_params,
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
CORPUS_DIR = Path(__file__).resolve().parents[3] / "data"
HIDDEN_CORPUS_FILES = {"readme.md", "questions.md"}


def _index_fingerprint(req: IngestRequest, params: dict, model: dict) -> str:
    """Fingerprint every input that can change chunks or their vector space."""
    value = {
        "text_sha256": hashlib.sha256(req.text.encode("utf-8")).hexdigest(),
        "document_title": req.document_title,
        "chunking": params,
        "embedding": {
            "provider": model.get("provider"),
            "model": model.get("model"),
        },
    }
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source_is_current(existing: list[dict], fingerprint: str) -> bool:
    expected_counts = {
        point["payload"].get("index_chunk_count")
        for point in existing
    }
    return bool(
        existing
        and expected_counts == {len(existing)}
        and all(
            point["payload"].get("index_fingerprint") == fingerprint
            for point in existing
        )
    )


def _corpus_source_path(source: str) -> Path:
    """Resolve a source through an allowlist built from the corpus directory."""
    available = {
        path.stem: path
        for path in CORPUS_DIR.glob("*.md")
        if path.name.casefold() not in HIDDEN_CORPUS_FILES
    }
    path = available.get(source)
    if path is None:
        raise HTTPException(status_code=404, detail="Source document is not available.")
    return path


def _document_title(text: str, fallback: str) -> str:
    if text.startswith("---"):
        for line in text.splitlines()[1:]:
            if line.strip() == "---":
                break
            key, separator, value = line.partition(":")
            if separator and key.strip().casefold() == "title":
                return value.strip().strip("\"'") or fallback
    return fallback


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
    params = chunk_params(req)
    embedding_model = embedder().describe()
    fingerprint = _index_fingerprint(req, params, embedding_model)
    source = (req.source or "").strip()
    if source:
        existing = store.source_snapshot(source)
        if _source_is_current(existing, fingerprint):
            ordered = sorted(
                existing,
                key=lambda point: int(point["payload"].get("index", 0)),
            )
            pieces = [str(point["payload"].get("text", "")) for point in ordered]
            info = store.info()
            return IngestResponse(
                status="unchanged",
                fingerprint=fingerprint,
                strategy=params["strategy"],
                count=len(pieces),
                vector_dimension=int(info["vector_dimension"] or 0),
                embedding_preview=[],
                embedding_model=embedding_model,
                point_ids=[point["id"] for point in ordered],
                chunks=chunk_infos(pieces),
            )
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
    ids = store.upsert(
        pieces,
        vectors,
        params["strategy"],
        req.source,
        fingerprint,
    )
    return IngestResponse(
        status="indexed",
        fingerprint=fingerprint,
        strategy=params["strategy"],
        count=len(pieces),
        vector_dimension=dimension,
        embedding_preview=[round(value, 5) for value in vectors[0][:8]],
        embedding_model=embedding_model,
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


@router.delete("/collection/sources/{source}", tags=["2 · ingestion"])
def collection_source_delete(source: str) -> dict:
    """Remove one document source without touching the rest of the collection."""
    require_qdrant()
    return {
        "source": source,
        "deleted_points": store.delete_source(source),
        "collection": settings.qdrant_collection,
    }


@router.get("/sources/{source}/download", tags=["3 · retrieval"])
def source_document_download(source: str) -> Response:
    """Download an allowlisted grounding document."""
    path = _corpus_source_path(source)
    return Response(
        content=path.read_bytes(),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@router.get("/sources/{source}", tags=["3 · retrieval"])
def source_document(source: str) -> dict[str, str]:
    """Return an allowlisted grounding document for an in-browser viewer."""
    path = _corpus_source_path(source)
    content = path.read_text(encoding="utf-8")
    return {
        "source": source,
        "filename": path.name,
        "title": _document_title(content, path.stem.replace("_", " ").title()),
        "content": content,
    }


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
