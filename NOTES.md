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

- Unit tests: **6 passed**.
- Loader dry run: **16 documents found**.
- Stable-ID integration check against a temporary Qdrant collection: first ingest
  **2 points**, second ingest **2 points**, with identical IDs.
- API-level heading request: passed; the returned chunk starts with the frontmatter
  title and current Markdown section.
