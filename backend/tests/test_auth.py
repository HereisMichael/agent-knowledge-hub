from __future__ import annotations

import importlib

import pytest

from app.config import settings
from app.db import store


def _use_database(tmp_path, monkeypatch):
    database = tmp_path / "auth.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    store.init_db()
    return database


def test_first_user_is_admin_and_second_user_is_member(tmp_path, monkeypatch):
    _use_database(tmp_path, monkeypatch)

    first = store.create_user("owner@example.com", "hash-1")
    second = store.create_user("member@example.com", "hash-2")

    assert first["role"] == "admin"
    assert second["role"] == "member"


def test_user_email_is_normalized_and_unique(tmp_path, monkeypatch):
    _use_database(tmp_path, monkeypatch)
    created = store.create_user(" Owner@Example.COM ", "hash-1")

    assert created["email"] == "owner@example.com"
    assert store.get_user_by_email("OWNER@example.com")["id"] == created["id"]


def test_expired_session_does_not_resolve_identity(tmp_path, monkeypatch):
    _use_database(tmp_path, monkeypatch)
    user = store.create_user("owner@example.com", "hash")
    store.create_auth_session(user["id"], "token-hash", "2026-01-01T00:00:00+00:00")

    assert store.get_identity_by_token_hash(
        "token-hash", "2026-01-02T00:00:00+00:00"
    ) is None


def test_revoked_session_does_not_resolve_identity(tmp_path, monkeypatch):
    _use_database(tmp_path, monkeypatch)
    user = store.create_user("owner@example.com", "hash")
    store.create_auth_session(user["id"], "token-hash", "2027-01-01T00:00:00+00:00")

    identity = store.get_identity_by_token_hash(
        "token-hash", "2026-01-02T00:00:00+00:00"
    )
    assert identity == {
        "user_id": user["id"],
        "email": "owner@example.com",
        "role": "admin",
    }

    store.revoke_auth_session("token-hash")
    assert store.get_identity_by_token_hash(
        "token-hash", "2026-01-02T00:00:00+00:00"
    ) is None


def _configure_auth(tmp_path, monkeypatch):
    database = _use_database(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    monkeypatch.setattr(settings, "session_ttl_hours", 24)
    return database


def _auth_service():
    return importlib.import_module("app.auth.service")


def test_register_rejects_wrong_invite_code(tmp_path, monkeypatch):
    _configure_auth(tmp_path, monkeypatch)
    auth = _auth_service()

    with pytest.raises(auth.AuthError) as error:
        auth.register(
            "owner@example.com",
            "correct horse battery staple",
            "wrong-invite",
        )

    assert error.value.code == "invalid_invite"


def test_register_stores_password_hash_and_never_raw_session_token(tmp_path, monkeypatch):
    database = _configure_auth(tmp_path, monkeypatch)
    auth = _auth_service()

    grant = auth.register(
        "owner@example.com",
        "correct horse battery staple",
        "invite-2026-safe",
    )

    database_bytes = database.read_bytes()
    assert grant.token.encode() not in database_bytes
    assert b"correct horse battery staple" not in database_bytes
    assert auth.authenticate(grant.token) == grant.identity


def test_login_rejects_invalid_password_and_logout_revokes_token(tmp_path, monkeypatch):
    _configure_auth(tmp_path, monkeypatch)
    auth = _auth_service()
    registered = auth.register(
        "owner@example.com",
        "correct horse battery staple",
        "invite-2026-safe",
    )

    with pytest.raises(auth.AuthError) as error:
        auth.login("owner@example.com", "incorrect-password")
    assert error.value.code == "invalid_credentials"

    logged_in = auth.login("OWNER@example.com", "correct horse battery staple")
    assert logged_in.identity == registered.identity
    auth.logout(logged_in.token)
    with pytest.raises(auth.AuthError) as revoked:
        auth.authenticate(logged_in.token)
    assert revoked.value.code == "invalid_session"


def test_register_rejects_short_password_and_duplicate_email(tmp_path, monkeypatch):
    _configure_auth(tmp_path, monkeypatch)
    auth = _auth_service()

    with pytest.raises(auth.AuthError) as short:
        auth.register("owner@example.com", "too-short", "invite-2026-safe")
    assert short.value.code == "weak_password"

    auth.register(
        "owner@example.com",
        "correct horse battery staple",
        "invite-2026-safe",
    )
    with pytest.raises(auth.AuthError) as duplicate:
        auth.register(
            " OWNER@example.com ",
            "another correct horse battery staple",
            "invite-2026-safe",
        )
    assert duplicate.value.code == "email_exists"
