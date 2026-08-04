from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from backend.main import _do_chunk, app, ingest, store
from backend.api.dependencies import chunk_params
from backend.api.routers.rag import (
    _index_fingerprint,
    _source_is_current,
    ingest as routed_ingest,
    source_document,
    source_document_download,
)
from backend.schemas.agents import AskRequest as DomainAskRequest
from backend.schemas.rag import ChunkRequest as DomainChunkRequest
from backend.schemas import AskRequest, ChunkRequest
from backend.schemas import IngestRequest


class AppStructureTests(unittest.TestCase):
    def test_schema_package_reexports_domain_models(self) -> None:
        self.assertIs(AskRequest, DomainAskRequest)
        self.assertIs(ChunkRequest, DomainChunkRequest)

    def test_main_preserves_legacy_handler_aliases(self) -> None:
        self.assertIs(ingest, routed_ingest)
        self.assertIsNotNone(store)

    def test_openapi_contains_every_domain_router(self) -> None:
        expected_paths = {
            "/health",
            "/config",
            "/azure",
            "/chunk",
            "/ingest",
            "/collection",
            "/collection/sources/{source}",
            "/sources/{source}",
            "/sources/{source}/download",
            "/search",
            "/documents/extract",
            "/ask",
            "/generations/{generation_id}/cancel",
            "/sessions",
            "/sessions/{session_id}",
            "/agents",
            "/agents/hosted",
            "/agents/hosted/{agent_id}",
            "/agents/{name}",
            "/agents/{name}/deploy",
            "/tools/web-fetch",
            "/tools/catalog",
            "/tools/select",
            "/tools/speak",
            "/tools/transcribe",
        }

        self.assertEqual(set(app.openapi()["paths"]), expected_paths)

    def test_shared_chunk_helper_remains_available_from_main(self) -> None:
        pieces, params = _do_chunk(ChunkRequest(
            text="# Fees\n\nNo opening fee.",
            strategy="heading",
        ))

        self.assertEqual(params["strategy"], "heading")
        self.assertTrue(pieces[0].startswith("Document:"))

    def test_index_fingerprint_changes_with_content_or_embedding_model(self) -> None:
        params = {
            "strategy": "heading",
            "size": 500,
            "overlap": 80,
            "per_chunk": 3,
            "threshold": 0.75,
            "min_size": 160,
        }
        first = _index_fingerprint(
            IngestRequest(text="First", source="source"),
            params,
            {"provider": "azure", "model": "embedding-a"},
        )
        changed_text = _index_fingerprint(
            IngestRequest(text="Second", source="source"),
            params,
            {"provider": "azure", "model": "embedding-a"},
        )
        changed_model = _index_fingerprint(
            IngestRequest(text="First", source="source"),
            params,
            {"provider": "azure", "model": "embedding-b"},
        )

        self.assertNotEqual(first, changed_text)
        self.assertNotEqual(first, changed_model)

    def test_unchanged_source_skips_chunking_and_embedding(self) -> None:
        request = IngestRequest(
            text="# Documents\n\nIdentity card.",
            source="documents",
            strategy="heading",
        )
        model = {
            "provider": "test",
            "model": "embedding-test",
            "persistent_cache": True,
        }
        fingerprint = _index_fingerprint(request, chunk_params(request), model)
        snapshot = [{
            "id": "point-1",
            "payload": {
                "index": 0,
                "text": "Identity card.",
                "index_fingerprint": fingerprint,
                "index_chunk_count": 1,
            },
        }]
        with (
            patch("backend.api.routers.rag.require_qdrant"),
            patch(
                "backend.api.routers.rag.embedder",
                return_value=SimpleNamespace(describe=lambda: model),
            ),
            patch(
                "backend.api.routers.rag.store.source_snapshot",
                return_value=snapshot,
            ),
            patch(
                "backend.api.routers.rag.store.info",
                return_value={"vector_dimension": 2},
            ),
            patch("backend.api.routers.rag.do_chunk") as do_chunk,
            patch("backend.api.routers.rag.embed") as embed,
        ):
            response = routed_ingest(request)

        self.assertEqual(response.status, "unchanged")
        self.assertEqual(response.point_ids, ["point-1"])
        do_chunk.assert_not_called()
        embed.assert_not_called()

    def test_partial_source_is_never_treated_as_current(self) -> None:
        fingerprint = "same"
        partial = [{
            "id": "only-one",
            "payload": {
                "index_fingerprint": fingerprint,
                "index_chunk_count": 2,
            },
        }]

        self.assertFalse(_source_is_current(partial, fingerprint))

    def test_grounding_source_can_be_viewed_and_downloaded(self) -> None:
        source = "10_required_company_documents"
        document = source_document(source)
        download = source_document_download(source)

        self.assertEqual(document["filename"], f"{source}.md")
        self.assertIn("company", document["content"].casefold())
        self.assertTrue(download.body.startswith(b"---"))
        self.assertIn("attachment;", download.headers["content-disposition"])

    def test_non_corpus_and_excluded_sources_cannot_be_opened(self) -> None:
        for source in ("questions", "README", ".."):
            with self.subTest(source=source), self.assertRaises(HTTPException) as raised:
                source_document(source)
            self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
