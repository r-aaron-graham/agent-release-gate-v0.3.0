from __future__ import annotations

import hmac
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock
from typing import Callable, ParamSpec, TypeVar

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings
from app.services.utils import new_csrf_token


P = ParamSpec("P")
T = TypeVar("T")


def _safe_compare(candidate: str | None, expected: str) -> bool:
    if candidate is None:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def _extract_token(authorization: str | None, x_admin_api_key: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value:
            return value.strip()
    if x_admin_api_key:
        return x_admin_api_key.strip()
    return None


def verify_admin_api_key(
    authorization: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> str:
    token = _extract_token(authorization, x_admin_api_key)
    if not _safe_compare(token, settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid admin API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token or ""


def require_admin_session(request: Request) -> str:
    admin_token = request.session.get("admin_token")
    if not _safe_compare(admin_token, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session required")
    return admin_token or ""


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = new_csrf_token()
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, csrf_token: str | None) -> None:
    session_token = request.session.get("csrf_token")
    if not session_token or not csrf_token or not hmac.compare_digest(session_token, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[datetime]] = {}
        self._lock = Lock()

    def enforce(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=window_seconds)
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] < threshold:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
            bucket.append(now)


rate_limiter = InMemoryRateLimiter()


def client_identifier(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    return client_ip
