"""Small bounded in-memory store for generated chat downloads."""
from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4


@dataclass(frozen=True)
class Artifact:
    content: bytes
    media_type: str
    filename: str
    created_at: float


class ArtifactStore:
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 100) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._items: dict[str, Artifact] = {}
        self._lock = Lock()

    def put(self, content: bytes, media_type: str, filename: str) -> str:
        with self._lock:
            self._prune()
            if len(self._items) >= self.max_items:
                oldest = min(self._items, key=lambda key: self._items[key].created_at)
                self._items.pop(oldest, None)
            artifact_id = uuid4().hex
            self._items[artifact_id] = Artifact(
                content=content,
                media_type=media_type,
                filename=filename,
                created_at=time.time(),
            )
            return artifact_id

    def get(self, artifact_id: str) -> Artifact | None:
        with self._lock:
            self._prune()
            return self._items.get(artifact_id)

    def _prune(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        expired = [
            key for key, artifact in self._items.items()
            if artifact.created_at < cutoff
        ]
        for key in expired:
            self._items.pop(key, None)


artifact_store = ArtifactStore()
