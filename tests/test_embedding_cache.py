from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.core.embedding_cache import EmbeddingCache
from backend.core.embeddings import Embedder


class _FakeEmbeddingsApi:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str]):
        self.calls.append(list(input))
        return SimpleNamespace(data=[
            SimpleNamespace(embedding=[float(len(text)), float(len(model))])
            for text in input
        ])


class EmbeddingCacheTests(unittest.TestCase):
    def test_vectors_are_deduplicated_and_survive_a_new_embedder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "embeddings.sqlite3"
            first_api = _FakeEmbeddingsApi()
            first = Embedder(
                "openai",
                "model-a",
                SimpleNamespace(embeddings=first_api),
                EmbeddingCache(path),
            )

            vectors = first.embed(["same text", "same text", "other"])

            second_api = _FakeEmbeddingsApi()
            second = Embedder(
                "openai",
                "model-a",
                SimpleNamespace(embeddings=second_api),
                EmbeddingCache(path),
            )
            cached_vectors = second.embed(["other", "same text"])

        self.assertEqual(first_api.calls, [["same text", "other"]])
        self.assertEqual(second_api.calls, [])
        self.assertEqual(cached_vectors, [vectors[2], vectors[0]])

    def test_model_name_is_part_of_the_cache_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "embeddings.sqlite3"
            first_api = _FakeEmbeddingsApi()
            Embedder(
                "openai",
                "model-a",
                SimpleNamespace(embeddings=first_api),
                EmbeddingCache(path),
            ).embed(["same text"])
            second_api = _FakeEmbeddingsApi()
            Embedder(
                "openai",
                "model-b",
                SimpleNamespace(embeddings=second_api),
                EmbeddingCache(path),
            ).embed(["same text"])

        self.assertEqual(second_api.calls, [["same text"]])


if __name__ == "__main__":
    unittest.main()
