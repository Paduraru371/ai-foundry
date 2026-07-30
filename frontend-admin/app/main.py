"""Server admin console """
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_client import BackendError, rag_api
from .artifacts import artifact_store
from .document_export import generate as generate_document
from .forms import chunk_payload, form_values
from .service_catalog import build_service_catalog

BASE_DIR = Path(__file__).resolve().parent.parent

# the route handlers
# FastAPI top level app definition
app = FastAPI(title="Libra Assist Admin", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def render(
    request: Request,
    template: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    """Adds values used by every page to the Jinja context"""
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"backend_online": context.get("backend_online", True), **context},
        status_code=status_code,
    )


def error_context(exc: BackendError) -> dict[str, Any]:
    """Convert a backend exception into values understood by the html templates"""
    return {"error": exc.message, "error_status": exc.status_code}


def chat_defaults() -> dict[str, Any]:
    return {
        "agent": "default",
        "agent_mode": "local",
        "agents": [],
        "hosted_only": [],
        "foundry": None,
    }


async def load_agents() -> dict[str, Any]:
    """Return the backend agent inventory in a template-friendly shape."""
    data = await rag_api.agents()
    return {
        "agents": data.get("personas", []),
        "hosted_only": data.get("hosted_only", []),
        "foundry": data.get("foundry"),
        "agent_defaults": {
            "agent": data.get("default_persona", "default"),
            "agent_mode": data.get("active_mode", "local"),
        },
    }


# Service overview 
@app.get("/", response_class=HTMLResponse)
async def overview(request: Request) -> HTMLResponse:
    # independent load of health and config for 
    # page load and error reporting
    health_result, config_result = await asyncio.gather(
        rag_api.health(),
        rag_api.config(),
        return_exceptions=True,
    )
    
    health = None if isinstance(health_result, Exception) else health_result
    config = None if isinstance(config_result, Exception) else config_result
    catalog = build_service_catalog(health, config)

    errors = [
        result for result in (health_result, config_result) if isinstance(result, BackendError)
    ]
    
    context: dict[str, Any] = {
        "active_page": "overview",
        "backend_online": health is not None,
        "catalog": catalog,
    }
    
    if errors:
        context["error"] = " | ".join(error.message for error in errors)
        context["error_status"] = errors[0].status_code
    return render(request, "overview.html", **context)


# Knowledge base 
async def knowledge_page(
    request: Request,
    *,
    result: dict[str, Any] | None = None,
    result_type: str | None = None,
    values: dict[str, Any] | None = None,
    error: BackendError | None = None,
    extracted: dict[str, Any] | None = None,
) -> HTMLResponse:
    """Render the shared knowledge page after GET, chunk, ingest or reset"""
    collection = None
    collection_error = None
    
    try:
        collection = await rag_api.collection()
        
    except BackendError as exc:
        collection_error = exc

    context: dict[str, Any] = {
        "active_page": "knowledge",
        "collection": collection,
        "result": result,
        "result_type": result_type,
        "values": values or form_values(),
        "extracted": extracted,
    }
    
    if error:
        context.update(error_context(error))
    elif collection_error:
        context.update(error_context(collection_error))
        
    return render(request, "knowledge.html", **context)


@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge(request: Request) -> HTMLResponse:
    return await knowledge_page(request)


@app.post("/knowledge/chunk", response_class=HTMLResponse)
async def chunk_document(
    request: Request,
    text: str = Form(min_length=1),
    strategy: str = Form(),
    chunk_size: int = Form(ge=50),
    chunk_overlap: int = Form(ge=0),
    source: str = Form(default=""),
) -> HTMLResponse:
    # visible submission values returned to the form
    values = form_values(text, strategy, chunk_size, chunk_overlap, source)
    try:
        result = await rag_api.chunk(chunk_payload(text, strategy, chunk_size, chunk_overlap))
        return await knowledge_page(request, result=result, result_type="chunk", values=values)
    
    except BackendError as exc:
        return await knowledge_page(request, values=values, error=exc)


@app.post("/knowledge/extract", response_class=HTMLResponse)
async def extract_knowledge_document(
    request: Request,
    file: UploadFile = File(...),
) -> HTMLResponse:
    content = await file.read()
    try:
        extracted = await rag_api.extract_document(
            file.filename or "document",
            content,
            file.content_type or "application/octet-stream",
        )
        values = form_values(
            text=extracted["text"],
            source=Path(extracted["filename"]).stem,
        )
        return await knowledge_page(request, values=values, extracted=extracted)
    except BackendError as exc:
        return await knowledge_page(request, error=exc)


@app.post("/knowledge/ingest", response_class=HTMLResponse)
async def ingest_document(
    request: Request,
    text: str = Form(min_length=1),
    strategy: str = Form(),
    chunk_size: int = Form(ge=50),
    chunk_overlap: int = Form(ge=0),
    source: str = Form(default=""),
) -> HTMLResponse:
    values = form_values(text, strategy, chunk_size, chunk_overlap, source)
    try:
        result = await rag_api.ingest(
            chunk_payload(text, strategy, chunk_size, chunk_overlap, source)
        )
        return await knowledge_page(request, result=result, result_type="ingest", values=values)
    
    except BackendError as exc:
        return await knowledge_page(request, values=values, error=exc)


@app.get("/collection/reset", response_class=HTMLResponse)
async def confirm_reset(request: Request) -> HTMLResponse:
    return render(request, "confirm_reset.html", active_page="knowledge")


@app.post("/collection/reset")
async def reset_collection(request: Request) -> HTMLResponse:
    try:
        await rag_api.reset_collection()
        # error for the reset is handled by the knowledge page
        return RedirectResponse("/knowledge?reset=success", status_code=303)
    except BackendError as exc:
        return await knowledge_page(request, error=exc)


# Semantic search 
@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request) -> HTMLResponse:
    return render(request, "search.html", active_page="search", query="", top_k=3)


@app.post("/search", response_class=HTMLResponse)
async def run_search(
    request: Request,
    query: str = Form(min_length=1),
    top_k: int = Form(ge=1, le=50),
) -> HTMLResponse:
    try:
        result = await rag_api.search(query.strip(), top_k)
        # order remains displayed highest-score-first
        result["hits"] = sorted(result["hits"], key=lambda hit: hit["score"], reverse=True)
        
        return render(
            request, "search.html", active_page="search", query=query, top_k=top_k, result=result
        )
        
    except BackendError as exc:
        return render(
            request,
            "search.html",
            active_page="search",
            query=query,
            top_k=top_k,
            **error_context(exc),
        )


# Answer generation
@app.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request) -> HTMLResponse:
    context: dict[str, Any] = {
        "active_page": "ask",
        "question": "",
        "top_k": 3,
        "use_rag": True,
        "speak_answer": False,
        "fact_check": False,
        "agent": "default",
        "agent_mode": "local",
        "response_format": "plain",
        "document": None,
        "agents": [],
        "hosted_only": [],
    }
    try:
        context.update(await load_agents())
        context.update(context.pop("agent_defaults"))
    except BackendError as exc:
        context.update(error_context(exc))
    return render(request, "ask.html", **context)


@app.post("/ask", response_class=HTMLResponse)
async def run_ask(
    request: Request,
    question: str = Form(min_length=1),
    top_k: int = Form(ge=1, le=50),
    use_rag: bool = Form(default=False),
    speak_answer: bool = Form(default=False),
    fact_check: bool = Form(default=False),
    agent: str = Form(default="default"),
    agent_mode: str = Form(default="local"),
    response_format: str = Form(default="plain"),
    document: UploadFile | None = File(default=None),
) -> HTMLResponse:
    context: dict[str, Any] = {
        "active_page": "ask",
        "question": question,
        "top_k": top_k,
        "use_rag": use_rag,
        "speak_answer": speak_answer,
        "fact_check": fact_check,
        "agent": agent,
        "agent_mode": agent_mode,
        "response_format": response_format,
        "document": None,
        "agents": [],
        "hosted_only": [],
    }
    try:
        agent_context = await load_agents()
        agent_context.pop("agent_defaults", None)
        context.update(agent_context)
    except BackendError:
        pass

    extracted = None
    if document and document.filename:
        try:
            content = await document.read()
            extracted = await rag_api.extract_document(
                document.filename,
                content,
                document.content_type or "application/octet-stream",
            )
            context["document"] = extracted
        except BackendError as exc:
            return render(request, "ask.html", **context, **error_context(exc))

    try:
        result = await rag_api.ask(
            question.strip(),
            use_rag,
            top_k,
            agent,
            agent_mode,
            fact_check,
            response_format,
            extracted["text"] if extracted else None,
            extracted["filename"] if extracted else None,
        )
        # retrieved context uses the same order as search
        result["retrieved"] = sorted(
            result.get("retrieved", []), key=lambda hit: hit["score"], reverse=True
        )

        return render(request, "ask.html", result=result, **context)

    except BackendError as exc:
        return render(request, "ask.html", **context, **error_context(exc))


@app.post("/chat/transcribe")
@app.post("/ask/transcribe")
async def transcribe_question(file: UploadFile = File(...)) -> JSONResponse:
    """Turn a browser microphone recording into text for the Ask form."""
    content = await file.read()
    if not content:
        return JSONResponse({"detail": "The recording is empty."}, status_code=422)
    if len(content) > 10 * 1024 * 1024:
        return JSONResponse(
            {"detail": "The recording is larger than 10 MB."},
            status_code=413,
        )
    try:
        result = await rag_api.transcribe(
            file.filename or "question.wav",
            content,
            file.content_type or "audio/wav",
        )
        return JSONResponse(result)
    except BackendError as exc:
        return JSONResponse(
            {"detail": exc.message},
            status_code=exc.status_code or 502,
        )


# Conversational chat
@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
    context: dict[str, Any] = {
        "active_page": "chat",
        **chat_defaults(),
    }
    try:
        context.update(await load_agents())
        context.update(context.pop("agent_defaults"))
    except BackendError as exc:
        context.update(error_context(exc))
    return render(request, "chat.html", **context)


@app.get("/chat/sessions")
async def chat_sessions() -> JSONResponse:
    try:
        return JSONResponse(await rag_api.sessions())
    except BackendError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code or 502)


@app.post("/chat/sessions")
async def chat_session_create() -> JSONResponse:
    try:
        return JSONResponse(await rag_api.create_session())
    except BackendError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code or 502)


@app.get("/chat/sessions/{session_id}")
async def chat_session_detail(session_id: str) -> JSONResponse:
    try:
        return JSONResponse(await rag_api.session(session_id))
    except BackendError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code or 502)


@app.delete("/chat/sessions/{session_id}")
async def chat_session_delete(session_id: str) -> JSONResponse:
    try:
        return JSONResponse(await rag_api.delete_session(session_id))
    except BackendError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code or 502)


@app.post("/chat/message")
async def chat_message(
    message: str = Form(min_length=1),
    history: str = Form(default="[]"),
    session_id: str | None = Form(default=None),
    shared_memory: bool = Form(default=False),
    use_rag: bool = Form(default=False),
    fact_check: bool = Form(default=False),
    agent: str = Form(default="default"),
    agent_mode: str = Form(default="local"),
    response_format: str = Form(default="plain"),
    top_k: int = Form(default=3, ge=1, le=50),
    delivery: str = Form(default="conversation"),
    document_type: str = Form(default="pdf"),
    attachment: UploadFile | None = File(default=None),
) -> JSONResponse:
    if delivery not in {"conversation", "speech", "document"}:
        return JSONResponse({"detail": "Invalid delivery option."}, status_code=422)
    if delivery == "document" and document_type not in {"pdf", "docx", "txt", "md", "json"}:
        return JSONResponse({"detail": "Invalid document type."}, status_code=422)

    try:
        parsed_history = json.loads(history)
        if not isinstance(parsed_history, list):
            raise ValueError
        safe_history = [
            {"role": item["role"], "content": str(item["content"])}
            for item in parsed_history[-20:]
            if isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and item.get("content")
        ]
    except (ValueError, TypeError, KeyError):
        return JSONResponse({"detail": "Invalid conversation history."}, status_code=422)

    extracted = None
    if attachment and attachment.filename:
        try:
            content = await attachment.read()
            extracted = await rag_api.extract_document(
                attachment.filename,
                content,
                attachment.content_type or "application/octet-stream",
                session_id,
            )
        except BackendError as exc:
            return JSONResponse(
                {"detail": exc.message},
                status_code=exc.status_code or 502,
            )

    try:
        result = await rag_api.ask(
            message.strip(),
            use_rag,
            top_k,
            agent,
            agent_mode,
            fact_check,
            response_format,
            extracted["text"] if extracted else None,
            extracted["filename"] if extracted else None,
            safe_history,
            session_id=session_id,
            shared_memory=shared_memory,
            document_path=extracted.get("saved_path") if extracted else None,
        )
        artifact = None
        if delivery == "speech":
            audio = await rag_api.speak(result["answer"])
            artifact_id = artifact_store.put(
                audio,
                "audio/wav",
                "libra-assist-answer.wav",
            )
            artifact = {
                "kind": "speech",
                "url": f"/chat/artifacts/{artifact_id}",
                "filename": "libra-assist-answer.wav",
            }
        elif delivery == "document":
            generated = generate_document(
                document_type,
                result["answer"],
                {
                    "question": message.strip(),
                    "agent": result.get("agent", {}).get("display_name"),
                    "model": result.get("model"),
                    "response_format": result.get("response_format"),
                },
            )
            artifact_id = artifact_store.put(
                generated.content,
                generated.media_type,
                generated.filename,
            )
            artifact = {
                "kind": "document",
                "url": f"/chat/artifacts/{artifact_id}",
                "filename": generated.filename,
            }
        return JSONResponse({
            "answer": result["answer"],
            "agent": result.get("agent"),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "usage": result.get("usage"),
            "fact_check": result.get("fact_check"),
            "augmented": result.get("augmented", False),
            "sources": result.get("retrieved", []),
            "response_format": result.get("response_format"),
            "attachment": (
                {
                    "filename": extracted["filename"],
                    "characters": extracted["characters"],
                    "estimated_tokens": extracted["estimated_tokens"],
                }
                if extracted else None
            ),
            "artifact": artifact,
            "session_id": result.get("session_id"),
            "memory": result.get("memory"),
        })
    except BackendError as exc:
        return JSONResponse(
            {"detail": exc.message},
            status_code=exc.status_code or 502,
        )
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=422)


@app.get("/chat/artifacts/{artifact_id}")
async def chat_artifact(artifact_id: str) -> Response:
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        return Response("Artifact not found or expired.", status_code=404)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f'inline; filename="{artifact.filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


# Agents
@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, detail: str | None = None) -> HTMLResponse:
    context: dict[str, Any] = {
        "active_page": "agents",
        "agents": [],
        "hosted_only": [],
    }
    try:
        context.update(await load_agents())
        context.pop("agent_defaults", None)
        context["azure"] = await rag_api.azure()
        if detail:
            context["detail"] = await rag_api.agent(detail)
    except BackendError as exc:
        context.update(error_context(exc))
    return render(request, "agents.html", **context)


@app.post("/agents/deploy")
async def deploy_agent(request: Request, name: str = Form(min_length=1)) -> HTMLResponse:
    try:
        result = await rag_api.deploy_agent(name)
        message = f"{result.get('action', 'Deployed')} {name} in Foundry."
        return RedirectResponse(
            f"/agents?{urlencode({'notice': message})}", status_code=303
        )
    except BackendError as exc:
        context: dict[str, Any] = {"agents": [], "hosted_only": []}
        try:
            context.update(await load_agents())
            context.pop("agent_defaults", None)
        except BackendError:
            pass
        return render(
            request,
            "agents.html",
            active_page="agents",
            **context,
            **error_context(exc),
        )


@app.post("/agents/hosted/delete")
async def delete_hosted_agent(
    request: Request, agent_id: str = Form(min_length=1), name: str = Form(min_length=1)
) -> HTMLResponse:
    try:
        await rag_api.delete_hosted_agent(agent_id)
        return RedirectResponse(
            f"/agents?{urlencode({'notice': f'Removed {name} from Foundry.'})}",
            status_code=303,
        )
    except BackendError as exc:
        context: dict[str, Any] = {"agents": [], "hosted_only": []}
        try:
            context.update(await load_agents())
            context.pop("agent_defaults", None)
        except BackendError:
            pass
        return render(
            request,
            "agents.html",
            active_page="agents",
            **context,
            **error_context(exc),
        )


# Tools
@app.get("/tools", response_class=HTMLResponse)
async def tools_page(request: Request) -> HTMLResponse:
    return render(
        request,
        "tools.html",
        active_page="tools",
        url="https://example.com",
        max_chars=20000,
        speech_text="Your card was blocked after three failed PIN attempts.",
    )


@app.post("/tools/web-fetch", response_class=HTMLResponse)
async def web_fetch(
    request: Request,
    url: str = Form(min_length=1),
    max_chars: int = Form(ge=200, le=200000),
) -> HTMLResponse:
    try:
        result = await rag_api.web_fetch(url.strip(), max_chars)
        return render(
            request,
            "tools.html",
            active_page="tools",
            url=url,
            max_chars=max_chars,
            speech_text="Your card was blocked after three failed PIN attempts.",
            web_result=result,
        )
    except BackendError as exc:
        return render(
            request,
            "tools.html",
            active_page="tools",
            url=url,
            max_chars=max_chars,
            speech_text="Your card was blocked after three failed PIN attempts.",
            **error_context(exc),
        )


@app.post("/tools/speak")
async def speak(
    text: str = Form(min_length=1), voice: str = Form(default="")
) -> Response:
    try:
        audio = await rag_api.speak(text, voice or None)
        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"Content-Disposition": 'inline; filename="libra-assist.wav"'},
        )
    except BackendError as exc:
        return Response(content=exc.message, status_code=exc.status_code or 502)


@app.post("/tools/transcribe", response_class=HTMLResponse)
async def transcribe(request: Request, file: UploadFile = File(...)) -> HTMLResponse:
    content = await file.read()
    try:
        result = await rag_api.transcribe(
            file.filename or "audio.wav",
            content,
            file.content_type or "audio/wav",
        )
        return render(
            request,
            "tools.html",
            active_page="tools",
            url="https://example.com",
            max_chars=20000,
            speech_text="Your card was blocked after three failed PIN attempts.",
            transcript=result,
        )
    except BackendError as exc:
        return render(
            request,
            "tools.html",
            active_page="tools",
            url="https://example.com",
            max_chars=20000,
            speech_text="Your card was blocked after three failed PIN attempts.",
            **error_context(exc),
        )


# Detailed platform status
@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request) -> HTMLResponse:
    health_result, config_result, azure_result = await asyncio.gather(
        rag_api.health(),
        rag_api.config(),
        rag_api.azure(),
        return_exceptions=True,
    )
    context: dict[str, Any] = {
        "active_page": "status",
        "health": None if isinstance(health_result, Exception) else health_result,
        "config": None if isinstance(config_result, Exception) else config_result,
        "azure": None if isinstance(azure_result, Exception) else azure_result,
        "backend_online": not isinstance(health_result, Exception),
    }
    errors = [
        result
        for result in (health_result, config_result, azure_result)
        if isinstance(result, BackendError)
    ]
    if errors:
        context["error"] = " | ".join(error.message for error in errors)
        context["error_status"] = errors[0].status_code
    return render(request, "status.html", **context)
