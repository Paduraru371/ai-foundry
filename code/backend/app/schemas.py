"""Stable schema facade.

Models are grouped by responsibility in ``schema_rag``, ``schema_agents``, and
``schema_ops``. Re-exporting them here preserves existing imports such as
``from app.schemas import AskRequest``.
"""
from .schema_agents import (
    AgentInfo,
    AgentListResponse,
    AskRequest,
    AskResponse,
    FoundryAvailability,
    HostedAgent,
    PersonaSummary,
    Usage,
)
from .schema_ops import (
    AzureDeployment,
    AzureDeployments,
    AzureStatus,
    Health,
    ScrapeRequest,
    ScrapeResponse,
    SpeakRequest,
    TranscribeResponse,
)
from .schema_rag import (
    ChunkInfo,
    ChunkRequest,
    ChunkResponse,
    CollectionInfo,
    IngestRequest,
    IngestResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
    Strategy,
)

__all__ = [
    "AgentInfo",
    "AgentListResponse",
    "AskRequest",
    "AskResponse",
    "AzureDeployment",
    "AzureDeployments",
    "AzureStatus",
    "ChunkInfo",
    "ChunkRequest",
    "ChunkResponse",
    "CollectionInfo",
    "FoundryAvailability",
    "Health",
    "HostedAgent",
    "IngestRequest",
    "IngestResponse",
    "PersonaSummary",
    "ScrapeRequest",
    "ScrapeResponse",
    "SearchHit",
    "SearchRequest",
    "SearchResponse",
    "SpeakRequest",
    "Strategy",
    "TranscribeResponse",
    "Usage",
]
