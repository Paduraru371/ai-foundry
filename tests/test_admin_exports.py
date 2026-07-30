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
from pptx import Presentation

ADMIN_ROOT = Path(__file__).resolve().parents[1] / "frontend-admin"
sys.path.insert(0, str(ADMIN_ROOT))

from app.artifacts import ArtifactStore  # noqa: E402
from app.api_client import BackendError  # noqa: E402
from app.document_export import generate  # noqa: E402
from app.main import (  # noqa: E402
    app,
    chat_artifact,
    chat_message,
    chat_source_download,
    infer_document_request,
    speech_text,
)


class AdminDocumentExportTests(unittest.TestCase):
    def test_chat_exposes_microphone_and_test_topics(self) -> None:
        chat_template = (
            ADMIN_ROOT / "templates" / "chat.html"
        ).read_text(encoding="utf-8")
        base_template = (
            ADMIN_ROOT / "templates" / "base.html"
        ).read_text(encoding="utf-8")

        self.assertIn('id="chat-record"', chat_template)
        self.assertIn('id="chat-send"', chat_template)
        self.assertIn('"■ Stop generating"', chat_template)
        self.assertIn('"message-action", "Copy"', chat_template)
        self.assertIn('"message-action", "Edit"', chat_template)
        self.assertIn('class="chat-control-column"', chat_template)
        self.assertIn('class="chat-composer-notes"', chat_template)
        self.assertIn("navigator.clipboard.writeText(message.content)", chat_template)
        self.assertIn("memory: metadata.memory", chat_template)
        copy_handler = chat_template.split(
            "async function copyMessage", 1
        )[1].split("function render", 1)[0]
        self.assertNotIn("fillComposer", copy_handler)
        self.assertIn("new AbortController()", chat_template)
        self.assertIn("/chat/generations/", chat_template)
        self.assertIn('id="chat-source-dialog"', chat_template)
        self.assertIn('id="chat-source-format"', chat_template)
        self.assertIn('name="apply_response_format"', chat_template)
        self.assertIn('name="apply_document_type"', chat_template)
        self.assertIn('value="pptx"', chat_template)
        self.assertIn("Generated file type", chat_template)
        self.assertIn("Content formatting", chat_template)
        self.assertIn("Plain text file (.txt)", chat_template)
        self.assertIn("Changing its value checks it automatically", chat_template)
        self.assertIn("sessionReady = initializeSession()", chat_template)
        self.assertIn("localStorage.removeItem(sessionStorageKey)", chat_template)
        self.assertIn("async function openSource", chat_template)
        self.assertIn(
            "/chat/sources/${encodeURIComponent(activeSource)}/download",
            chat_template,
        )
        self.assertIn('"chat-source-link"', chat_template)
        self.assertIn("message.artifacts?.length", chat_template)
        self.assertIn('fetch("/chat/transcribe"', chat_template)
        self.assertIn("data-chat-topic", base_template)
        self.assertIn(
            "/chat/transcribe",
            {route.path for route in app.routes},
        )
        self.assertIn(
            "/chat/generations/{generation_id}/cancel",
            {route.path for route in app.routes},
        )
        self.assertIn(
            "/chat/sources/{source}",
            {route.path for route in app.routes},
        )
        self.assertIn(
            "/chat/sources/{source}/download",
            {route.path for route in app.routes},
        )

    def test_generates_pdf(self) -> None:
        generated = generate("pdf", "Verified answer.", {"model": "gpt-5-mini"})

        self.assertTrue(generated.content.startswith(b"%PDF"))
        self.assertEqual(len(PdfReader(io.BytesIO(generated.content)).pages), 1)

    def test_pdf_and_docx_preserve_bullet_items(self) -> None:
        answer = "- Identity document\n- Proof of address"
        pdf = PdfReader(io.BytesIO(generate("pdf", answer, {}).content))
        docx = Document(io.BytesIO(generate("docx", answer, {}).content))

        self.assertIn("Identity document", pdf.pages[0].extract_text())
        self.assertEqual(
            ["List Bullet", "List Bullet"],
            [
                paragraph.style.name
                for paragraph in docx.paragraphs
                if paragraph.text in {"Identity document", "Proof of address"}
            ],
        )

    def test_generates_readable_docx(self) -> None:
        generated = generate("docx", "Technical answer.", {"agent": "Libra Assist"})
        document = Document(io.BytesIO(generated.content))

        self.assertIn(
            "Technical answer.",
            "\n".join(paragraph.text for paragraph in document.paragraphs),
        )

    def test_generates_readable_pptx(self) -> None:
        generated = generate(
            "pptx",
            "- Identity document\n- Proof of address",
            {"agent": "Libra Assist"},
        )
        presentation = Presentation(io.BytesIO(generated.content))
        slide_text = "\n".join(
            shape.text
            for slide in presentation.slides
            for shape in slide.shapes
            if hasattr(shape, "text")
        )

        self.assertEqual(generated.filename, "libra-assist-answer.pptx")
        self.assertGreaterEqual(len(presentation.slides), 2)
        self.assertIn("Identity document", slide_text)

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
            apply_delivery=True,
            apply_document_type=True,
            attachment=None,
        ))
        payload = json.loads(response.body)
        artifact_id = payload["artifact"]["url"].rsplit("/", 1)[-1]
        download = asyncio.run(chat_artifact(artifact_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["artifact"]["filename"], "libra-assist-answer.docx")
        self.assertTrue(download.body.startswith(b"PK"))
        self.assertEqual(ask.await_args.args[-1][0]["content"], "Earlier context")

    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_unchecked_answer_settings_are_ignored(self, ask) -> None:
        ask.return_value = {
            "answer": "Plain answer",
            "agent": {"display_name": "Configured agent"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 20},
            "fact_check": None,
            "response_format": "plain",
        }

        response = asyncio.run(chat_message(
            message="Answer this question.",
            history="[]",
            use_rag=False,
            fact_check=False,
            agent="motrun-onboarding",
            agent_mode="foundry",
            response_format="bullet_list",
            top_k=12,
            delivery="document",
            document_type="docx",
            attachment=None,
        ))
        payload = json.loads(response.body)

        self.assertEqual(payload["artifacts"], [])
        self.assertIsNone(ask.await_args.args[3])
        self.assertIsNone(ask.await_args.args[4])
        self.assertIsNone(ask.await_args.args[2])
        self.assertEqual(ask.await_args.args[6], "plain")
        self.assertEqual(ask.await_args.kwargs["delivery"], "conversation")
        self.assertEqual(ask.await_args.kwargs["document_type"], "pdf")

    @patch("app.main.rag_api.create_session", new_callable=AsyncMock)
    @patch("app.main.rag_api.session", new_callable=AsyncMock)
    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_stale_browser_session_is_replaced_automatically(
        self,
        ask,
        session,
        create_session,
    ) -> None:
        session.side_effect = BackendError("Session not found.", 404)
        create_session.return_value = {"session_id": "replacement-session"}
        ask.return_value = {
            "answer": "Recovered answer",
            "agent": {"display_name": "Configured agent"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 20},
            "fact_check": None,
            "response_format": "plain",
            "session_id": "replacement-session",
        }

        response = asyncio.run(chat_message(
            message="hi",
            history="[]",
            session_id="deleted-session",
            use_rag=False,
            attachment=None,
        ))
        payload = json.loads(response.body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["answer"], "Recovered answer")
        self.assertEqual(payload["session_id"], "replacement-session")
        create_session.assert_awaited_once()
        self.assertEqual(
            ask.await_args.kwargs["session_id"],
            "replacement-session",
        )

    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_checked_file_type_implies_document_delivery(self, ask) -> None:
        ask.return_value = {
            "answer": "Generated answer",
            "agent": {"display_name": "Configured agent"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 20},
            "fact_check": None,
            "response_format": "plain",
        }

        response = asyncio.run(chat_message(
            message="Answer this question.",
            history="[]",
            use_rag=False,
            fact_check=False,
            response_format="plain",
            top_k=3,
            delivery="conversation",
            document_type="pptx",
            apply_document_type=True,
            attachment=None,
        ))
        payload = json.loads(response.body)

        self.assertEqual(
            payload["artifact"]["filename"],
            "libra-assist-answer.pptx",
        )
        self.assertEqual(ask.await_args.kwargs["delivery"], "document")

    def test_message_overrides_checked_document_and_structure_settings(self) -> None:
        delivery, document_type, response_format = infer_document_request(
            "Generează o prezentare PPTX în plain text.",
            "document",
            "pdf",
            "bullet_list",
        )

        self.assertEqual(delivery, "document")
        self.assertEqual(document_type, "pptx")
        self.assertEqual(response_format, "plain")

    def test_plain_text_document_request_means_txt_file(self) -> None:
        delivery, document_type, response_format = infer_document_request(
            "Generează un document plain text cu bullet points.",
            "conversation",
            "pdf",
            "plain",
        )

        self.assertEqual(delivery, "document")
        self.assertEqual(document_type, "txt")
        self.assertEqual(response_format, "bullet_list")

    def test_natural_audio_pdf_and_bullets_request_keeps_both_deliveries(self) -> None:
        delivery, document_type, response_format = infer_document_request(
            (
                "Răspunde la aceste întrebări audio și printr-un document PDF "
                "în stilul bullet points."
            ),
            "conversation",
            "docx",
            "plain",
        )

        self.assertEqual(delivery, "speech_document")
        self.assertEqual(document_type, "pdf")
        self.assertEqual(response_format, "bullet_list")

    def test_explicit_no_audio_overrides_audio_word(self) -> None:
        delivery, document_type, response_format = infer_document_request(
            "Răspunde fără audio și generează un document PDF cu bullet points.",
            "conversation",
            "docx",
            "plain",
        )

        self.assertEqual(delivery, "document")
        self.assertEqual(document_type, "pdf")
        self.assertEqual(response_format, "bullet_list")

    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_conversation_request_generates_downloadable_pdf_with_bullets(
        self,
        ask,
    ) -> None:
        ask.return_value = {
            "answer": "- Identity document\n- Proof of address",
            "agent": {"display_name": "Motrun Onboarding"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 42},
            "fact_check": None,
            "response_format": "bullet_list",
        }

        response = asyncio.run(chat_message(
            message="Generează un PDF cu bullet points despre onboarding",
            history="[]",
            use_rag=True,
            fact_check=False,
            agent="motrun-onboarding",
            agent_mode="local",
            response_format="plain",
            top_k=3,
            delivery="conversation",
            document_type="docx",
            attachment=None,
        ))
        payload = json.loads(response.body)
        artifact_id = payload["artifact"]["url"].rsplit("/", 1)[-1]
        download = asyncio.run(chat_artifact(artifact_id))

        self.assertEqual(payload["artifact"]["filename"], "libra-assist-answer.pdf")
        self.assertEqual(ask.await_args.args[6], "bullet_list")
        self.assertTrue(download.body.startswith(b"%PDF"))
        self.assertTrue(
            download.headers["content-disposition"].startswith("attachment;")
        )

    def test_generated_document_can_use_a_source_filename(self) -> None:
        generated = generate(
            "pdf",
            "Source content",
            {},
            filename_stem="10_required_company_documents",
        )

        self.assertEqual(
            generated.filename,
            "10_required_company_documents.pdf",
        )

    def test_speech_text_removes_numeric_citations_only(self) -> None:
        cleaned = speech_text(
            "Actul este necesar [1]. Termenul este 30 zile [2, 3]. "
            "Folosiți politica [KYC]."
        )

        self.assertEqual(
            cleaned,
            "Actul este necesar. Termenul este 30 zile. Folosiți politica [KYC].",
        )

    @patch("app.main.rag_api.speak", new_callable=AsyncMock)
    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_conversation_request_can_infer_spoken_answer(self, ask, speak) -> None:
        ask.return_value = {
            "answer": "Documentul de identitate este necesar.",
            "agent": {"display_name": "Motrun Onboarding"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 20},
            "fact_check": None,
            "response_format": "plain",
        }
        speak.return_value = b"RIFF-test-audio"

        response = asyncio.run(chat_message(
            message="Vreau să îmi răspunzi vocal la această întrebare.",
            history="[]",
            use_rag=True,
            fact_check=False,
            agent="motrun-onboarding",
            agent_mode="local",
            response_format="plain",
            top_k=3,
            delivery="conversation",
            document_type="pdf",
            attachment=None,
        ))
        payload = json.loads(response.body)
        artifact_id = payload["artifact"]["url"].rsplit("/", 1)[-1]
        audio = asyncio.run(chat_artifact(artifact_id))

        self.assertEqual(payload["artifact"]["kind"], "speech")
        speak.assert_awaited_once_with("Documentul de identitate este necesar.")
        self.assertEqual(audio.media_type, "audio/wav")
        self.assertTrue(
            audio.headers["content-disposition"].startswith("inline;")
        )

    @patch("app.main.rag_api.speak", new_callable=AsyncMock)
    @patch("app.main.rag_api.ask", new_callable=AsyncMock)
    def test_vocal_and_pdf_request_produces_both_artifacts(self, ask, speak) -> None:
        ask.return_value = {
            "answer": "Actul de identitate este necesar [1].",
            "agent": {"display_name": "Motrun Onboarding"},
            "provider": "azure",
            "model": "gpt-5-mini",
            "usage": {"total_tokens": 20},
            "fact_check": None,
            "response_format": "plain",
        }
        speak.return_value = b"RIFF-test-audio"

        response = asyncio.run(chat_message(
            message="Răspunde vocal și generează și un PDF.",
            history="[]",
            use_rag=True,
            fact_check=False,
            agent="motrun-onboarding",
            agent_mode="local",
            response_format="plain",
            top_k=3,
            delivery="conversation",
            document_type="docx",
            attachment=None,
        ))
        payload = json.loads(response.body)

        self.assertEqual(
            {artifact["kind"] for artifact in payload["artifacts"]},
            {"speech", "document"},
        )
        self.assertTrue(
            next(
                artifact["filename"]
                for artifact in payload["artifacts"]
                if artifact["kind"] == "document"
            ).endswith(".pdf")
        )
        speak.assert_awaited_once_with("Actul de identitate este necesar.")
        self.assertEqual(ask.await_args.kwargs["delivery"], "speech_document")
        self.assertEqual(ask.await_args.kwargs["document_type"], "pdf")

    @patch("app.main.rag_api.source", new_callable=AsyncMock)
    def test_grounding_source_can_be_downloaded_as_pdf(self, source) -> None:
        source.return_value = {
            "source": "10_required_company_documents",
            "filename": "10_required_company_documents.md",
            "title": "Required company documents",
            "content": "# Documents\n\n- Registration certificate",
        }

        response = asyncio.run(chat_source_download(
            "10_required_company_documents",
            format="pdf",
        ))

        self.assertTrue(response.body.startswith(b"%PDF"))
        self.assertIn(
            'filename="10_required_company_documents.pdf"',
            response.headers["content-disposition"],
        )


if __name__ == "__main__":
    unittest.main()
