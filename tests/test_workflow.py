import pytest

from app.services.exceptions import ReviewAlreadyResolvedError
from app.services.schemas import DecisionInput, ReviewResolution
from app.services.workflow import build_metrics, decide_request, list_requests, resolve_review


def test_review_required_and_resolved(db_session):
    result = decide_request(
        db_session,
        DecisionInput(
            user_name="Aaron",
            role="viewer",
            prompt="Export confidential finance data",
            evidence_strength=0.9,
            sensitivity="high",
        ),
    )
    assert result["outcome"] == "review_required"

    metrics = build_metrics(db_session)
    assert metrics["open_reviews"] >= 1

    requests_page = list_requests(db_session, limit=10, offset=0)
    review_id = next(item["review_id"] for item in requests_page["items"] if item["review_id"] is not None)
    resolved = resolve_review(
        db_session,
        review_id,
        ReviewResolution(reviewer="Manager", decision="approved", resolution_note="Approved after manual check"),
    )
    assert resolved["status"] == "approved"


def test_review_resolution_is_idempotent(db_session):
    decide_request(
        db_session,
        DecisionInput(
            user_name="Aaron",
            role="viewer",
            prompt="Export confidential finance data",
            evidence_strength=0.9,
            sensitivity="high",
        ),
    )
    requests_page = list_requests(db_session, limit=10, offset=0)
    review_id = next(item["review_id"] for item in requests_page["items"] if item["review_id"] is not None)
    resolve_review(
        db_session,
        review_id,
        ReviewResolution(reviewer="Manager", decision="approved", resolution_note="Approved after manual check"),
    )
    with pytest.raises(ReviewAlreadyResolvedError):
        resolve_review(
            db_session,
            review_id,
            ReviewResolution(reviewer="Manager 2", decision="rejected", resolution_note="Second decision should fail"),
        )
