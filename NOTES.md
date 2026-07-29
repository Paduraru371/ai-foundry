# Assignment 2 Notes

## Chunk Counts

- Static: 6
- Sentence: 4
- Dynamic: 5
- Semantic: 10

## Part 3

### 1. Embedding dimensions
The embeddings have **1536 dimensions**, according to the `vector_dimension` value returned by the ingest endpoint.

### 2. Off-topic query
The highest score was **0.2147**. Since the query was unrelated to the indexed content, the result was not really relevant, just the closest match available.

### 3. What is added when `use_rag` is enabled?
With `use_rag = true`, the prompt includes:

- a **CONTEXT** section with the retrieved passages
- similarity scores
- references (`[1]`, `[2]`, `[3]`)
- the original question

Without RAG, only the question is sent.

### 4. Where can the `lyrical` agent run?
The `lyrical` agent can run **locally** because it is listed in the local persona configuration.

During testing, `runs_on` was `unknown` and `foundry.available` was `false`, so the hosted Foundry status could not be verified.

## Assignment 3 — Part 4

### Implemented ingestion improvements

1. **Heading-aware chunking:** the new `heading` strategy removes YAML frontmatter
   from embedded prose, splits Markdown on headings, retains the full nested section
   path, and repeats the heading when a long section needs multiple chunks.
2. **Chunk context and hierarchy:** every heading-aware chunk begins with
   `Document: <title>`, `Section: <H1 > H2 > H3 path>`, and an explicit
   `Order: section x/y, part a/b`. The title comes from the loader/frontmatter;
   the response chunk index remains the global document order.
3. **Stable chunk IDs:** Qdrant IDs are deterministic UUIDv5 values derived from
   `source + chunk index`. Re-ingesting the same source therefore replaces matching
   points instead of assigning fresh IDs.
4. **Corpus loader:** from `code/backend`, run:

   ```bash
   uv run python scripts/ingest_corpus.py
   ```

   The loader finds all corpus Markdown files, ignores `data/README.md`, and uses the
   `heading` strategy by default. `--dry-run` previews the 16 documents.

### Verification

- Unit tests: **15 passed**.
- Loader dry run: **16 documents found**.
- Before/after stable-ID comparison against an in-memory Qdrant collection, using
  the same two-chunk document twice:
  - **Before** (random UUIDs): **2 points after the first ingest, 4 after the
    second** (**+100%**, duplicated).
  - **After** (deterministic UUIDv5 IDs): **2 points after the first ingest, 2
    after the second** (**0% growth**, replaced in place).
- API-level heading request: passed; the returned chunk starts with the frontmatter
  title and current Markdown section.

## Assignment 3 — Part 5

1. **Re-ranking** retrieves at least 10 candidates for `/ask`, improves their initial
   order with cosine similarity plus exact query-term coverage, then asks the
   configured model to choose the final passages. This fixes cases where semantically
   broad text ranked above a passage containing the actual policy terms; invalid
   model output safely falls back to the deterministic order. Demonstration question:
   **"What is the business onboarding fee?"**
2. **Deduplication and diversity** remove near-identical passages and apply a small
   similarity penalty to the remaining candidates, fixing wasted context slots.
   Demonstration question: **"When does an incomplete application expire?"**
3. **Score threshold** drops cosine hits below **0.30**; `/search` reports that
   nothing relevant was found and `/ask` stops before the LLM can invent an answer.
   Demonstration question: **"What is the weather in Cluj?"**

The retrieval unit cases measured all three effects: an exact-term hit with cosine
**0.58** moved above a generic hit at **0.60** after re-ranking; two identical
passages plus one different passage became **2** diverse results instead of **3**;
and a weak hit at **0.29** produced **0** results at the **0.30** threshold.
