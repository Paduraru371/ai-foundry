"""Qdrant wrapper — collection lifecycle, upsert, similarity search.

The collection is created lazily with the dimension of the first embedding that
arrives. If a later embedding model produces a different dimension, we refuse
loudly: vectors from different models live in different spaces and comparing
them is meaningless — reset the collection and re-ingest instead.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient, models

from ..core.config import settings

POINT_ID_NAMESPACE = uuid.UUID("8ca82e2d-605f-4e4e-91b5-8a0991249b62")


def stable_chunk_id(source: str | None, index: int) -> str:
    """Return the same Qdrant-compatible UUID for a document chunk every time."""
    source_key = (source or "adhoc").strip() or "adhoc"
    return str(uuid.uuid5(POINT_ID_NAMESPACE, f"{source_key}:{index}"))


class DimensionMismatch(Exception):
    def __init__(self, existing: int, incoming: int) -> None:
        self.existing = existing
        self.incoming = incoming
        super().__init__(
            f"Collection stores {existing}-dimensional vectors but the current embedding "
            f"model produces {incoming} dimensions. Vectors from different embedding models "
            f"are not comparable — DELETE /collection and re-ingest."
        )


class VectorStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url, timeout=10)
        self.collection = settings.qdrant_collection

    # --- lifecycle -----------------------------------------------------------
    def ensure_collection(self, dim: int) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )
            return
        existing = self._vector_size()
        if existing != dim:
            raise DimensionMismatch(existing, dim)

    def reset(self) -> bool:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
            return True
        return False

    # --- data ----------------------------------------------------------------
    def _scroll_source(
        self,
        source: str,
        *,
        with_payload: bool,
    ) -> list:
        points: list = []
        offset = None
        source_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source),
                )
            ]
        )
        while True:
            page, offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=source_filter,
                limit=256,
                offset=offset,
                with_payload=with_payload,
                with_vectors=False,
            )
            points.extend(page)
            if offset is None:
                break
        return points

    def delete_source(self, source: str) -> int:
        """Delete only chunks belonging to one source, preserving the corpus."""
        source_name = source.strip()
        if not source_name or not self.client.collection_exists(self.collection):
            return 0
        points = self._scroll_source(source_name, with_payload=False)
        point_ids = [point.id for point in points]
        if point_ids:
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.PointIdsList(points=point_ids),
                wait=True,
            )
        return len(point_ids)

    def source_snapshot(self, source: str) -> list[dict]:
        """Return stored IDs and payloads used for incremental-index checks."""
        source_name = source.strip()
        if not source_name or not self.client.collection_exists(self.collection):
            return []
        points = self._scroll_source(source_name, with_payload=True)
        return [
            {"id": str(point.id), "payload": dict(point.payload or {})}
            for point in points
        ]

    def upsert(self, chunks: list[str], vectors: list[list[float]], strategy: str,
               source: str | None, fingerprint: str | None = None) -> list[str]:
        source_name = source.strip() if source and source.strip() else None
        old_ids: set[str] = set()
        if source_name:
            points = self._scroll_source(source_name, with_payload=False)
            old_ids = {str(point.id) for point in points}
        ids = [stable_chunk_id(source, index) for index in range(len(chunks))]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=pid,
                    vector=vec,
                    payload={
                        "text": text,
                        "index": i,
                        "strategy": strategy,
                        "source": source or "adhoc",
                        "index_fingerprint": fingerprint,
                        "index_chunk_count": len(chunks),
                        "ingested_at": now,
                    },
                )
                for i, (pid, text, vec) in enumerate(zip(ids, chunks, vectors))
            ],
            wait=True,
        )
        stale_ids = old_ids - set(ids)
        if stale_ids:
            self.client.delete(
                collection_name=self.collection,
                points_selector=models.PointIdsList(points=list(stale_ids)),
                wait=True,
            )
        return ids

    def search(self, vector: list[float], top_k: int) -> list[dict]:
        hits = self.client.query_points(
            collection_name=self.collection, query=vector, limit=top_k, with_payload=True
        ).points
        return [
            {
                "id": str(h.id),
                "score": round(float(h.score), 4),
                "text": (h.payload or {}).get("text", ""),
                "index": (h.payload or {}).get("index"),
                "strategy": (h.payload or {}).get("strategy"),
                "source": (h.payload or {}).get("source"),
            }
            for h in hits
        ]

    # --- introspection --------------------------------------------------------
    def info(self) -> dict:
        if not self.client.collection_exists(self.collection):
            return {"exists": False, "name": self.collection, "points_count": 0,
                    "vector_dimension": None, "distance": None}
        c = self.client.get_collection(self.collection)
        return {
            "exists": True,
            "name": self.collection,
            "points_count": c.points_count or 0,
            "vector_dimension": self._vector_size(),
            "distance": "cosine",
        }

    def ping(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def _vector_size(self) -> int:
        cfg = self.client.get_collection(self.collection).config.params.vectors
        return cfg.size if hasattr(cfg, "size") else next(iter(cfg.values())).size
