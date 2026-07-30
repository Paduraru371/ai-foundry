"""RAG Teaching API application assembly.

Endpoint implementations live in domain routers. This module owns only FastAPI
configuration and keeps compatibility aliases for code that imported handlers
or shared helpers from ``backend.main``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.dependencies import (
    chunk_infos as _chunk_infos,
    chunk_params as _chunk_params,
    do_chunk as _do_chunk,
    embed as _embed,
    embedder as _embedder,
    require_qdrant as _require_qdrant,
    store,
)
from .api.routers import agents, azure, documents, generation, ops, rag, sessions, tools
from .api.routers.documents import extract_document
from .api.routers.agents import (
    agent_deploy,
    agent_detail,
    agent_hosted_delete,
    agents_hosted,
    agents_list,
)
from .api.routers.azure import azure_status
from .api.routers.generation import ask
from .api.routers.ops import config, health
from .api.routers.rag import (
    chunk_only,
    collection_info,
    collection_reset,
    ingest,
    search,
)
from .api.routers.tools import speak, transcribe, web_fetch

app = FastAPI(
    title="RAG Teaching API",
    description=(
        "A backend built to *show* Retrieval-Augmented Generation, step by step: "
        "chunk text (five strategies), embed and store in Qdrant, retrieve with "
        "similarity scores, and answer with or without augmentation — the exact "
        "final prompt is always returned. Libra Bank Academy · AI Engineering on Azure."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ops.router)
app.include_router(azure.router)
app.include_router(rag.router)
app.include_router(documents.router)
app.include_router(generation.router)
app.include_router(sessions.router)
app.include_router(agents.router)
app.include_router(tools.router)

__all__ = [
    "agent_deploy",
    "agent_detail",
    "agent_hosted_delete",
    "agents_hosted",
    "agents_list",
    "app",
    "ask",
    "azure_status",
    "chunk_only",
    "collection_info",
    "collection_reset",
    "config",
    "extract_document",
    "health",
    "ingest",
    "search",
    "speak",
    "store",
    "transcribe",
    "web_fetch",
]
