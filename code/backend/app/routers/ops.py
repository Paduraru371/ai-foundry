"""Health and effective application configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ..agents.persona import available_names
from ..api_dependencies import store
from ..config import settings
from ..schemas import Health

router = APIRouter()


@router.get("/health", response_model=Health, tags=["ops"])
def health() -> Health:
    return Health(
        status="ok",
        qdrant="ok" if store.ping() else "unreachable",
        qdrant_url=settings.qdrant_url,
        llm={
            "provider": settings.llm_provider,
            "model": {
                "lmstudio": settings.lmstudio_model,
                "openai": settings.openai_model,
                "anthropic": settings.anthropic_model,
                "azure": settings.azure_ai_chat_deployment,
            }.get(settings.llm_provider, "?"),
        },
        embeddings={
            "provider": settings.embedding_provider,
            "model": {
                "lmstudio": settings.lmstudio_embedding_model,
                "openai": settings.openai_embedding_model,
                "azure": settings.azure_ai_embedding_deployment,
            }.get(settings.embedding_provider, "?"),
        },
        agents={
            "mode": settings.agent_mode,
            "default_persona": settings.agent_persona,
            "available": available_names(),
            "foundry_agent_id": settings.foundry_agent_id or None,
        },
        speech={
            "configured": bool(
                settings.azure_speech_key and settings.azure_speech_region
            ),
            "region": settings.azure_speech_region or None,
            "voice": settings.azure_speech_voice,
        },
    )


@router.get("/config", tags=["ops"])
def config() -> dict:
    def mask(value: str) -> str:
        return (
            value[:6] + "…" + value[-4:]
            if len(value) > 12
            else ("set" if value else "not set")
        )

    return {
        "chunking": {
            "strategy": settings.chunk_strategy,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "sentences_per_chunk": settings.sentences_per_chunk,
            "semantic_threshold": settings.semantic_threshold,
        },
        "retrieval": {
            "top_k": settings.top_k,
            "score_threshold": settings.retrieval_score_threshold,
            "candidate_pool": settings.retrieval_candidate_pool,
            "vector_weight": settings.retrieval_vector_weight,
            "duplicate_threshold": settings.retrieval_duplicate_threshold,
            "collection": settings.qdrant_collection,
            "qdrant_url": settings.qdrant_url,
        },
        "generation": {
            "provider": settings.llm_provider,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        },
        "providers": {
            "lmstudio": {
                "base_url": settings.lmstudio_base_url,
                "model": settings.lmstudio_model,
                "embedding_model": settings.lmstudio_embedding_model,
            },
            "openai": {
                "api_key": mask(settings.openai_api_key),
                "model": settings.openai_model,
                "embedding_model": settings.openai_embedding_model,
            },
            "anthropic": {
                "api_key": mask(settings.anthropic_api_key),
                "model": settings.anthropic_model,
            },
            "azure": {
                "endpoint": settings.azure_ai_endpoint or "not set",
                "auth": settings.azure_ai_auth,
                "api_key": mask(settings.azure_ai_api_key),
                "chat_deployment": settings.azure_ai_chat_deployment,
                "embedding_deployment": settings.azure_ai_embedding_deployment,
            },
        },
    }
