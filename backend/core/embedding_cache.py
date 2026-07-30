"""Persistent, model-aware SQLite cache for embedding vectors."""
from __future__ import annotations

import sqlite3
from array import array
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EmbeddingCache:
    """Store vectors by provider, model and exact-text SHA-256 digest."""

    def __init__(self, path: str | Path, max_entries: int = 50_000) -> None:
        self.path = Path(path)
        self.max_entries = max(1, max_entries)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS embeddings_v2 (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    text_digest TEXT NOT NULL,
                    vector_blob BLOB NOT NULL,
                    dimensions INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(provider, model, text_digest)
                );
                CREATE INDEX IF NOT EXISTS idx_embeddings_v2_updated
                    ON embeddings_v2(updated_at);
                """
            )
            connection.commit()

    def get_many(
        self,
        provider: str,
        model: str,
        digests: list[str],
    ) -> dict[str, list[float]]:
        if not digests:
            return {}
        unique = list(dict.fromkeys(digests))
        result: dict[str, list[float]] = {}
        with self._connect() as connection:
            for offset in range(0, len(unique), 800):
                batch = unique[offset:offset + 800]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"""
                    SELECT text_digest, vector_blob, dimensions
                    FROM embeddings_v2
                    WHERE provider = ? AND model = ?
                      AND text_digest IN ({placeholders})
                    """,
                    (provider, model, *batch),
                ).fetchall()
                for digest, raw_vector, dimensions in rows:
                    try:
                        values = array("f")
                        values.frombytes(bytes(raw_vector))
                        vector = [float(value) for value in values]
                    except (TypeError, ValueError):
                        continue
                    if len(vector) == int(dimensions) and vector:
                        result[str(digest)] = vector
        return result

    def put_many(
        self,
        provider: str,
        model: str,
        vectors: dict[str, list[float]],
    ) -> None:
        if not vectors:
            return
        now = _now()
        rows = [
            (
                provider,
                model,
                digest,
                array("f", vector).tobytes(),
                len(vector),
                now,
            )
            for digest, vector in vectors.items()
            if vector
        ]
        if not rows:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO embeddings_v2(
                    provider, model, text_digest, vector_blob, dimensions, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, model, text_digest) DO UPDATE SET
                    vector_blob = excluded.vector_blob,
                    dimensions = excluded.dimensions,
                    updated_at = excluded.updated_at
                """,
                rows,
            )
            count = int(connection.execute(
                "SELECT COUNT(*) FROM embeddings_v2"
            ).fetchone()[0])
            excess = count - self.max_entries
            if excess > 0:
                connection.execute(
                    """
                    DELETE FROM embeddings_v2 WHERE rowid IN (
                        SELECT rowid FROM embeddings_v2
                        ORDER BY updated_at ASC LIMIT ?
                    )
                    """,
                    (excess,),
                )
            connection.commit()

    def info(self) -> dict[str, int | str]:
        with self._connect() as connection:
            count = int(connection.execute(
                "SELECT COUNT(*) FROM embeddings_v2"
            ).fetchone()[0])
        return {
            "path": str(self.path),
            "entries": count,
            "max_entries": self.max_entries,
        }
