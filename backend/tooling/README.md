# Chat and onboarding tools

This package keeps tool discovery, selection and execution separate from the HTTP
and LLM layers.

- `catalog.py` is the source of truth for available tools.
- `selector.py` builds an explainable plan and may select several tools.
- `executors.py` contains deterministic, side-effect-free local implementations.
- `orchestrator.py` is the integration facade.

Tools marked `pipeline` are already performed by established application stages
(RAG, memory, fact-check, speech and document export). The selector records why
they are needed; it does not duplicate those stages. Local tool output is a routing
hint only. Exact onboarding requirements must still come from retrieved bank
documents, and no tool may make a final KYC/AML approval decision.
