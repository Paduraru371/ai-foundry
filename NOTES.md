# Assignment 2 — Part 3 notes

## Chunk counts

Using the same `sampleText` from the Postman collection:

- Static: **6**
- Sentence: **4**
- Dynamic: **5**
- Semantic: **10**

The dynamic ingestion stored **5** chunks, and `GET /collection` reported the
same `points_count`.

## Acceptance answers

1. **How many dimensions does an embedding have here?**  
   **1536 dimensions.** The field is `vector_dimension` in the response from
   `POST /ingest`.

2. **What score did the off-topic query get, and what does that tell you?**  
   The three returned `hits[].score` values were **0.2147**, **0.1135**, and
   **0.0835** (top score: **0.2147**). Retrieval still returns the nearest
   chunks even when none is relevant, so these low scores show that the result
   should not be treated as meaningful evidence.

3. **What exactly is added to the prompt when `use_rag` is `true`?**  
   The response field is `prompt_sent`. Without RAG it contained only the
   question. With RAG it added a `CONTEXT — retrieved passages, most similar
   first:` block containing three numbered passages (`[1]`, `[2]`, `[3]`),
   each passage's similarity score and text, followed by a `QUESTION:` block
   containing the original question.

4. **Where can the `lyrical` agent run, and how do you know?**  
   It can definitely run **locally**, because it is returned in
   `GET /agents` from the local persona file. In this run, its `runs_on` field
   was **`unknown`**, rather than `local` or `both`, because the accompanying
   `foundry.available` field was `false` and `foundry.reason` reported that
   `AZURE_AI_PROJECT_ENDPOINT` was not configured. Therefore the API could not
   determine whether a hosted Foundry copy also exists.

## Run notes

- Every request in folders 0–4 was sent in order; the collection reset was
  deferred until folders 3 and 4 were complete.
- The first three requests in folder 5 were sent. The Foundry deployment
  request returned HTTP 503 because `AZURE_AI_PROJECT_ENDPOINT` is empty.
- The final reset succeeded, and `points_count` was **0** afterward.
