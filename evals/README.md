# Result cross-checks

`onboarding_retrieval.json` is the golden retrieval set. Each case maps a
question to one or more acceptable source documents.

Retrieval-only evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py
```

The command reports:

- Hit@K — whether an expected source appears in the returned results;
- MRR — how high the first expected source appears;
- failed case identifiers and the actual source order.

Full answer evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_results.py --answers --llm-judge `
  --output runtime\evaluation-full.json
```

With `--answers`, each answer is cross-checked using embeddings:

- question versus retrieved evidence;
- every answer claim versus the closest evidence passage.

With `--llm-judge`, a separate strict model also scores relevance,
groundedness, completeness, and refusal correctness. This option adds model
calls and cost. Embedding similarity is a regression signal rather than proof
of factual entailment, so the LLM judge complements it.

Default quality gates are Hit@4 ≥ 0.85 and MRR ≥ 0.70. The process exits with
code 1 when a gate or enabled answer check fails, making it suitable for CI.
