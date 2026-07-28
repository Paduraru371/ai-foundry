"""Local persona and Foundry agent management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..agents import foundry_agent
from ..agents.persona import (
    PERSONA_DIR,
    PersonaNotFound,
    list_personas,
    load_persona,
)
from ..config import settings
from ..schemas import (
    AgentListResponse,
    FoundryAvailability,
    HostedAgent,
    PersonaSummary,
)

router = APIRouter()


@router.get("/agents", response_model=AgentListResponse, tags=["5 · agents"])
def agents_list() -> AgentListResponse:
    """List every persona and the execution environments available to it."""
    personas = list_personas()
    availability = foundry_agent.availability()

    hosted_by_name: dict[str, dict] = {}
    if availability["available"]:
        try:
            hosted_by_name = {
                agent["name"]: agent for agent in foundry_agent.list_hosted()
            }
        except Exception as error:
            availability = {
                "available": False,
                "reason": f"{type(error).__name__}: {error}",
            }

    summaries: list[PersonaSummary] = []
    for persona in personas:
        hosted = hosted_by_name.get(persona.name)
        runs_on = (
            "unknown"
            if not availability["available"]
            else ("both" if hosted else "local")
        )
        summaries.append(PersonaSummary(
            **persona.summary(),
            runs_on=runs_on,
            hosted=HostedAgent(**hosted) if hosted else None,
        ))

    local_names = {persona.name for persona in personas}
    hosted_only = [
        PersonaSummary(
            name=agent["name"],
            display_name=agent["name"],
            description=agent.get("description")
            or "Created in Foundry — no local persona file.",
            runs_on="foundry",
            hosted=HostedAgent(**agent),
        )
        for name, agent in hosted_by_name.items()
        if name not in local_names
    ]
    return AgentListResponse(
        active_mode=settings.agent_mode,
        default_persona=settings.agent_persona,
        personas_dir=str(PERSONA_DIR),
        count=len(summaries),
        personas=summaries,
        foundry=FoundryAvailability(**availability),
        hosted_only=hosted_only,
    )


@router.get("/agents/hosted", tags=["5 · agents"])
def agents_hosted() -> dict:
    availability = foundry_agent.availability()
    if not availability["available"]:
        raise HTTPException(status_code=503, detail=availability["reason"])
    try:
        items = foundry_agent.list_hosted()
        return {"count": len(items), "agents": items}
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not list hosted agents: {error}",
        )


@router.delete("/agents/hosted/{agent_id}", tags=["5 · agents"])
def agent_hosted_delete(agent_id: str) -> dict:
    try:
        foundry_agent.delete_hosted(agent_id)
    except foundry_agent.FoundryUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not delete agent: {error}",
        )
    return {"deleted": True, "agent_id": agent_id}


@router.get("/agents/{name}", tags=["5 · agents"])
def agent_detail(name: str) -> dict:
    try:
        persona = load_persona(name)
    except PersonaNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {
        **persona.summary(),
        "system_prompt_plain": persona.system_prompt(grounded=False),
        "system_prompt_grounded": persona.system_prompt(grounded=True),
        "file": str(PERSONA_DIR / f"{name}.json"),
    }


@router.post("/agents/{name}/deploy", tags=["5 · agents"])
def agent_deploy(name: str) -> dict:
    try:
        persona = load_persona(name)
    except PersonaNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    try:
        result = foundry_agent.deploy(persona)
    except foundry_agent.FoundryUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Deployment to Foundry failed: {error}",
        )
    result["next_step"] = (
        f"Put FOUNDRY_AGENT_ID={result['agent_id']} in .env, then call /ask with "
        f'"agent_mode": "foundry".'
    )
    return result
