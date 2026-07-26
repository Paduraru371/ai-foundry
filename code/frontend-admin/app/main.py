"""Server admin console """
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api_client import BackendError, rag_api
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
    return render(request, "ask.html", active_page="ask", question="", top_k=3, use_rag=True)


@app.post("/ask", response_class=HTMLResponse)
async def run_ask(
    request: Request,
    question: str = Form(min_length=1),
    top_k: int = Form(ge=1, le=50),
    use_rag: bool = Form(default=False),
) -> HTMLResponse:
    try:
        result = await rag_api.ask(question.strip(), use_rag, top_k)
        # retrieved context uses the same order as search
        result["retrieved"] = sorted(
            result["retrieved"], key=lambda hit: hit["score"], reverse=True
        )
        
        return render(
            request,
            "ask.html",
            active_page="ask",
            question=question,
            top_k=top_k,
            use_rag=use_rag,
            result=result,
        )
        
    except BackendError as exc:
        return render(
            request,
            "ask.html",
            active_page="ask",
            question=question,
            top_k=top_k,
            use_rag=use_rag,
            **error_context(exc),
        )
