from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.ingest_corpus import (
    corpus_files,
    load_manifest,
    save_manifest,
)


class IngestCorpusTests(unittest.TestCase):
    def test_questions_and_readme_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            for name in ("onboarding.md", "questions.md", "README.md"):
                (data_dir / name).write_text(f"# {name}", encoding="utf-8")

            names = [path.name for path in corpus_files(data_dir)]

        self.assertEqual(names, ["onboarding.md"])

    def test_incremental_manifest_round_trip_is_scoped_to_data_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_dir = root / "data"
            data_dir.mkdir()
            manifest = root / "runtime" / "manifest.json"
            documents = {
                "onboarding": {
                    "fingerprint": "abc",
                    "chunks": 3,
                    "strategy": "heading",
                }
            }

            save_manifest(manifest, data_dir.resolve(), documents)
            loaded = load_manifest(manifest, data_dir.resolve())
            other = load_manifest(manifest, (root / "other").resolve())

        self.assertEqual(loaded["managed_sources"], ["onboarding"])
        self.assertEqual(loaded["documents"], documents)
        self.assertEqual(other["managed_sources"], [])


if __name__ == "__main__":
    unittest.main()
