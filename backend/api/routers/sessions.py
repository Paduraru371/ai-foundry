"""Persistent conversation session endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...memory import session_store
from ...schemas import SessionCreate, SessionDetail, SessionSummary

router = APIRouter(prefix="/sessions", tags=["5 · sessions & memory"])


@router.post("", response_model=SessionDetail)
def session_create(request: SessionCreate) -> SessionDetail:
    return SessionDetail(**session_store.create(request.title))


@router.get("", response_model=list[SessionSummary])
def session_list() -> list[SessionSummary]:
    return [SessionSummary(**item) for item in session_store.list()]


@router.get("/{session_id}", response_model=SessionDetail)
def session_detail(session_id: str) -> SessionDetail:
    result = session_store.get(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionDetail(**result)


@router.delete("/{session_id}")
def session_delete(session_id: str) -> dict[str, bool]:
    deleted = session_store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": True}
