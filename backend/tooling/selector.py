"""Explainable, deterministic multi-tool selection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .catalog import ToolCatalog, default_catalog
from .models import ToolCall, ToolPlan

_ONBOARDING = re.compile(
    r"\b(onboard(?:ing(?:ul(?:ui)?)?)?|deschid(?:ere|e) (?:de )?cont|client nou|new customer|cui|kyc|aml|pep|beneficiar(?: efectiv)?|beneficial owner)\b",
    re.IGNORECASE,
)
_ONBOARDING_DOCUMENTS = re.compile(r"\b(documente?|acte?|evidence|papers?)\b", re.IGNORECASE)
_CUSTOMER_CONTEXT = re.compile(
    r"\b(companie|firmă|societate|persoan[ăa] fizic[ăa]|persoan[ăa] juridic[ăa]|identitat|administrator|cont bancar|company|business|individual|identity|bank account)\b",
    re.IGNORECASE,
)
_ESCALATION = re.compile(
    r"\b(blocat|respins|refuzat|fraud[ăa]?|suspect|reclama|plângere|urgent|compliance|support|eroare|nu funcționează|failed|rejected|blocked)\b",
    re.IGNORECASE,
)
_CALCULATION = re.compile(r"(?<!\w)(?:\d+(?:[.,]\d+)?\s*[+*/()-]\s*)+\d+(?:[.,]\d+)?(?!\w)")
_URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_URL_ACTION = re.compile(r"\b(citește|verifică|deschide|read|check|open|fetch)\b", re.IGNORECASE)


@dataclass
class SelectionContext:
    question: str
    use_rag: bool = True
    shared_memory: bool = True
    has_attachment: bool = False
    fact_check: bool = False
    delivery: str = "conversation"
    requested_tools: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)


class ToolSelector:
    def __init__(self, catalog: ToolCatalog = default_catalog) -> None:
        self.catalog = catalog

    def select(self, context: SelectionContext) -> ToolPlan:
        selected: dict[str, ToolCall] = {}

        def add(name: str, reason: str, arguments: dict | None = None) -> None:
            spec = self.catalog.get(name)
            if not spec:
                return
            if context.allowed_tools and name not in context.allowed_tools:
                return
            selected.setdefault(name, ToolCall(name, spec.phase, reason, arguments or {}))

        add("language_detector", "Keep the answer in the language of the current message")
        add("pii_safety_scan", "Apply safe handling when the message contains sensitive identifiers")
        if context.use_rag:
            add("internal_knowledge_search", "Ground the answer in internal bank documents")
        if context.shared_memory:
            add("session_memory_search", "Use relevant conversational context")
        if context.has_attachment:
            add("attachment_analysis", "An attachment was supplied for analysis")
        onboarding_request = bool(
            _ONBOARDING.search(context.question)
            or (
                _ONBOARDING_DOCUMENTS.search(context.question)
                and _CUSTOMER_CONTEXT.search(context.question)
            )
        )
        if onboarding_request:
            add("onboarding_intent_classifier", "The request concerns onboarding or identity evidence")
            add("onboarding_checklist", "Verify the relevant onboarding evidence categories")
        if _ESCALATION.search(context.question):
            add("escalation_router", "The request may require operational or regulated escalation")
        expression = _CALCULATION.search(context.question)
        if expression:
            add("safe_calculator", "The message contains an arithmetic expression", {"expression": expression.group(0)})
        if context.fact_check:
            add("web_fact_check", "Open-web verification was explicitly enabled")
        url = _URL.search(context.question)
        if url and _URL_ACTION.search(context.question):
            add("web_fetch", "The user explicitly asked to read a public URL", {"url": url.group(0).rstrip(".,)")})
        if context.delivery in {"speech", "speech_document"}:
            add("speech_delivery", "Speech delivery was requested")
        if context.delivery in {"document", "speech_document"}:
            add("document_export", "Document export was requested")
        for name in context.requested_tools:
            add(name, "The caller explicitly requested this tool")
        return ToolPlan(calls=list(selected.values()))
