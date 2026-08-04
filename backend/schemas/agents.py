"""Schemas for generation, personas, and hosted agents."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .rag import SearchHit
from .sessions import MemoryContextInfo


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=20_000)


class AskRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "question": "What fee does Libra Bank charge for early mortgage repayment?",
        "use_rag": True,
        "top_k": 3,
        "agent": "lyrical",
    }]}}

    question: str = Field(..., min_length=1)
    use_rag: bool = Field(True, description="false = plain LLM; true = retrieve then augment")
    top_k: Optional[int] = Field(None, ge=1, le=50)
    min_score: Optional[float] = Field(
        None,
        ge=-1,
        le=1,
        description="Minimum cosine similarity for retrieved context",
    )
    temperature: Optional[float] = Field(None, ge=0, le=2)
    agent: Optional[str] = Field(
        None,
        description="Persona name from backend/agents/personas/ — try 'default', 'lyrical', "
                    "'compliance', 'teller'. Falls back to AGENT_PERSONA in .env.",
    )
    agent_mode: Optional[Literal["local", "foundry"]] = Field(
        None,
        description="local = the loop runs here; foundry = the hosted Agent Service",
    )
    fact_check: bool = Field(
        False,
        description="Verify the generated answer against open-web evidence",
    )
    response_format: Literal[
        "plain", "markdown", "bullet_list", "table", "json",
        "executive_summary", "technical_report",
    ] = Field("plain", description="Shape required for the generated answer")
    delivery: Literal[
        "conversation", "speech", "document", "speech_document",
    ] = Field(
        "conversation",
        description="How the frontend will deliver the generated content.",
    )
    document_type: Literal[
        "pdf", "docx", "pptx", "txt", "md", "json",
    ] = "pdf"
    document_text: Optional[str] = Field(
        None,
        max_length=120_000,
        description="Text extracted from an uploaded document and supplied for analysis",
    )
    document_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Original uploaded filename, for prompt provenance",
    )
    document_path: Optional[str] = Field(
        None,
        max_length=500,
        description="Server-relative path of a persisted chat upload",
    )
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=20,
        description="Recent user/assistant turns supplied as conversational context",
    )
    session_id: Optional[str] = Field(
        None,
        min_length=8,
        max_length=64,
        description="Persistent backend session. When set, stored history is authoritative.",
    )
    generation_id: Optional[str] = Field(
        None,
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Client-generated id used to cancel an in-flight answer.",
    )
    shared_memory: bool = Field(
        True,
        description="Inject semantically relevant summaries from other sessions",
    )
    tool_mode: Literal["auto", "none"] = Field(
        "auto",
        description="auto = select relevant tools; none = bypass tool selection",
    )
    requested_tools: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Optional tool names to add to the automatic plan",
    )


class AgentInfo(BaseModel):
    name: str
    display_name: str
    description: str
    mode: str = Field(description="Where this run executed: local or foundry")
    temperature: Optional[float] = None
    style_rules: list[str] = Field(default_factory=list)


class HostedAgent(BaseModel):
    agent_id: str
    name: str
    model: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[int] = None
    instructions_preview: Optional[str] = None


class PersonaSummary(BaseModel):
    name: str
    display_name: str
    description: str
    policy_file: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    style_rules: list[str] = Field(default_factory=list)
    require_citations: bool = True
    refuse_when_unsupported: bool = True
    unsupported_response: Optional[str] = None
    reasoning_effort: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    runs_on: Literal["local", "both", "foundry", "unknown"] = Field(
        "local",
        description="local = JSON file only · both = also hosted in Foundry · "
                    "foundry = hosted only, no local file · unknown = cannot ask Foundry",
    )
    hosted: Optional[HostedAgent] = None


class FoundryAvailability(BaseModel):
    available: bool
    reason: Optional[str] = Field(
        None,
        description="Why the Agent Service could not be queried, when it could not",
    )


class AgentListResponse(BaseModel):
    active_mode: str
    default_persona: str
    personas_dir: str
    count: int
    personas: list[PersonaSummary]
    foundry: FoundryAvailability
    hosted_only: list[PersonaSummary] = Field(
        default_factory=list,
        description="Agents that exist in Foundry with no local persona file — "
                    "created in the portal, or from a file since deleted",
    )


class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    estimated_prompt_tokens: int = 0
    estimated_max_completion_tokens: int = 0
    input_cost_usd: Optional[float] = None
    output_cost_usd: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    pricing: dict = Field(default_factory=dict)
    phases: dict = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    augmented: bool
    provider: str
    model: str
    agent: Optional[AgentInfo] = Field(
        None,
        description="Which persona shaped this answer",
    )
    system_prompt: str = Field(description="The system message actually sent")
    prompt_sent: str = Field(
        description="The exact user prompt sent to the model — compare with/without RAG"
    )
    retrieved: list[SearchHit] = Field(default_factory=list)
    usage: Optional[Usage] = None
    response_format: str = "plain"
    document_name: Optional[str] = None
    fact_check: Optional[dict] = None
    guardrail: Optional[dict] = None
    session_id: Optional[str] = None
    memory: Optional[MemoryContextInfo] = None
    tool_plan: Optional[dict] = None
    tool_results: list[dict] = Field(default_factory=list)
