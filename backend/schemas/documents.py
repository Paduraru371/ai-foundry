"""Uploaded-document extraction schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentExtractionResponse(BaseModel):
    filename: str
    extension: str
    content_type: str
    size_bytes: int
    text: str
    characters: int
    estimated_tokens: int
    pages_or_slides: int | None = None
    truncated: bool = False
    warnings: list[str] = Field(default_factory=list)
    saved_path: str | None = None
