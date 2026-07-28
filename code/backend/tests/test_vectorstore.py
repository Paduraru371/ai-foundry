from __future__ import annotations

import unittest

from app.vectorstore import stable_chunk_id


class StableChunkIdTests(unittest.TestCase):
    def test_same_source_and_index_produce_same_id(self) -> None:
        first_ingest = [stable_chunk_id("fees-2026", index) for index in range(3)]
        second_ingest = [stable_chunk_id("fees-2026", index) for index in range(3)]

        self.assertEqual(first_ingest, second_ingest)

    def test_source_and_index_are_part_of_identity(self) -> None:
        self.assertNotEqual(
            stable_chunk_id("fees-2025", 0),
            stable_chunk_id("fees-2026", 0),
        )
        self.assertNotEqual(
            stable_chunk_id("fees-2026", 0),
            stable_chunk_id("fees-2026", 1),
        )

    def test_blank_source_has_a_stable_fallback(self) -> None:
        self.assertEqual(stable_chunk_id(None, 0), stable_chunk_id("", 0))


if __name__ == "__main__":
    unittest.main()
