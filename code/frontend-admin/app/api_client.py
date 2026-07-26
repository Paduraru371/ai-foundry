"""HTTP client for the RAG API"""
from __future__ import annotations

from typing import Any

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
    ) -> dict[str, Any]:
        try:
            # the timeout prevents a provider outage from hanging the frontend forever
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.request(
                    method,
                    f"{BACKEND_URL}{path}",
                    json=payload,
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

        return response.json()

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

    async def ask(self, question: str, use_rag: bool, top_k: int) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/ask",
            {"question": question, "use_rag": use_rag, "top_k": top_k},
        )

    async def reset_collection(self) -> dict[str, Any]:
        return await self._request("DELETE", "/collection")


# routes use  stateless client
rag_api = RagApiClient()
