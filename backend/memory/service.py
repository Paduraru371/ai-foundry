"""Token-aware current context, semantic compaction, and shared memory."""
from __future__ import annotations

import math
import re
import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..core.config import settings
from ..core.embeddings import get_embedder
from ..core.llm import ChatResult, get_llm
from ..core.token_usage import count_text, estimate_messages
from .store import _preview, session_store

TERM = re.compile(r"[^\W_]+", re.UNICODE)
STOP = {
    "a", "and", "are", "as", "at", "de", "din", "este", "for", "in",
    "is", "it", "la", "of", "o", "on", "or", "sau", "the", "to", "un",
    "with", "care", "pentru",
}


@dataclass
class PreparedContext:
    session_id: str | None = None
    summary: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    shared: list[dict[str, str]] = field(default_factory=list)


@dataclass
class RecordedTurn:
    assistant_message_id: int
    compaction_result: ChatResult | None = None
    compaction: str = "not-needed"
    compaction_estimated_prompt_tokens: int = 0


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def _terms(text: str) -> set[str]:
    return {
        value.casefold()
        for value in TERM.findall(text)
        if len(value) > 1 and value.casefold() not in STOP
    }


class MemoryService:
    def __init__(self) -> None:
        self._summary_vectors: dict[tuple[str, str], list[float]] = {}

    def prepare(
        self,
        session_id: str | None,
        query: str,
        use_shared: bool,
    ) -> PreparedContext:
        if not session_id:
            return PreparedContext()
        if not session_store.exists(session_id):
            raise ValueError("Session not found.")

        detail = session_store.get(session_id) or {}
        candidates = session_store.recent_messages(
            session_id,
            settings.history_max_messages,
        )
        history: list[dict[str, str]] = []
        used = 0
        for message in reversed(candidates):
            content = message["content"]
            attachment = message.get("metadata", {}).get("attachment")
            if attachment and attachment.get("filename"):
                content += (
                    "\n[Uploaded document in this turn: "
                    f"{attachment['filename']}]"
                )
            cost = count_text(content) + 5
            if history and used + cost > settings.history_max_tokens:
                break
            history.append({
                "role": message["role"],
                "content": content,
            })
            used += cost
        history.reverse()
        shared = self._shared(session_id, query) if use_shared else []
        return PreparedContext(
            session_id=session_id,
            summary=str(detail.get("summary") or ""),
            history=history,
            shared=shared,
        )

    def _shared(self, session_id: str, query: str) -> list[dict[str, str]]:
        candidates = session_store.memory_candidates(
            session_id,
            settings.shared_memory_candidate_limit,
        )
        if not candidates:
            return []
        semantic: list[float] | None = None
        try:
            embedder = get_embedder()
            descriptor = embedder.describe()
            model_key = f"{descriptor['provider']}:{descriptor['model']}"
            texts = [
                f"{item['title']}\n{item['summary']}"
                for item in candidates
            ]
            digests = [
                hashlib.sha256(text.encode("utf-8")).hexdigest()
                for text in texts
            ]
            missing = [
                (index, text)
                for index, (digest, text) in enumerate(zip(digests, texts))
                if (model_key, digest) not in self._summary_vectors
            ]
            embedded = embedder.embed([query, *[text for _, text in missing]])
            query_vector = embedded[0]
            for (index, _), vector in zip(missing, embedded[1:]):
                self._summary_vectors[(model_key, digests[index])] = vector
            semantic = [
                _cosine(
                    query_vector,
                    self._summary_vectors[(model_key, digest)],
                )
                for digest in digests
            ]
        except Exception:
            semantic = None

        query_terms = _terms(query)
        ranked: list[tuple[float, dict[str, str]]] = []
        for index, candidate in enumerate(candidates):
            candidate_terms = _terms(candidate["title"] + " " + candidate["summary"])
            lexical = (
                len(query_terms & candidate_terms) / len(query_terms)
                if query_terms else 0.0
            )
            semantic_score = semantic[index] if semantic is not None else lexical
            recency = 1.0 - index / max(1, len(candidates))
            score = 0.78 * semantic_score + 0.17 * lexical + 0.05 * recency
            if (
                score >= settings.shared_memory_min_score
                or lexical >= settings.shared_memory_lexical_override
            ):
                ranked.append((score, candidate))
        ranked.sort(key=lambda item: item[0], reverse=True)

        selected: list[dict[str, str]] = []
        used_chars = 0
        for score, candidate in ranked[:settings.shared_memory_session_limit]:
            remaining = settings.shared_memory_max_chars - used_chars
            if remaining < 160:
                break
            summary = _preview(candidate["summary"], remaining)
            selected.append({**candidate, "summary": summary, "score": f"{score:.4f}"})
            used_chars += len(summary)
        return selected

    def record(
        self,
        session_id: str,
        question: str,
        answer: str,
        user_metadata: dict[str, Any] | None = None,
    ) -> RecordedTurn:
        session_store.add_message(
            session_id,
            "user",
            question,
            user_metadata,
        )
        assistant_id = session_store.add_message(session_id, "assistant", answer)
        session_store.set_title_from_message(session_id, question)
        payload = session_store.compaction_payload(
            session_id,
            settings.history_max_messages,
            settings.session_compaction_batch_messages,
        )
        if payload is None:
            return RecordedTurn(assistant_id)

        turns = "\n".join(
            f"{item['role'].upper()}: {_preview(item['content'], 1_200)}"
            for item in payload["messages"]
        )
        system = (
            "Compress old conversation context into durable semantic memory. "
            "Preserve user goals, constraints, decisions, preferences, named entities, "
            "corrections, unresolved work and important facts. Remove greetings and "
            "repetition. Never invent. Use complete sentences and stay under "
            f"{settings.session_summary_max_chars} characters."
        )
        user = (
            f"EXISTING SUMMARY:\n{payload['previous_summary'] or '(none)'}\n\n"
            f"NEWLY ARCHIVED TURNS:\n{turns}\n\nReturn only the merged summary."
        )
        try:
            result = get_llm().chat(
                system=system,
                user=user,
                temperature=0,
                max_tokens=700,
            )
            summary = _preview(result.text, settings.session_summary_max_chars)
            if not summary:
                raise ValueError("Empty semantic summary")
            session_store.save_summary(session_id, summary, payload["through_id"])
            return RecordedTurn(
                assistant_id,
                result,
                "semantic",
                estimate_messages([system, user]),
            )
        except Exception:
            fallback = "\n".join(
                part for part in (
                    payload["previous_summary"],
                    *[
                        f"- {item['role'].title()}: {_preview(item['content'], 420)}"
                        for item in payload["messages"]
                    ],
                )
                if part
            )
            session_store.save_summary(session_id, fallback, payload["through_id"])
            return RecordedTurn(assistant_id, None, "deterministic-fallback")

    @staticmethod
    def set_turn_metadata(message_id: int, metadata: dict[str, Any]) -> None:
        session_store.set_message_metadata(message_id, metadata)


memory_service = MemoryService()
