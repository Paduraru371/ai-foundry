from __future__ import annotations

import io
import json
import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from docx import Document
from pypdf import PdfReader

ADMIN_ROOT = Path(__file__).resolve().parents[1] / "frontend-admin"
sys.path.insert(0, str(ADMIN_ROOT))

from app.artifacts import ArtifactStore  # noqa: E402
from app.document_export import generate  # noqa: E402
from app.main import app, chat_artifact, chat_message  # noqa: E402


class AdminDocumentExportTests(unittest.TestCase):
    def test_chat_exposes_microphone_and_test_topics(self) -> None:
        chat_template = (ADMIN_ROOT / "templates" / "chat.html").read_text()
        base_template = (ADMIN_ROOT / "templates" / "base.html").read_text()

        self.assertIn('id="chat-record"', chat_template)
        self.assertIn('fetch("/chat/transcribe"', chat_template)
        self.assertIn("data-chat-topic", base_template)
        self.assertIn(
            "/chat/transcribe",
            {route.path for route in app.routes},
        )

    def test_generates_pdf(self) -> None:
        generated = generate("pdf", "Verified answer.", {"model": "gpt-5-mini"})

        self.assertTrue(generated.content.startswith(b"%PDF"))
        self.assertEqual(len(PdfReader(io.BytesIO(generated.content)).pages), 1)

    def test_generates_readable_docx(self) -> None:
        generated = generate("docx", "Technical answer.", {"agent": "Libra Assist"})
        document = Document(io.BytesIO(generated.content))

        self.assertIn(
            "Technical answer.",
            "\n".join(paragraph.text for paragraph in document.paragraphs),
        )

    def test_generates_text_markdown_and_json(self) -> None:
        text = generate("txt", "Answer", {})
        markdown = generate("md", "Answer", {})
        data = generate("json", "Answer", {"model": "gpt-5-mini"})

        self.assertIn(b"LIBRA ASSIST ANSWER", text.content)
        self.assertIn(b"# Libra Assist answer", markdown.content)
        self.assertEqual(json.loads(data.content)["answer"], "Answer")

    def test_artifact_store_round_trip(self) -> None:
        store = ArtifactStore()
        artifact_id = store.put(b"payload", "text/plain", "answer.txt")

        artifact = store.get(artifact_id)
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.content, b"payload")
        self.assertEqual(artifact.filename, "answer.txt")

    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_chat_can_deliver_generated_document(self, ask) -> None:
        ask.return_value = {
            "answer": "Generated answer",
            "agent": {"display_name": "Libra Assist"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 42},
            "fact_check": None,
            "response_format": "plain",
        }

        response = asyncio.run(chat_message(
            message="Create a report",
            history='[{"role":"user","content":"Earlier context"}]',
            use_rag=False,
            fact_check=False,
            agent="default",
            agent_mode="local",
            response_format="plain",
            top_k=3,
            delivery="document",
            document_type="docx",
            attachment=None,
        ))
        payload = json.loads(response.body)
        artifact_id = payload["artifact"]["url"].rsplit("/", 1)[-1]
        download = asyncio.run(chat_artifact(artifact_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["artifact"]["filename"], "libra-assist-answer.docx")
        self.assertTrue(download.body.startswith(b"PK"))
        self.assertEqual(ask.await_args.args[-1][0]["content"], "Earlier context")


if __name__ == "__main__":
    unittest.main()
