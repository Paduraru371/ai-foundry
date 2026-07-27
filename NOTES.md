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