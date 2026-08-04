"""Small framework-independent models used by the tool layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ToolPhase = Literal["pre", "retrieval", "post", "delivery"]
ToolExecution = Literal["local", "pipeline"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    category: str
    phase: ToolPhase
    execution: ToolExecution
    automatic: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolCall:
    name: str
    phase: ToolPhase
    reason: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolPlan:
    calls: list[ToolCall] = field(default_factory=list)
    selector: str = "rules-v1"

    @property
    def multi_tool(self) -> bool:
        return len(self.calls) > 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "selector": self.selector,
            "multi_tool": self.multi_tool,
            "calls": [call.as_dict() for call in self.calls],
        }


@dataclass
class ToolResult:
    name: str
    status: Literal["completed", "delegated", "skipped", "error"]
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
