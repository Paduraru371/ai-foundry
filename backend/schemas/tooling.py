"""Public API contracts for tool discovery and dry-run selection."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ToolCatalogItem(BaseModel):
    name: str
    title: str
    description: str
    category: str
    phase: Literal["pre", "retrieval", "post", "delivery"]
    execution: Literal["local", "pipeline"]
    automatic: bool


class ToolCatalogResponse(BaseModel):
    count: int
    tools: list[ToolCatalogItem]


class ToolSelectionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=20_000)
    use_rag: bool = True
    shared_memory: bool = True
    has_attachment: bool = False
    fact_check: bool = False
    delivery: Literal["conversation", "speech", "document", "speech_document"] = "conversation"
    requested_tools: list[str] = Field(default_factory=list, max_length=20)
    allowed_tools: list[str] = Field(default_factory=list, max_length=50)


class ToolSelectionResponse(BaseModel):
    selector: str
    multi_tool: bool
    calls: list[dict]
