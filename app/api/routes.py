from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import (
    client_identifier,
    ensure_csrf_token,
    rate_limiter,
    require_admin_session,
    validate_csrf,
    verify_admin_api_key,
)
from app.services.exceptions import ReviewAlreadyResolvedError, ReviewNotFoundError
from app.services.schemas import DecisionInput, ReviewResolution
from app.services.workflow import build_metrics, decide_request, get_request_by_id, list_requests, resolve_review

ui_router = APIRouter()
api_router = APIRouter()


@ui_router.get("/", response_class=HTMLResponse)
def index(request: Request, request_id: int | None = None, db: Session = Depends(get_db)):
    latest_decision = get_request_by_id(db, request_id) if request_id is not None else None
    csrf_token = ensure_csrf_token(request)
    return request.app.state.templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_decision": latest_decision,
            "settings": settings,
            "csrf_token": csrf_token,
        },
    )


@ui_router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    csrf_token = ensure_csrf_token(request)
    return request.app.state.templates.TemplateResponse(
        request,
        "admin_login.html",
        {"settings": settings, "csrf_token": csrf_token},
    )


@ui_router.post("/admin/login")
def admin_login_submit(request: Request, api_key: str = Form(...), csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    rate_limiter.enforce(f"admin-login:{client_identifier(request)}", limit=10, window_seconds=60)
    from app.core.security import _safe_compare  # local import to keep helper private-ish

    if not _safe_compare(api_key.strip(), settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Valid admin API key required")
    request.session["admin_token"] = api_key.strip()
    request.session["csrf_token"] = ensure_csrf_token(request)
    return RedirectResponse(url="/admin", status_code=303)


@ui_router.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form(...)):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@ui_router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_session),
):
    csrf_token = ensure_csrf_token(request)
    metrics = build_metrics(db)
    requests_page = list_requests(db, limit=limit, offset=offset)
    return request.app.state.templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_decision": None,
            "admin_mode": True,
            "metrics": metrics,
            "requests_page": requests_page,
            "settings": settings,
            "csrf_token": csrf_token,
        },
    )


@ui_router.post("/submit", response_class=HTMLResponse)
def submit_form(
    request: Request,
    user_name: str = Form(...),
    role: str = Form(...),
    prompt: str = Form(...),
    evidence_strength: float = Form(...),
    sensitivity: str = Form(...),
    requested_action: str = Form(default=""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    if not settings.public_form_enabled:
        raise HTTPException(status_code=403, detail="Public form submissions are disabled")
    validate_csrf(request, csrf_token)
    rate_limiter.enforce(f"submit:{client_identifier(request)}", limit=settings.request_rate_limit_per_minute, window_seconds=60)
    try:
        payload = DecisionInput(
            user_name=user_name,
            role=role,
            prompt=prompt,
            evidence_strength=evidence_strength,
            sensitivity=sensitivity,
            requested_action=requested_action or None,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    result = decide_request(db, payload)
    return RedirectResponse(url=f"/?request_id={result['request_id']}", status_code=303)


@ui_router.post("/admin/reviews/{review_id}/resolve", response_class=HTMLResponse)
def resolve_review_form(
    request: Request,
    review_id: int,
    reviewer: str = Form(...),
    decision: str = Form(...),
    resolution_note: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin_session),
):
    validate_csrf(request, csrf_token)
    try:
        resolve_review(
            db,
            review_id,
            ReviewResolution(reviewer=reviewer, decision=decision, resolution_note=resolution_note),
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewAlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RedirectResponse(url="/admin", status_code=303)


@api_router.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}


@api_router.post("/requests")
def create_request(
    request: Request,
    payload: DecisionInput,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin_api_key),
):
    rate_limiter.enforce(f"api-create:{client_identifier(request)}", limit=settings.request_rate_limit_per_minute, window_seconds=60)
    return decide_request(db, payload)


@api_router.get("/requests")
def get_requests(
    limit: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin_api_key),
):
    return list_requests(db, limit=limit, offset=offset)


@api_router.get("/requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db), _: str = Depends(verify_admin_api_key)):
    item = get_request_by_id(db, request_id)
    if not item:
        raise HTTPException(status_code=404, detail="Request not found")
    return item


@api_router.get("/metrics")
def metrics(db: Session = Depends(get_db), _: str = Depends(verify_admin_api_key)):
    return build_metrics(db)


@api_router.post("/reviews/{review_id}/resolve")
def resolve_review_api(
    review_id: int,
    payload: ReviewResolution,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin_api_key),
):
    try:
        return resolve_review(db, review_id, payload)
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewAlreadyResolvedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
