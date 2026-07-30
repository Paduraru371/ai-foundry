"""Thread-safe cooperative cancellation for in-flight generations."""
from __future__ import annotations

from contextlib import contextmanager
from threading import Event, Lock
from time import monotonic
from typing import Iterator


class GenerationCancelled(Exception):
    """Raised at a safe checkpoint after a client requests cancellation."""


class GenerationControl:
    """Coordinate cancel requests with synchronous generation workers."""

    def __init__(self, *, retention_seconds: float = 600, max_entries: int = 1024):
        self._retention_seconds = retention_seconds
        self._max_entries = max_entries
        self._entries: dict[str, tuple[Event, float]] = {}
        self._lock = Lock()

    def _prune(self, now: float) -> None:
        expired = [
            generation_id
            for generation_id, (_, touched) in self._entries.items()
            if now - touched > self._retention_seconds
        ]
        for generation_id in expired:
            self._entries.pop(generation_id, None)
        if len(self._entries) > self._max_entries:
            oldest = sorted(
                self._entries,
                key=lambda key: self._entries[key][1],
            )
            for generation_id in oldest[: len(self._entries) - self._max_entries]:
                self._entries.pop(generation_id, None)

    @contextmanager
    def track(self, generation_id: str | None) -> Iterator[Event | None]:
        if not generation_id:
            yield None
            return
        now = monotonic()
        with self._lock:
            self._prune(now)
            event, _ = self._entries.get(generation_id, (Event(), now))
            self._entries[generation_id] = (event, now)
        try:
            yield event
        finally:
            with self._lock:
                self._entries.pop(generation_id, None)

    def cancel(self, generation_id: str) -> bool:
        """Mark a generation cancelled, including a request still in transit."""
        now = monotonic()
        with self._lock:
            self._prune(now)
            event, _ = self._entries.get(generation_id, (Event(), now))
            event.set()
            self._entries[generation_id] = (event, now)
        return True

    @staticmethod
    def checkpoint(event: Event | None) -> None:
        if event is not None and event.is_set():
            raise GenerationCancelled("Generation cancelled by the user.")


generation_control = GenerationControl()
