from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app


def _configure(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "provenance.db"))
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    monkeypatch.setattr(settings, "session_cookie_name", "akh_session")
    monkeypatch.setattr(settings, "session_ttl_hours", 24)
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(
        settings,
        "privacy_ledger_path",
        str(tmp_path / "privacy-deletions.db"),
    )
    store.init_db()


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct horse battery staple",
            "invite_code": "invite-2026-safe",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def _source_payload() -> dict:
    return {
        "source_path": "questions/ai-infra/gpu-memory.md",
        "source_url": "https://example.com/interview/gpu-memory",
        "source_title": "AI Infra interview notes",
        "publisher": "Example Publisher",
        "retrieved_at": "2026-08-29T10:00:00+00:00",
        "rights_note": "Public interview experience; retain attribution.",
    }


def test_admin_can_record_and_list_content_provenance(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    _register(admin, "owner@example.com")

    created = admin.post("/api/admin/content/sources", json=_source_payload())

    assert created.status_code == 201
    assert created.json()["source_url"] == _source_payload()["source_url"]
    assert created.json()["status"] == "active"
    listed = admin.get("/api/admin/content/sources")
    assert listed.status_code == 200
    assert listed.json()["sources"] == [created.json()]


def test_member_cannot_manage_content_provenance(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    member = TestClient(app)
    _register(admin, "owner@example.com")
    _register(member, "member@example.com")

    assert member.post(
        "/api/admin/content/sources", json=_source_payload()
    ).status_code == 403
    assert member.get("/api/admin/content/sources").status_code == 403


def test_takedown_request_updates_status_and_appends_audit_log(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    admin_user = _register(admin, "owner@example.com")
    source = admin.post(
        "/api/admin/content/sources", json=_source_payload()
    ).json()

    response = admin.post(
        f"/api/admin/content/sources/{source['id']}/takedown",
        json={"action": "requested", "reason": "Rights holder request #42"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"]["status"] == "takedown_requested"
    assert body["event"]["source_id"] == source["id"]
    assert body["event"]["actor_user_id"] == admin_user["id"]
    assert body["event"]["action"] == "requested"
    assert body["event"]["reason"] == "Rights holder request #42"

    second = admin.post(
        f"/api/admin/content/sources/{source['id']}/takedown",
        json={"action": "removed", "reason": "Source hidden from publication"},
    )
    assert second.status_code == 200
    detail = admin.get(f"/api/admin/content/sources/{source['id']}")
    assert detail.status_code == 200
    assert detail.json()["source"]["status"] == "removed"
    assert [event["action"] for event in detail.json()["events"]] == [
        "requested",
        "removed",
    ]


def test_provenance_rejects_invalid_url_and_unknown_source(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    _register(admin, "owner@example.com")
    invalid = _source_payload()
    invalid["source_url"] = "file:///private/corpus.md"

    assert admin.post("/api/admin/content/sources", json=invalid).status_code == 422
    missing = admin.post(
        "/api/admin/content/sources/missing/takedown",
        json={"action": "requested", "reason": "Cannot locate source"},
    )
    assert missing.status_code == 404


def test_takedown_log_is_append_only_but_account_deletion_anonymizes_actor(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    admin = TestClient(app)
    member = TestClient(app)
    _register(admin, "owner@example.com")
    member_user = _register(member, "member@example.com")
    source = admin.post(
        "/api/admin/content/sources", json=_source_payload()
    ).json()
    event = store.record_content_takedown(
        source["id"],
        member_user["id"],
        "requested",
        "Forwarded rights request",
    )["event"]

    with sqlite3.connect(settings.sqlite_path) as connection:
        with pytest.raises(
            sqlite3.IntegrityError,
            match="append-only",
        ):
            connection.execute(
                "UPDATE content_takedown_log SET reason = 'rewritten' WHERE id = ?",
                (event["id"],),
            )

    deleted = member.request(
        "DELETE",
        "/api/account",
        json={"password": "correct horse battery staple"},
    )
    assert deleted.status_code == 204
    with sqlite3.connect(settings.sqlite_path) as connection:
        actor = connection.execute(
            "SELECT actor_user_id FROM content_takedown_log WHERE id = ?",
            (event["id"],),
        ).fetchone()
    assert actor == (None,)


def test_schema_validation_rejects_extra_governance_trigger(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER unreviewed_governance_trigger
            AFTER INSERT ON content_sources
            BEGIN
                SELECT 1;
            END
            """
        )

    from app.db.migrations import validate_current_schema

    with sqlite3.connect(settings.sqlite_path) as connection:
        with pytest.raises(RuntimeError, match="governance guards"):
            validate_current_schema(connection)


def test_schema_validation_rejects_extra_governance_trigger(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    with sqlite3.connect(settings.sqlite_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER unreviewed_governance_trigger
            AFTER INSERT ON content_sources
            BEGIN
                SELECT 1;
            END
            """
        )

    from app.db.migrations import validate_current_schema

    with sqlite3.connect(settings.sqlite_path) as connection:
        with pytest.raises(RuntimeError, match="governance guards"):
            validate_current_schema(connection)
