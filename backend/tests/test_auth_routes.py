from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "auth-routes.db"))
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    monkeypatch.setattr(settings, "session_cookie_name", "akh_session")
    monkeypatch.setattr(settings, "session_ttl_hours", 24)
    monkeypatch.setattr(settings, "app_env", "development")
    store.init_db()
    return TestClient(app)


def _register(client: TestClient, email: str = "owner@example.com"):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "invite_code": "invite-2026-safe",
        },
    )


def test_register_sets_http_only_same_site_cookie(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = _register(client)

    assert response.status_code == 201
    assert response.json()["user"] == {
        "id": response.json()["user"]["id"],
        "email": "owner@example.com",
        "role": "admin",
    }
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("akh_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie


def test_me_rejects_anonymous_request(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "authentication_required"


def test_login_me_and_logout_session_flow(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _register(client)
    client.cookies.clear()

    login = client.post(
        "/api/auth/login",
        json={
            "email": "OWNER@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert login.status_code == 200
    assert client.get("/api/auth/me").json()["user"]["email"] == "owner@example.com"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_auth_errors_use_stable_status_codes(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    wrong_invite = client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "correct horse battery staple",
            "invite_code": "wrong",
        },
    )
    assert wrong_invite.status_code == 403
    assert wrong_invite.json()["detail"] == "invalid_invite"

    assert _register(client).status_code == 201
    duplicate = _register(client)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "email_exists"

    invalid_login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "incorrect-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "invalid_credentials"


def test_production_cookie_is_secure(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "app_env", "production")

    response = _register(client)

    assert "Secure" in response.headers["set-cookie"]

