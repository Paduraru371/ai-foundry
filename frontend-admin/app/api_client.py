"""HTTP client for the RAG API"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .config import BACKEND_URL, REQUEST_TIMEOUT


class BackendError(Exception):

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RagApiClient:
    """Keeps all backend communication outside the route handlers"""

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> dict[str, Any] | bytes:
        try:
            # the timeout prevents a provider outage from hanging the frontend forever
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.request(
                    method,
                    f"{BACKEND_URL}{path}",
                    json=payload if files is None and data is None else None,
                    files=files,
                    data=data,
                )
                
        except httpx.RequestError as exc:
            raise BackendError(
                f"The backend cannot be reached at {BACKEND_URL}. "
                "Check that the service is running."
            ) from exc

        if not response.is_success:
            # FastAPI normally returns {"detail": ...}; plain text remains a fallback.
            try:
                body = response.json()
                detail = body.get("detail", body)
                
            except ValueError:
                detail = response.text or response.reason_phrase
                
            raise BackendError(str(detail), response.status_code)

        return response.content if raw else response.json()

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def config(self) -> dict[str, Any]:
        return await self._request("GET", "/config")

    async def collection(self) -> dict[str, Any]:
        return await self._request("GET", "/collection")

    async def chunk(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/chunk", payload)

    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/ingest", payload)

    async def search(self, query: str, top_k: int) -> dict[str, Any]:
        return await self._request("POST", "/search", {"query": query, "top_k": top_k})

    async def tool_catalog(self) -> dict[str, Any]:
        return await self._request("GET", "/tools/catalog")

    async def source(self, source: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/sources/{quote(source, safe='')}",
        )

    async def source_download(self, source: str) -> bytes:
        result = await self._request(
            "GET",
            f"/sources/{quote(source, safe='')}/download",
            raw=True,
        )
        return bytes(result)

    async def ask(
        self,
        question: str,
        use_rag: bool,
        top_k: int | None,
        agent: str | None = None,
        agent_mode: str | None = None,
        fact_check: bool = False,
        response_format: str = "plain",
        document_text: str | None = None,
        document_name: str | None = None,
        history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
        shared_memory: bool = True,
        document_path: str | None = None,
        generation_id: str | None = None,
        delivery: str = "conversation",
        document_type: str = "pdf",
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/ask",
            {
                "question": question,
                "use_rag": use_rag,
                "top_k": top_k,
                "agent": agent,
                "agent_mode": agent_mode,
                "fact_check": fact_check,
                "response_format": response_format,
                "document_text": document_text,
                "document_name": document_name,
                "document_path": document_path,
                "history": history or [],
                "session_id": session_id,
                "shared_memory": shared_memory,
                "generation_id": generation_id,
                "delivery": delivery,
                "document_type": document_type,
            },
        )

    async def cancel_generation(self, generation_id: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/generations/{quote(generation_id, safe='')}/cancel",
        )

    async def sessions(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/sessions")

    async def create_session(self, title: str = "New conversation") -> dict[str, Any]:
        return await self._request("POST", "/sessions", {"title": title})

    async def session(self, session_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/sessions/{quote(session_id, safe='')}",
        )

    async def delete_session(self, session_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/sessions/{quote(session_id, safe='')}",
        )

    async def extract_document(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/documents/extract",
            files={"file": (filename, content, content_type)},
            data={"session_id": session_id} if session_id else None,
        )

    async def reset_collection(self) -> dict[str, Any]:
        return await self._request("DELETE", "/collection")

    async def agents(self) -> dict[str, Any]:
        return await self._request("GET", "/agents")

    async def agent(self, name: str) -> dict[str, Any]:
        return await self._request("GET", f"/agents/{quote(name, safe='')}")

    async def deploy_agent(self, name: str) -> dict[str, Any]:
        return await self._request("POST", f"/agents/{quote(name, safe='')}/deploy")

    async def delete_hosted_agent(self, agent_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", f"/agents/hosted/{quote(agent_id, safe='')}"
        )

    async def azure(self) -> dict[str, Any]:
        return await self._request("GET", "/azure")

    async def web_fetch(self, url: str, max_chars: int) -> dict[str, Any]:
        return await self._request(
            "POST", "/tools/web-fetch", {"url": url, "max_chars": max_chars}
        )

    async def speak(self, text: str, voice: str | None = None) -> bytes:
        result = await self._request(
            "POST", "/tools/speak", {"text": text, "voice": voice}, raw=True
        )
        return bytes(result)

    async def transcribe(
        self, filename: str, content: bytes, content_type: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/tools/transcribe",
            files={"file": (filename, content, content_type)},
        )


# routes use  stateless client
rag_api = RagApiClient()
