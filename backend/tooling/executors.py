"""Safe local tool implementations and pipeline hand-off markers."""
from __future__ import annotations

import ast
import operator
import re
from typing import Callable

from .models import ToolCall, ToolResult

_PII_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?40|0)[\s.-]?\d{2,3}(?:[\s.-]?\d{3}){2}(?!\d)"),
    "romanian_personal_id": re.compile(r"(?<!\d)[1-8]\d{12}(?!\d)"),
    "iban": re.compile(r"\bRO\d{2}[A-Z]{4}[A-Z0-9]{16}\b", re.IGNORECASE),
}


def detect_language(text: str) -> dict:
    lowered = f" {text.lower()} "
    markers = {
        "ro": (" și ", " este ", " vreau ", " care ", " pentru ", " documente ", " să ", " î", " ț"),
        "en": (" the ", " and ", " what ", " how ", " for ", " documents ", " is "),
        "fr": (" le ", " la ", " et ", " pour ", " quels "),
        "de": (" der ", " die ", " und ", " für ", " welche "),
        "es": (" el ", " la ", " y ", " para ", " qué "),
    }
    scores = {lang: sum(lowered.count(item) for item in words) for lang, words in markers.items()}
    language = max(scores, key=scores.get) if max(scores.values(), default=0) else "unknown"
    return {"language": language, "confidence": "medium" if language != "unknown" else "low"}


def scan_pii(text: str) -> dict:
    counts = {name: len(pattern.findall(text)) for name, pattern in _PII_PATTERNS.items()}
    counts = {name: count for name, count in counts.items() if count}
    return {"detected": bool(counts), "categories": counts, "values_included": False}


def classify_onboarding(text: str) -> dict:
    lower = text.lower()
    if re.search(r"\b(companie|firmă|firma|societate|cui|company|business)\b", lower):
        customer_type = "business"
    elif re.search(
        r"\b(persoană fizică|persoana fizica|client individual|individual|personal)\b",
        lower,
    ):
        customer_type = "individual"
    else:
        customer_type = "unspecified"
    topics = []
    for topic, pattern in {
        "identity": r"identitat|buletin|pașaport|passport|identity",
        "ownership": r"beneficiar|acționar|administrator|owner|shareholder",
        "address": r"adres|domicili|address",
        "tax": r"cui|fiscal|tax",
    }.items():
        if re.search(pattern, lower):
            topics.append(topic)
    return {"intent": "onboarding", "customer_type": customer_type, "topics": topics or ["general"]}


def onboarding_checklist(text: str) -> dict:
    kind = classify_onboarding(text)["customer_type"]
    categories = ["identity", "contact details", "consents"]
    if kind == "business":
        categories += ["company registration", "representation authority", "beneficial ownership"]
    elif kind == "unspecified":
        categories.insert(0, "customer type clarification")
    return {
        "customer_type": kind,
        "evidence_categories": categories,
        "authoritative": False,
        "instruction": (
            "Confirm exact requirements against retrieved bank policy. When customer "
            "type is unspecified, distinguish individual and business requirements "
            "or ask for clarification; do not merge them into one mandatory list."
        ),
    }


def route_escalation(text: str) -> dict:
    lower = text.lower()
    if re.search(r"fraud|suspect|aml|pep|compliance", lower):
        team, priority = "Compliance", "high"
    elif re.search(r"blocat|eroare|nu funcționează|blocked|failed", lower):
        team, priority = "Customer Support", "normal"
    else:
        team, priority = "Onboarding Operations", "normal"
    return {"team": team, "priority": priority, "automatic_decision": False}


_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}


def safe_calculate(expression: str) -> float | int:
    node = ast.parse(expression.replace(",", "."), mode="eval")

    def evaluate(item: ast.AST) -> float | int:
        if isinstance(item, ast.Expression):
            return evaluate(item.body)
        if isinstance(item, ast.Constant) and type(item.value) in {int, float}:
            return item.value
        if isinstance(item, ast.UnaryOp) and isinstance(item.op, (ast.UAdd, ast.USub)):
            value = evaluate(item.operand)
            return value if isinstance(item.op, ast.UAdd) else -value
        if isinstance(item, ast.BinOp) and type(item.op) in _OPS:
            left, right = evaluate(item.left), evaluate(item.right)
            if isinstance(item.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is outside the safe range")
            return _OPS[type(item.op)](left, right)
        raise ValueError("Only numeric arithmetic is allowed")

    result = evaluate(node)
    if abs(float(result)) > 1e15:
        raise ValueError("Result is outside the safe range")
    return result


LOCAL_EXECUTORS = {
    "language_detector": lambda call, text: detect_language(text),
    "pii_safety_scan": lambda call, text: scan_pii(text),
    "onboarding_intent_classifier": lambda call, text: classify_onboarding(text),
    "onboarding_checklist": lambda call, text: onboarding_checklist(text),
    "escalation_router": lambda call, text: route_escalation(text),
    "safe_calculator": lambda call, text: {"expression": call.arguments["expression"], "result": safe_calculate(call.arguments["expression"])},
}


def execute_call(call: ToolCall, question: str) -> ToolResult:
    executor = LOCAL_EXECUTORS.get(call.name)
    if not executor:
        return ToolResult(call.name, "delegated", {"phase": call.phase})
    try:
        return ToolResult(call.name, "completed", executor(call, question))
    except Exception as error:
        return ToolResult(call.name, "error", error=str(error))
