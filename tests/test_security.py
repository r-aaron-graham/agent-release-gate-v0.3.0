"""Regression tests for admin-session and rate-limit hardening."""

import base64
import json

import pytest
from bs4 import BeautifulSoup

from app.core import security
from app.core.config import settings


@pytest.fixture(autouse=True)
def fresh_rate_limiter():
    security.rate_limiter._hits.clear()
    yield
    security.rate_limiter._hits.clear()


def _csrf(client, path="/admin/login") -> str:
    soup = BeautifulSoup(client.get(path).text, "html.parser")
    return soup.find("input", {"name": "csrf_token"})["value"]


def _session_payload(client) -> dict:
    raw = client.cookies.get("session")
    data = raw.split(".")[0]
    return json.loads(base64.b64decode(data + "=" * (-len(data) % 4)))


def _login(client, api_key: str, **headers: str):
    return client.post(
        "/admin/login",
        data={"api_key": api_key, "csrf_token": _csrf(client)},
        headers=headers,
        follow_redirects=False,
    )


def test_session_cookie_never_contains_the_admin_key(client):
    assert _login(client, "test-admin-key").status_code == 303
    payload = _session_payload(client)
    assert "test-admin-key" not in json.dumps(payload)
    assert "admin_token" not in payload
    assert client.get("/admin").status_code == 200


def test_legacy_or_forged_session_value_is_rejected(client, monkeypatch):
    assert _login(client, "test-admin-key").status_code == 303
    # Rotating the key must invalidate existing admin sessions.
    monkeypatch.setattr(settings, "admin_api_key", "rotated-key")
    assert client.get("/admin", follow_redirects=False).status_code in (303, 401)


def test_admin_login_is_rate_limited(client):
    codes = [_login(client, "wrong").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_spoofed_forwarded_for_cannot_bypass_rate_limit(client):
    codes = [
        _login(client, "wrong", **{"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(11)
    ]
    assert codes[-1] == 429


def test_forwarded_for_is_honoured_when_proxy_is_trusted(client, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    codes = [
        _login(client, "wrong", **{"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(11)
    ]
    assert 429 not in codes


def test_api_rejects_missing_and_wrong_keys(client):
    assert client.get("/api/v1/requests").status_code == 401
    assert client.get("/api/v1/requests", headers={"Authorization": "Bearer nope"}).status_code == 401
    ok = client.get("/api/v1/requests", headers={"X-Admin-Api-Key": "test-admin-key"})
    assert ok.status_code == 200


def test_login_requires_valid_csrf(client):
    client.get("/admin/login")
    res = client.post(
        "/admin/login", data={"api_key": "test-admin-key", "csrf_token": "forged"}, follow_redirects=False
    )
    assert res.status_code == 403
