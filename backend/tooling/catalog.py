"""Central catalog for tools available to chatbot personas."""
from __future__ import annotations

from .models import ToolSpec


_DEFAULT_TOOLS = (
    ToolSpec("language_detector", "Language detector", "Detects the language of the current message.", "conversation", "pre", "local"),
    ToolSpec("pii_safety_scan", "PII safety scan", "Classifies sensitive identifiers without returning their values.", "safety", "pre", "local"),
    ToolSpec("internal_knowledge_search", "Internal knowledge search", "Retrieves grounded passages from the bank knowledge base.", "knowledge", "retrieval", "pipeline"),
    ToolSpec("session_memory_search", "Session memory search", "Finds relevant context from this and shared sessions.", "conversation", "retrieval", "pipeline"),
    ToolSpec("attachment_analysis", "Attachment analysis", "Extracts and analyses supported onboarding documents.", "documents", "pre", "pipeline"),
    ToolSpec("onboarding_intent_classifier", "Onboarding intent classifier", "Identifies onboarding subject and customer type.", "onboarding", "pre", "local"),
    ToolSpec("onboarding_checklist", "Onboarding checklist", "Builds a non-authoritative checklist of evidence categories to verify.", "onboarding", "pre", "local"),
    ToolSpec("escalation_router", "Escalation router", "Routes regulated, blocked or support cases to the appropriate team.", "onboarding", "pre", "local"),
    ToolSpec("safe_calculator", "Safe calculator", "Evaluates simple arithmetic without executing arbitrary code.", "utility", "pre", "local"),
    ToolSpec("web_fact_check", "Web fact-check", "Checks answer claims against bounded open-web evidence.", "verification", "post", "pipeline", automatic=False),
    ToolSpec("web_fetch", "Web page reader", "Reads an explicitly supplied public URL with bounded extraction.", "knowledge", "retrieval", "pipeline", automatic=False),
    ToolSpec("speech_delivery", "Speech delivery", "Converts the final answer to speech on request.", "delivery", "delivery", "pipeline", automatic=False),
    ToolSpec("document_export", "Document export", "Exports the final answer to the selected document type.", "delivery", "delivery", "pipeline", automatic=False),
)


class ToolCatalog:
    def __init__(self, tools: tuple[ToolSpec, ...] = _DEFAULT_TOOLS) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique")

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def as_dicts(self) -> list[dict]:
        return [tool.as_dict() for tool in self._tools.values()]


default_catalog = ToolCatalog()
