from app.services.policy import evaluate_policy
from app.services.schemas import DecisionInput


def test_destructive_prompt_is_refused():
    payload = DecisionInput(user_name="Aaron", role="analyst", prompt="Delete the customer records", evidence_strength=0.9, sensitivity="high")
    result = evaluate_policy(payload)
    assert result.outcome == "refused"


def test_ambiguous_prompt_requests_clarification():
    payload = DecisionInput(user_name="Aaron", role="analyst", prompt="Handle this", evidence_strength=0.8, sensitivity="low")
    result = evaluate_policy(payload)
    assert result.outcome == "clarify"


def test_weak_evidence_falls_back():
    payload = DecisionInput(user_name="Aaron", role="architect", prompt="Recommend the production change for rollout", evidence_strength=0.2, sensitivity="medium")
    result = evaluate_policy(payload)
    assert result.outcome == "fallback"


def test_negated_destructive_phrase_is_not_refused():
    payload = DecisionInput(user_name="Aaron", role="analyst", prompt="Do not delete this file until I confirm", evidence_strength=0.9, sensitivity="low")
    result = evaluate_policy(payload)
    assert result.outcome != "refused"
