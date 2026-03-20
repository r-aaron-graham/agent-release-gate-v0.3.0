from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.models import AuditEvent, RequestRecord, ReviewItem
from app.services.exceptions import ReviewAlreadyResolvedError, ReviewNotFoundError
from app.services.policy import evaluate_policy
from app.services.responses import compose_response
from app.services.schemas import (
    DecisionInput,
    PaginatedRequestList,
    PaginationMeta,
    RequestListItem,
    ReviewResolution,
    ReviewResolutionOutput,
)
from app.services.utils import prompt_preview


def decide_request(db: Session, payload: DecisionInput) -> dict:
    decision = evaluate_policy(payload)
    reason_summary = "; ".join(decision.reasons)
    suggested_response = compose_response(payload, decision.outcome, decision.reasons)

    record = RequestRecord(
        user_name=payload.user_name,
        role=payload.role,
        prompt=payload.prompt,
        prompt_preview=prompt_preview(payload.prompt, limit=140),
        evidence_strength=payload.evidence_strength,
        sensitivity=payload.sensitivity,
        requested_action=payload.requested_action,
        outcome=decision.outcome,
        reason_summary=reason_summary,
        suggested_response=suggested_response,
        risk_score=decision.risk_score,
    )
    db.add(record)
    db.flush()

    db.add_all(
        [
            AuditEvent(request_id=record.id, event_type="request_received", detail=f"Prompt submitted by {payload.user_name}"),
            AuditEvent(request_id=record.id, event_type="policy_decision", detail=reason_summary),
        ]
    )

    if decision.outcome == "review_required":
        db.add(ReviewItem(request_id=record.id, status="open"))
        db.add(AuditEvent(request_id=record.id, event_type="review_opened", detail="Human review required"))

    db.commit()
    db.refresh(record)
    return {
        "request_id": record.id,
        "outcome": record.outcome,
        "risk_score": record.risk_score,
        "reasons": decision.reasons,
        "suggested_response": record.suggested_response,
        "created_at": record.created_at,
    }


def get_request_by_id(db: Session, request_id: int) -> dict | None:
    row = (
        db.query(RequestRecord)
        .options(joinedload(RequestRecord.review_item))
        .filter(RequestRecord.id == request_id)
        .first()
    )
    if not row:
        return None
    return RequestListItem(
        id=row.id,
        user_name=row.user_name,
        role=row.role,
        prompt=row.prompt,
        prompt_preview=row.prompt_preview,
        evidence_strength=row.evidence_strength,
        sensitivity=row.sensitivity,
        requested_action=row.requested_action,
        outcome=row.outcome,
        risk_score=row.risk_score,
        reason_summary=row.reason_summary,
        suggested_response=row.suggested_response,
        created_at=row.created_at,
        review_id=row.review_item.id if row.review_item else None,
        review_status=row.review_item.status if row.review_item else None,
        review_reviewer=row.review_item.reviewer if row.review_item else None,
    ).model_dump(mode="json")


def list_requests(db: Session, limit: int, offset: int) -> dict:
    total = db.query(func.count(RequestRecord.id)).scalar() or 0
    rows = (
        db.query(RequestRecord)
        .options(joinedload(RequestRecord.review_item))
        .order_by(RequestRecord.created_at.desc(), RequestRecord.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [
        RequestListItem(
            id=row.id,
            user_name=row.user_name,
            role=row.role,
            prompt=row.prompt,
            prompt_preview=row.prompt_preview,
            evidence_strength=row.evidence_strength,
            sensitivity=row.sensitivity,
            requested_action=row.requested_action,
            outcome=row.outcome,
            risk_score=row.risk_score,
            reason_summary=row.reason_summary,
            suggested_response=row.suggested_response,
            created_at=row.created_at,
            review_id=row.review_item.id if row.review_item else None,
            review_status=row.review_item.status if row.review_item else None,
            review_reviewer=row.review_item.reviewer if row.review_item else None,
        )
        for row in rows
    ]
    return PaginatedRequestList(
        items=items,
        pagination=PaginationMeta(total=total, limit=limit, offset=offset, has_more=offset + limit < total),
    ).model_dump(mode="json")


def build_metrics(db: Session) -> dict:
    total = db.query(func.count(RequestRecord.id)).scalar() or 0
    counts = {status: 0 for status in ["approved", "clarify", "fallback", "review_required", "refused"]}
    rows = db.query(RequestRecord.outcome, func.count(RequestRecord.id)).group_by(RequestRecord.outcome).all()
    for outcome, count in rows:
        counts[outcome] = count
    open_reviews = db.query(func.count(ReviewItem.id)).filter(ReviewItem.status == "open").scalar() or 0
    return {"total_requests": total, **counts, "open_reviews": open_reviews}


def resolve_review(db: Session, review_id: int, payload: ReviewResolution) -> dict:
    item = db.query(ReviewItem).filter(ReviewItem.id == review_id).first()
    if not item:
        raise ReviewNotFoundError(f"Review item {review_id} not found")
    if item.status != "open":
        raise ReviewAlreadyResolvedError(f"Review item {review_id} is already {item.status}")

    item.status = payload.decision
    item.reviewer = payload.reviewer
    item.resolution_note = payload.resolution_note
    db.add(
        AuditEvent(
            request_id=item.request_id,
            event_type="review_resolved",
            detail=f"{payload.decision} by {payload.reviewer}: {payload.resolution_note}",
        )
    )
    db.commit()
    db.refresh(item)
    return ReviewResolutionOutput(
        review_id=item.id,
        status=item.status,
        reviewer=item.reviewer or payload.reviewer,
        resolution_note=item.resolution_note or payload.resolution_note,
    ).model_dump(mode="json")
