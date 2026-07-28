"""Agent execution endpoint, with optional retrieval augmentation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..agents import foundry_agent, local_agent
from ..agents.persona import PersonaNotFound, load_persona
from ..api_dependencies import embed, require_qdrant, store
from ..config import settings
from ..schemas import AgentInfo, AskRequest, AskResponse, SearchHit, Usage

router = APIRouter()


@router.post("/ask", response_model=AskResponse, tags=["4 · generation"])
def ask(req: AskRequest) -> AskResponse:
    """Run the selected agent, optionally augmented with retrieved context."""
    retrieved: list[SearchHit] = []
    persona_name = req.agent or settings.agent_persona
    mode_requested = (req.agent_mode or settings.agent_mode).lower()
    persona = None
    hosted_only = None
    try:
        persona = load_persona(persona_name)
    except PersonaNotFound as error:
        if mode_requested != "foundry":
            raise HTTPException(status_code=404, detail=str(error))
        try:
            hosted_only = foundry_agent.find_hosted(persona_name)
        except foundry_agent.FoundryUnavailable as foundry_error:
            raise HTTPException(status_code=503, detail=str(foundry_error))
        if not hosted_only:
            raise HTTPException(status_code=404, detail=str(error))

    if req.use_rag:
        require_qdrant()
        if not store.info()["exists"]:
            raise HTTPException(
                status_code=404,
                detail="use_rag=true but the collection is empty — POST /ingest first, "
                       "or set use_rag=false for a plain LLM answer.",
            )
        top_k = req.top_k or settings.top_k
        query_vector = embed([req.question])[0]
        retrieved = [
            SearchHit(**hit) for hit in store.search(query_vector, top_k)
        ]

    chunks = [hit.model_dump() for hit in retrieved]
    try:
        if hosted_only is not None:
            reply = foundry_agent.run_hosted(hosted_only, req.question, chunks)
        elif mode_requested == "foundry":
            reply = foundry_agent.run(persona, req.question, chunks)
        else:
            reply = local_agent.run(
                persona,
                req.question,
                chunks,
                temperature=req.temperature,
            )
    except foundry_agent.FoundryUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Agent run failed (mode={mode_requested}, "
                   f"provider={settings.llm_provider}): {error}",
        )

    info = (
        AgentInfo(
            name=persona.name,
            display_name=persona.display_name,
            description=persona.description,
            mode=reply.mode,
            temperature=persona.temperature,
            style_rules=persona.style_rules,
        )
        if persona is not None
        else AgentInfo(
            name=hosted_only["name"],
            display_name=hosted_only["name"],
            description=hosted_only.get("description")
            or "Hosted in Foundry — no local persona file.",
            mode=reply.mode,
        )
    )
    return AskResponse(
        answer=reply.text,
        augmented=req.use_rag,
        provider=reply.provider,
        model=reply.model,
        agent=info,
        system_prompt=reply.system_prompt,
        prompt_sent=reply.prompt_sent,
        retrieved=retrieved,
        usage=Usage(
            prompt_tokens=reply.prompt_tokens,
            completion_tokens=reply.completion_tokens,
        ),
    )
