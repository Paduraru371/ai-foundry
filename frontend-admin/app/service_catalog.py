"""Display-ready service status data from backend responses"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServiceStatus:
    """Database or model displayed on the overview page"""

    category: str
    provider: str
    model: str
    status: str
    tone: str
    detail: str
    icon: str


# Fallback names for when /config is unavailable
KNOWN_MODELS = {
    "llm": {
        "azure": "gpt-5.1",
        "openai": "gpt-5.4-nano",
        "anthropic": "claude-sonnet-5",
        "lmstudio": "google/gemma-3-4b",
    },
    "embeddings": {
        "azure": "text-embedding-3-small",
        "openai": "text-embedding-3-small",
        "lmstudio": "text-embedding-nomic-embed-text-v1.5",
    },
}

MODEL_FIELDS = {
    "llm": {
        "azure": "chat_deployment",
        "openai": "model",
        "anthropic": "model",
        "lmstudio": "model",
    },
    "embeddings": {
        "azure": "embedding_deployment",
        "openai": "embedding_model",
        "lmstudio": "embedding_model",
    },
}

PROVIDER_LABELS = {
    "azure": "Azure",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "lmstudio": "LM Studio",
}


def _has_credentials(provider: str, values: dict[str, Any]) -> bool:
    """Check configuration presence"""
    if provider == "lmstudio":
        return bool(values.get("base_url"))
    
    if provider in {"openai", "anthropic"}:
        return values.get("api_key") not in {None, "", "not set"}
    
    if provider == "azure":
        endpoint_ready = values.get("endpoint") not in {None, "", "not set"}
        auth = values.get("auth")
        key_ready = values.get("api_key") not in {None, "", "not set"}
        
        return endpoint_ready and (auth == "identity" or key_ready)
    
    return False


def _model_services(
    category: str,
    health: dict[str, Any] | None,
    config: dict[str, Any] | None,
) -> list[ServiceStatus]:
    provider_config = (config or {}).get("providers", {})
    active_provider = (health or {}).get(category, {}).get("provider")
    services: list[ServiceStatus] = []

    for provider, fallback_model in KNOWN_MODELS[category].items():
        values = provider_config.get(provider, {})
        field = MODEL_FIELDS[category][provider]
        model = values.get(field) or fallback_model

        if config is None:
            status, tone, detail = "Unavailable", "error", "Backend config could not be loaded"
        elif not _has_credentials(provider, values):
            status, tone, detail = "Not configured", "error", "Credentials or endpoint missing"
        elif provider == active_provider:
            status, tone, detail = "Active", "ok", "Selected by the backend"
        else:
            status, tone = "Configured", "configured"
            detail = "Endpoint configured; connectivity not tested"

        services.append(
            ServiceStatus(
                category=category,
                provider=PROVIDER_LABELS[provider],
                model=str(model),
                status=status,
                tone=tone,
                detail=detail,
                icon="AI" if category == "llm" else "E",
            )
        )
    return services


def build_service_catalog(
    health: dict[str, Any] | None,
    config: dict[str, Any] | None,
) -> dict[str, list[ServiceStatus]]:
    """Return all databases and models known by the backend code"""
    qdrant_status = (health or {}).get("qdrant", "unavailable")
    qdrant_ok = qdrant_status == "ok"
    
    database = ServiceStatus(
        category="database",
        provider="Qdrant",
        model=(health or {}).get("qdrant_url", "http://localhost:7833"),
        status="OK" if qdrant_ok else str(qdrant_status).replace("_", " ").title(),
        tone="ok" if qdrant_ok else "error",
        detail="Vector database reachable" if qdrant_ok else "Vector database is not reachable",
        icon="DB",
    )
    speech = (health or {}).get("speech", {})

    def speech_service(capability: str, label: str, icon: str) -> ServiceStatus:
        values = speech.get(capability, {})
        configured = bool(values.get("configured", speech.get("configured", False)))
        return ServiceStatus(
            category="speech",
            provider=label,
            model=str(
                speech.get("voice")
                if capability == "tts"
                else speech.get("region") or speech.get("endpoint") or "Azure Speech"
            ),
            status="Configured" if configured else "Not configured",
            tone="configured" if configured else "error",
            detail=str(
                values.get("detail")
                or speech.get("source")
                or "Azure Speech credentials or endpoint missing"
            ),
            icon=icon,
        )

    return {
        "databases": [database],
        "llms": _model_services("llm", health, config),
        "embeddings": _model_services("embeddings", health, config),
        "speech": [
            speech_service("tts", "Text to speech", "TTS"),
            speech_service("stt", "Speech to text", "STT"),
        ],
    }
