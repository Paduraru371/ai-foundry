"""SQLite persistence for conversations and incremental summaries."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    candidate = clean[: max(1, limit - 3)].rstrip()
    boundary = max(candidate.rfind(". "), candidate.rfind("? "), candidate.rfind("! "))
    if boundary >= limit // 2:
        candidate = candidate[:boundary + 1]
    else:
        word = candidate.rfind(" ")
        if word >= limit // 2:
            candidate = candidate[:word]
    return candidate.rstrip() + "..."


class SessionStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.session_db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    summarized_through_id INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, id);
                CREATE INDEX IF NOT EXISTS idx_sessions_updated
                    ON sessions(updated_at DESC);
                """
            )
            connection.commit()

    def create(self, title: str = "New conversation") -> dict[str, Any]:
        session_id = uuid4().hex
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions(
                    session_id, title, summary, summarized_through_id,
                    created_at, updated_at
                ) VALUES (?, ?, '', 0, ?, ?)
                """,
                (session_id, _preview(title, 120), now, now),
            )
            connection.commit()
        return self.get(session_id) or {}

    def exists(self, session_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return row is not None

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        if not self.exists(session_id):
            raise ValueError("Session not found.")
        now = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages(session_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content.strip(),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            connection.commit()
        return int(cursor.lastrowid)

    def set_message_metadata(self, message_id: int, metadata: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE messages SET metadata_json = ? WHERE id = ?",
                (json.dumps(metadata, ensure_ascii=False), message_id),
            )
            connection.commit()

    def set_title_from_message(self, session_id: str, message: str) -> None:
        title = _preview(message, 70) or "Conversation"
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions SET title = ?
                WHERE session_id = ? AND title = 'New conversation'
                """,
                (title, session_id),
            )
            connection.commit()

    def recent_messages(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, role, content, metadata_json, created_at
                FROM messages WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._message(row) for row in reversed(rows)]

    def compaction_payload(self, session_id: str, keep: int) -> dict | None:
        with self._connect() as connection:
            session = connection.execute(
                """
                SELECT summary, summarized_through_id FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if session is None:
                return None
            boundary = connection.execute(
                """
                SELECT id FROM messages WHERE session_id = ?
                ORDER BY id DESC LIMIT 1 OFFSET ?
                """,
                (session_id, keep),
            ).fetchone()
            if boundary is None:
                return None
            rows = connection.execute(
                """
                SELECT id, role, content, metadata_json FROM messages
                WHERE session_id = ? AND id > ? AND id <= ?
                ORDER BY id
                """,
                (session_id, int(session[1] or 0), int(boundary[0])),
            ).fetchall()
        if not rows:
            return None
        return {
            "previous_summary": str(session[0] or ""),
            "through_id": int(boundary[0]),
            "messages": [self._compaction_message(row) for row in rows],
        }

    def save_summary(self, session_id: str, summary: str, through_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions SET summary = ?, summarized_through_id = ?
                WHERE session_id = ?
                """,
                (
                    _preview(summary, settings.session_summary_max_chars),
                    through_id,
                    session_id,
                ),
            )
            connection.commit()

    def memory_candidates(self, exclude: str, limit: int) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, title, summary, updated_at FROM sessions
                WHERE session_id != ? ORDER BY updated_at DESC LIMIT ?
                """,
                (exclude, limit),
            ).fetchall()
            result: list[dict[str, str]] = []
            for session_id, title, summary, updated_at in rows:
                text = str(summary or "").strip()
                if not text:
                    recent = connection.execute(
                        """
                        SELECT role, content FROM messages WHERE session_id = ?
                        ORDER BY id DESC LIMIT 8
                        """,
                        (session_id,),
                    ).fetchall()
                    text = "\n".join(
                        f"- {str(role).title()}: {_preview(str(content), 360)}"
                        for role, content in reversed(recent)
                    )
                if text:
                    result.append({
                        "session_id": str(session_id),
                        "title": str(title),
                        "summary": text,
                        "updated_at": str(updated_at),
                    })
        return result

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.session_id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id),
                       SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END),
                       COALESCE((SELECT content FROM messages last
                           WHERE last.session_id = s.session_id
                           ORDER BY last.id DESC LIMIT 1), '')
                FROM sessions s LEFT JOIN messages m
                    ON m.session_id = s.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "session_id": str(row[0]),
                "title": str(row[1]),
                "created_at": str(row[2]),
                "updated_at": str(row[3]),
                "message_count": int(row[4]),
                "turn_count": int(row[5] or 0),
                "last_message": _preview(str(row[6]), 100),
            }
            for row in rows
        ]

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT s.session_id, s.title, s.summary, s.created_at, s.updated_at,
                       COUNT(m.id),
                       SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END),
                       COALESCE((SELECT content FROM messages last
                           WHERE last.session_id = s.session_id
                           ORDER BY last.id DESC LIMIT 1), '')
                FROM sessions s LEFT JOIN messages m
                    ON m.session_id = s.session_id
                WHERE s.session_id = ?
                GROUP BY s.session_id
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "session_id": str(row[0]),
            "title": str(row[1]),
            "summary": str(row[2] or ""),
            "created_at": str(row[3]),
            "updated_at": str(row[4]),
            "message_count": int(row[5]),
            "turn_count": int(row[6] or 0),
            "last_message": _preview(str(row[7]), 100),
            "messages": self.recent_messages(session_id, 500),
        }

    def delete(self, session_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _message(row: tuple) -> dict[str, Any]:
        try:
            metadata = json.loads(str(row[3] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": int(row[0]),
            "role": str(row[1]),
            "content": str(row[2]),
            "metadata": metadata if isinstance(metadata, dict) else {},
            "created_at": str(row[4]),
        }

    @staticmethod
    def _compaction_message(row: tuple) -> dict[str, Any]:
        content = str(row[2])
        try:
            metadata = json.loads(str(row[3] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        attachment = metadata.get("attachment") if isinstance(metadata, dict) else None
        if attachment and attachment.get("filename"):
            content += f"\n[Uploaded document: {attachment['filename']}]"
        return {
            "id": int(row[0]),
            "role": str(row[1]),
            "content": content,
        }


session_store = SessionStore()
