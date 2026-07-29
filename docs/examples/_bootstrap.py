"""Shared preamble: make `app` importable and print a small banner.

Every example imports this first so the scripts can be run from anywhere:
    .venv/Scripts/python.exe docs/examples/02_hello_foundry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings  # noqa: E402


def banner(title: str) -> None:
    line = "─" * max(len(title), 52)
    print(f"\n{line}\n{title}\n{line}")


def show_context() -> None:
    print(f"provider   : {settings.llm_provider}  ·  embeddings: {settings.embedding_provider}")
    if settings.llm_provider == "azure":
        print(f"endpoint   : {settings.azure_ai_endpoint}")
        print(f"deployment : {settings.azure_ai_chat_deployment}  ·  auth: {settings.azure_ai_auth}")
