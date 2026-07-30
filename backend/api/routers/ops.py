"""Health and effective application configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ...agents.persona import available_names
from ...core.config import settings
from ...schemas import Health
from ...services import speech
from ..dependencies import store

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
        speech=speech.describe(),
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
            "chunk_min_size": settings.chunk_min_size,
            "sentences_per_chunk": settings.sentences_per_chunk,
            "semantic_threshold": settings.semantic_threshold,
        },
        "retrieval": {
            "top_k": settings.top_k,
            "score_threshold": settings.retrieval_score_threshold,
            "candidate_pool": settings.retrieval_candidate_pool,
            "vector_weight": settings.retrieval_vector_weight,
            "duplicate_threshold": settings.retrieval_duplicate_threshold,
            "max_per_source": settings.retrieval_max_per_source,
            "collection": settings.qdrant_collection,
            "qdrant_url": settings.qdrant_url,
        },
        "generation": {
            "provider": settings.llm_provider,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        },
        "documents": {
            "max_upload_bytes": settings.max_upload_bytes,
            "max_extracted_characters": settings.max_document_chars,
            "supported": ["PDF", "DOCX", "PPTX", "TXT", "Markdown", "CSV", "JSON", "HTML", "code"],
        },
        "memory": {
            "session_db_path": settings.session_db_path,
            "history_max_messages": settings.history_max_messages,
            "history_max_tokens": settings.history_max_tokens,
            "session_summary_max_chars": settings.session_summary_max_chars,
            "shared_memory_max_chars": settings.shared_memory_max_chars,
            "shared_memory_session_limit": settings.shared_memory_session_limit,
            "shared_memory_min_score": settings.shared_memory_min_score,
            "chat_upload_dir": settings.chat_upload_dir,
        },
        "pricing_estimate": {
            "model": "Azure GPT-5-mini",
            "currency": "USD",
            "unit": "1M tokens",
            "input": settings.azure_gpt5_mini_input_price,
            "cached_input": settings.azure_gpt5_mini_cached_input_price,
            "output": settings.azure_gpt5_mini_output_price,
            "note": "Estimate only; Azure billing varies by region and deployment type.",
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
