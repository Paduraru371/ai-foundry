"""Schemas for operational status, Azure inspection, and specialist tools."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AzureDeployment(BaseModel):
    name: str
    model: Optional[str] = None
    version: Optional[str] = None
    sku: Optional[str] = None
    capacity: Optional[int] = None
    state: Optional[str] = None


class AzureDeployments(BaseModel):
    available: bool
    reason: Optional[str] = None
    items: list[AzureDeployment] = Field(default_factory=list)


class AzureStatus(BaseModel):
    configured: bool
    auth: str = Field(description="identity (Entra) or key")
    auth_note: Optional[str] = None
    resource: Optional[str] = None
    resource_group: Optional[str] = None
    project: Optional[str] = None
    location: Optional[str] = None
    subscription_id: Optional[str] = None
    inference_endpoint: Optional[str] = None
    project_endpoint: Optional[str] = None
    openai_endpoint: Optional[str] = None
    chat_deployment: Optional[str] = None
    embedding_deployment: Optional[str] = None
    foundry_url: Optional[str] = None
    portal_url: Optional[str] = None
    deployments: AzureDeployments


class ScrapeRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "url": "https://learn.microsoft.com/azure/ai-foundry/what-is-azure-ai-foundry",
    }]}}

    url: str = Field(..., description="Page to fetch and strip to text")
    max_chars: Optional[int] = Field(None, ge=200, le=200000)


class ScrapeResponse(BaseModel):
    url: str
    status_code: int
    title: Optional[str] = None
    text: str
    chars: int
    approx_tokens: int
    warnings: list[str] = Field(
        description="Everything the naive approach could not handle"
    )
    stats: dict


class SpeakRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "text": "Your card was blocked after three failed PIN attempts.",
    }]}}

    text: str = Field(..., min_length=1, max_length=3000)
    voice: Optional[str] = Field(
        None,
        description="Neural voice name; defaults to AZURE_SPEECH_VOICE",
    )


class TranscribeResponse(BaseModel):
    status: Optional[str] = None
    text: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class Health(BaseModel):
    status: str
    qdrant: str
    qdrant_url: str
    llm: dict
    embeddings: dict
    agents: dict = Field(default_factory=dict)
    speech: dict = Field(default_factory=dict)
