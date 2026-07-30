"""Schemas for persistent chat sessions and shared memory."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = Field("New conversation", min_length=1, max_length=120)


class SessionMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    metadata: dict = Field(default_factory=dict)


class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    turn_count: int = 0
    last_message: str = ""


class SessionDetail(SessionSummary):
    summary: str = ""
    messages: list[SessionMessage] = Field(default_factory=list)


class MemoryContextInfo(BaseModel):
    current_summary_used: bool = False
    shared_sessions_used: int = 0
    shared_session_ids: list[str] = Field(default_factory=list)
    compaction: Optional[str] = None
