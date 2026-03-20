from __future__ import annotations

from app.services.schemas import DecisionInput
from app.services.utils import prompt_preview


def compose_response(payload: DecisionInput, outcome: str, reasons: list[str]) -> str:
    preview = prompt_preview(payload.prompt, limit=90)
    role_text = payload.role.replace("_", " ")
    reason_text = "; ".join(reasons)

    if outcome == "approved":
        return (
            f"Approved for release for the {role_text} role. Answer '{preview}' in a bounded way, "
            f"cite supporting evidence, and keep the response proportional to the available proof. "
            f"Release rationale: {reason_text}."
        )
    if outcome == "clarify":
        return (
            f"Do not answer '{preview}' yet. Ask one narrowing question first so the user clarifies scope, "
            f"intent, or expected output. Reason: {reason_text}."
        )
    if outcome == "fallback":
        return (
            f"Do not provide a final answer to '{preview}'. Give a safe fallback response that explains evidence is weak "
            f"for the {role_text} role and request stronger source material or additional context. Reason: {reason_text}."
        )
    if outcome == "review_required":
        return (
            f"Do not release '{preview}' directly. Route it to human review with the current risk signals, role context, "
            f"and supporting notes. Reviewer note: {reason_text}."
        )
    return (
        f"Refuse '{preview}' politely. Explain that the requested action is blocked by policy or risk controls and offer "
        f"a safer next step where appropriate. Reason: {reason_text}."
    )
