"""Document upload and extraction endpoints."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ...schemas.documents import DocumentExtractionResponse
from ...services import documents

router = APIRouter()


@router.post(
    "/documents/extract",
    response_model=DocumentExtractionResponse,
    tags=["2 · ingestion"],
)
async def extract_document(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
) -> DocumentExtractionResponse:
    content = await file.read()
    try:
        result = documents.extract(
            file.filename or "document",
            content,
            file.content_type or "application/octet-stream",
        )
        if session_id:
            result.saved_path = documents.save_upload(
                session_id,
                result.filename,
                content,
            )
    except documents.DocumentExtractionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return DocumentExtractionResponse(**result.public())
