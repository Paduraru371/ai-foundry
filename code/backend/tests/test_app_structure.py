from __future__ import annotations

import unittest

from app.main import _do_chunk, app, ingest, store
from app.routers.rag import ingest as routed_ingest
from app.schema_agents import AskRequest as DomainAskRequest
from app.schema_rag import ChunkRequest as DomainChunkRequest
from app.schemas import AskRequest, ChunkRequest


class AppStructureTests(unittest.TestCase):
    def test_schema_facade_reexports_domain_models(self) -> None:
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
            "/search",
            "/ask",
            "/agents",
            "/agents/hosted",
            "/agents/hosted/{agent_id}",
            "/agents/{name}",
            "/agents/{name}/deploy",
            "/tools/web-fetch",
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


if __name__ == "__main__":
    unittest.main()
