from __future__ import annotations

import pytest

from backend.tooling import default_catalog, default_orchestrator
from backend.tooling.executors import safe_calculate, scan_pii
from backend.tooling.selector import SelectionContext


def _names(plan) -> set[str]:
    return {call.name for call in plan.calls}


def test_catalog_has_unique_chat_and_onboarding_tools():
    names = default_catalog.names()
    assert len(names) == len(set(names))
    assert {"internal_knowledge_search", "onboarding_checklist", "speech_delivery"} <= set(names)


def test_onboarding_request_selects_multiple_complementary_tools():
    plan = default_orchestrator.plan(SelectionContext(
        question="Ce documente sunt necesare pentru onboardingul unei companii?",
    ))
    assert plan.multi_tool is True
    assert {
        "language_detector", "pii_safety_scan", "internal_knowledge_search",
        "session_memory_search", "onboarding_intent_classifier", "onboarding_checklist",
    } <= _names(plan)


def test_selector_combines_attachment_fact_check_and_delivery():
    plan = default_orchestrator.plan(SelectionContext(
        question="Verifică acest document de onboarding",
        has_attachment=True,
        fact_check=True,
        delivery="speech_document",
    ))
    assert {
        "attachment_analysis", "web_fact_check", "speech_delivery", "document_export",
    } <= _names(plan)


def test_persona_allowlist_filters_tools():
    plan = default_orchestrator.plan(SelectionContext(
        question="Acte onboarding companie",
        allowed_tools=["language_detector", "onboarding_intent_classifier"],
    ))
    assert _names(plan) == {"language_detector", "onboarding_intent_classifier"}


def test_generic_document_request_does_not_trigger_onboarding_tools():
    plan = default_orchestrator.plan(SelectionContext(
        question="Rezuma acest document tehnic",
        has_attachment=True,
    ))
    assert "attachment_analysis" in _names(plan)
    assert "onboarding_intent_classifier" not in _names(plan)


def test_generic_onboarding_question_keeps_customer_type_unspecified():
    plan = default_orchestrator.plan(SelectionContext(
        question="Care sunt documentele necesare procesului de onboarding?",
    ))
    results = default_orchestrator.execute(plan, "Care sunt documentele necesare procesului de onboarding?")
    classifier = next(result for result in results if result.name == "onboarding_intent_classifier")
    assert classifier.output["customer_type"] == "unspecified"


def test_pii_scan_never_returns_identifier_values():
    source = "Contact: test@example.com, CNP 1960523123456"
    result = scan_pii(source)
    assert result["detected"] is True
    assert result["values_included"] is False
    assert "test@example.com" not in str(result)
    assert "1960523123456" not in str(result)


def test_safe_calculator_accepts_arithmetic_and_rejects_code():
    assert safe_calculate("(12 + 8) / 4") == 5
    with pytest.raises((ValueError, SyntaxError)):
        safe_calculate("__import__('os').system('dir')")
