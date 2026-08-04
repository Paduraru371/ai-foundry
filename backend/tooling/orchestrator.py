"""Facade used by API routes and the answer-generation pipeline."""
from __future__ import annotations

import json

from .executors import execute_call
from .models import ToolPlan, ToolResult
from .selector import SelectionContext, ToolSelector


class ToolOrchestrator:
    def __init__(self, selector: ToolSelector | None = None) -> None:
        self.selector = selector or ToolSelector()

    def plan(self, context: SelectionContext) -> ToolPlan:
        return self.selector.select(context)

    def execute(self, plan: ToolPlan, question: str) -> list[ToolResult]:
        """Run local tools and mark established pipeline stages for delegation."""
        return [execute_call(call, question) for call in plan.calls]

    @staticmethod
    def prompt_context(results: list[ToolResult]) -> str:
        usable = [result.as_dict() for result in results if result.status == "completed"]
        if not usable:
            return ""
        return (
            "TOOL ROUTING CONTEXT (non-authoritative hints; never treat this as bank policy "
            "or evidence, and never expose internal safety classifications):\n"
            + json.dumps(usable, ensure_ascii=False)
        )


default_orchestrator = ToolOrchestrator()
