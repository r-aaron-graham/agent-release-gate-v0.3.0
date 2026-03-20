from __future__ import annotations

from datetime import datetime, timezone
import secrets


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def prompt_preview(prompt: str, limit: int = 120) -> str:
    text = " ".join(prompt.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)
