from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.services.schemas import DecisionInput

NEGATING_PATTERNS = [
    re.compile(r"\bdo\s+not\s+(delete|wipe|destroy|erase|drop)\b"),
    re.compile(r"\bdon'?t\s+(delete|wipe|destroy|erase|drop)\b"),
    re.compile(r"\bavoid\s+(deleting|wiping|destroying|erasing|dropping)\b"),
]
EXPLANATORY_PATTERNS = [
    re.compile(r"\b(explain|understand|describe|why does|how does|tell me about)\b"),
]
AMBIGUOUS_PATTERNS = {
    "handle this",
    "take care of it",
    "fix it",
    "do the thing",
    "can you do this",
    "help with this",
}
SENSITIVE_TERMS = {"confidential", "payroll", "customer records", "finance", "export data"}
DESTRUCTIVE_PATTERNS = [
    re.compile(r"\b(delete|wipe|destroy|erase)\b"),
    re.compile(r"\bdrop\s+database\b"),
]
ROLE_RISK_OFFSET = {"viewer": 20, "analyst": 10, "architect": 0, "admin": -10}


@dataclass
class PolicyDecision:
    outcome: str
    risk_score: int
    reasons: list[str]


@dataclass
class PolicyContext:
    payload: DecisionInput
    risk_score: int
    reasons: list[str]


class PolicyRule(Protocol):
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        ...


def _mentions_destructive_action(prompt: str) -> bool:
    normalized = " ".join(prompt.lower().split())
    if any(pattern.search(normalized) for pattern in EXPLANATORY_PATTERNS):
        return False
    if any(pattern.search(normalized) for pattern in NEGATING_PATTERNS):
        return False
    return any(pattern.search(normalized) for pattern in DESTRUCTIVE_PATTERNS)


def _is_ambiguous(prompt: str) -> bool:
    normalized = " ".join(prompt.lower().split())
    if normalized in AMBIGUOUS_PATTERNS:
        return True
    if len(normalized.split()) < 3:
        return True
    return any(pattern in normalized for pattern in AMBIGUOUS_PATTERNS)


class DestructiveActionRule:
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        if _mentions_destructive_action(context.payload.prompt):
            context.risk_score += 60
            context.reasons.append("Destructive action detected")
            return PolicyDecision("refused", min(context.risk_score, 100), context.reasons.copy())
        return None


class AmbiguityRule:
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        if _is_ambiguous(context.payload.prompt):
            context.reasons.append("Prompt is too ambiguous to execute safely")
            return PolicyDecision("clarify", min(max(context.risk_score, 10), 100), context.reasons.copy())
        return None


class ViewerSensitiveRule:
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        prompt = context.payload.prompt.lower()
        if context.payload.role == "viewer" and (
            context.payload.sensitivity == "high" or any(term in prompt for term in SENSITIVE_TERMS)
        ):
            context.risk_score += 35
            context.reasons.append("Viewer role cannot directly access high-risk or sensitive requests")
            return PolicyDecision("review_required", min(context.risk_score, 100), context.reasons.copy())
        return None


class WeakEvidenceRule:
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        if context.payload.evidence_strength < 0.35:
            context.risk_score += 20
            context.reasons.append("Evidence strength is too weak for direct approval")
            return PolicyDecision("fallback", min(context.risk_score, 100), context.reasons.copy())
        return None


class HighSensitivityRule:
    def apply(self, context: PolicyContext) -> PolicyDecision | None:
        if context.payload.sensitivity == "high" and context.payload.role != "admin":
            context.risk_score += 20
            context.reasons.append("High-sensitivity request requires elevated review")
            return PolicyDecision("review_required", min(context.risk_score, 100), context.reasons.copy())
        return None


RULES: list[PolicyRule] = [
    DestructiveActionRule(),
    AmbiguityRule(),
    ViewerSensitiveRule(),
    WeakEvidenceRule(),
    HighSensitivityRule(),
]


def evaluate_policy(payload: DecisionInput) -> PolicyDecision:
    risk_score = 20 + ROLE_RISK_OFFSET[payload.role]
    reasons: list[str] = []

    if payload.sensitivity == "high":
        risk_score += 30
        reasons.append("Request marked high sensitivity")
    elif payload.sensitivity == "medium":
        risk_score += 15
        reasons.append("Request marked medium sensitivity")

    context = PolicyContext(payload=payload, risk_score=risk_score, reasons=reasons)

    for rule in RULES:
        decision = rule.apply(context)
        if decision is not None:
            return decision

    context.reasons.append("Request passed policy checks")
    return PolicyDecision("approved", min(context.risk_score, 100), context.reasons.copy())
