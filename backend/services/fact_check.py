"""Optional open-web verification for generated answers."""
from __future__ import annotations

import json
import re

from ..core.config import settings
from ..core.llm import get_llm
from ..core.token_usage import estimate_messages, usage_details
from . import web


def verify(question: str, answer: str) -> dict:
    """Search, read a bounded number of pages, then ask the model for a verdict."""
    try:
        hits, provider = web.search(question, max_results=settings.web_search_results)
    except Exception as error:
        return {
            "verdict": "unverified",
            "confidence": "low",
            "evidence_from": "open web",
            "reasoning": "",
            "sources": [],
            "error": f"Web search failed: {error}",
        }

    sources: list[dict] = []
    evidence: list[str] = []
    for hit in hits[: settings.fact_check_pages]:
        item = {
            "rank": hit.rank,
            "title": hit.title,
            "url": hit.url,
            "used": False,
            "chars_read": 0,
        }
        try:
            page = web.scrape(hit.url, max_chars=6000)
            if page.text:
                item["used"] = True
                item["chars_read"] = len(page.text)
                evidence.append(
                    f"[{hit.rank}] {hit.title}\nURL: {hit.url}\n{page.text}"
                )
        except Exception:
            pass
        sources.append(item)

    if not evidence:
        return {
            "verdict": "unverified",
            "confidence": "low",
            "evidence_from": provider,
            "reasoning": "",
            "sources": sources,
            "error": "Search returned results, but no source page could be read.",
        }

    system = (
        "You are a strict fact checker. Compare the ANSWER with the supplied web "
        "EVIDENCE. Return JSON only with keys verdict, confidence, reasoning. "
        "verdict must be supported, contradicted, mixed, or unverified; confidence "
        "must be high, medium, or low. Do not treat search snippets as proof."
    )
    user = (
        f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\n"
        "EVIDENCE:\n" + "\n\n".join(evidence)
    )
    llm = get_llm()
    result = llm.chat(
        system=system,
        user=user,
        temperature=0,
        max_tokens=700,
        extras={},
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", result.text.strip())
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = {
            "verdict": "unverified",
            "confidence": "low",
            "reasoning": result.text,
        }
    parsed.update({
        "evidence_from": provider,
        "sources": sources,
        "error": None,
        "usage": usage_details(
            provider=result.provider,
            model=result.model,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cached_input_tokens=result.cached_input_tokens,
            reasoning_tokens=result.reasoning_tokens,
            estimated_prompt_tokens=estimate_messages([system, user]),
            estimated_max_completion_tokens=700,
        ),
    })
    return parsed
