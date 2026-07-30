"""Endpoints exposing specialist services beside the language model."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ...schemas import (
    ScrapeRequest,
    ScrapeResponse,
    SpeakRequest,
    TranscribeResponse,
)
from ...services import speech, web

router = APIRouter()


@router.post("/tools/web-fetch", response_model=ScrapeResponse, tags=["6 · tools"])
def web_fetch(req: ScrapeRequest) -> ScrapeResponse:
    """Fetch a page and expose the limitations of plain HTML extraction."""
    try:
        result = web.scrape(req.url, max_chars=req.max_chars or 20000)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {error}")
    return ScrapeResponse(**result.__dict__)


@router.post(
    "/tools/speak",
    tags=["6 · tools"],
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "WAV audio",
        }
    },
)
def speak(req: SpeakRequest):
    """Convert text to speech and return a playable WAV file."""
    try:
        audio = speech.synthesize(req.text, req.voice)
    except speech.SpeechUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Speech synthesis failed: {error}",
        )
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="libra-assist.wav"'},
    )


@router.post(
    "/tools/transcribe",
    response_model=TranscribeResponse,
    tags=["6 · tools"],
)
async def transcribe(
    file: UploadFile = File(..., description="WAV, 16 kHz mono, under ~60 s"),
):
    """Convert a short uploaded WAV recording to text."""
    # The endpoint already enforces a small 10 MB bound. Reading the underlying
    # spooled file directly also keeps BytesIO-backed tests from requiring a
    # thread-pool hop.
    audio = file.file.read()
    if not audio:
        raise HTTPException(
            status_code=422,
            detail="The uploaded file is empty.",
        )
    if len(audio) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="The uploaded audio is larger than 10 MB.",
        )
    try:
        result = speech.transcribe(
            audio,
            content_type=file.content_type or "audio/wav",
        )
    except speech.SpeechUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {error}",
        )
    return TranscribeResponse(**result)
