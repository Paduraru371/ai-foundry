from __future__ import annotations

import unittest

from app.chunking import chunk, chunk_heading


class HeadingChunkingTests(unittest.TestCase):
    def test_frontmatter_title_and_section_are_added_as_context(self) -> None:
        text = """---
title: Account eligibility
product: onboarding
---

# Retail accounts

Customers must be at least 18 years old.

## Limits

A customer may hold three current accounts.
"""
        chunks = chunk_heading(text, size=500, overlap=40)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(piece.startswith("Document: Account eligibility\n") for piece in chunks))
        self.assertIn("Section: Retail accounts > Limits", chunks[1])
        self.assertIn("Order: section 2/2, part 1/1", chunks[1])
        self.assertIn("## Limits", chunks[1])
        self.assertNotIn("product: onboarding", "\n".join(chunks))

    def test_heading_is_repeated_when_a_long_section_is_split(self) -> None:
        text = """# Verification

First sentence contains the initial verification requirement. Second sentence
contains another important verification requirement. Third sentence contains
the final verification requirement.
"""
        chunks = chunk_heading(text, size=120, overlap=0, document_title="Remote onboarding")

        self.assertGreater(len(chunks), 1)
        for index, piece in enumerate(chunks, start=1):
            self.assertIn("Document: Remote onboarding", piece)
            self.assertIn("Section: Verification", piece)
            self.assertIn(f"part {index}/{len(chunks)}", piece)
            self.assertIn("# Verification", piece)

    def test_dispatcher_accepts_heading_strategy(self) -> None:
        chunks = chunk(
            "# Fees\n\nThe opening fee is £7.50.",
            "heading",
            size=200,
            overlap=20,
            per_chunk=3,
            threshold=0.75,
            document_title="Fee schedule",
        )

        self.assertEqual(len(chunks), 1)
        self.assertIn("Document: Fee schedule", chunks[0])


if __name__ == "__main__":
    unittest.main()
