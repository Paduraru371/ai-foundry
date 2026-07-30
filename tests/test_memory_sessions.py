from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.memory.service import MemoryService
from backend.memory.store import SessionStore
from backend.services import documents


class _FakeEmbedder:
    def describe(self) -> dict[str, str]:
        return {"provider": "local", "model": "fake"}

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [
                1.0 if "python" in text.casefold() else 0.0,
                1.0 if "database" in text.casefold() else 0.0,
            ]
            for text in texts
        ]


class SessionMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.temp.name) / "sessions.sqlite3")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_compaction_cursor_returns_only_newly_archived_messages(self) -> None:
        session_id = self.store.create()["session_id"]
        ids = [
            self.store.add_message(session_id, "user", "First preference."),
            self.store.add_message(session_id, "assistant", "First response."),
            self.store.add_message(session_id, "user", "Second question."),
            self.store.add_message(session_id, "assistant", "Second response."),
        ]

        payload = self.store.compaction_payload(session_id, keep=2)
        self.assertIsNotNone(payload)
        self.assertEqual(
            [message["id"] for message in payload["messages"]],
            ids[:2],
        )
        self.store.save_summary(
            session_id,
            "The user has a durable preference.",
            payload["through_id"],
        )
        self.assertIsNone(self.store.compaction_payload(session_id, keep=2))

    def test_shared_memory_is_ranked_by_current_query(self) -> None:
        current = self.store.create("Current")["session_id"]
        python_session = self.store.create("Python interview")["session_id"]
        database_session = self.store.create("Database interview")["session_id"]
        self.store.add_message(
            python_session,
            "user",
            "I want to improve Python decorators.",
        )
        self.store.add_message(
            database_session,
            "user",
            "Explain database locking.",
        )
        service = MemoryService()

        with (
            patch("backend.memory.service.session_store", self.store),
            patch(
                "backend.memory.service.get_embedder",
                return_value=_FakeEmbedder(),
            ),
        ):
            context = service.prepare(
                current,
                "Continue the Python topic",
                use_shared=True,
            )

        self.assertTrue(context.shared)
        self.assertEqual(context.shared[0]["session_id"], python_session)

    def test_upload_is_saved_under_the_session_folder(self) -> None:
        upload_root = Path(self.temp.name) / "uploads"
        with patch.object(
            documents.settings,
            "chat_upload_dir",
            str(upload_root),
        ):
            relative = documents.save_upload(
                "session-123",
                "../../notes.txt",
                b"hello",
            )

        files = list((upload_root / "session-123").iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), b"hello")
        self.assertTrue(relative.endswith("-notes.txt"))

    def test_session_reports_user_turns_separately_from_messages(self) -> None:
        session_id = self.store.create()["session_id"]
        self.store.add_message(session_id, "user", "Question one")
        self.store.add_message(session_id, "assistant", "Answer one")
        self.store.add_message(session_id, "user", "Question two")
        self.store.add_message(session_id, "assistant", "Answer two")

        detail = self.store.get(session_id)
        listed = self.store.list()[0]

        self.assertEqual(detail["message_count"], 4)
        self.assertEqual(detail["turn_count"], 2)
        self.assertEqual(listed["turn_count"], 2)


if __name__ == "__main__":
    unittest.main()
