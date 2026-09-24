from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.db.backup import create_backup, restore_backup
from app.main import app
from app.privacy import ledger_cli
from app.privacy import tombstones
from app.privacy import tombstones


client = TestClient(app)
INVITE = "privacy-test-invite"
ADMIN_PASSWORD = "admin privacy password"
MEMBER_PASSWORD = "member privacy password"


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    database = tmp_path / "privacy.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    monkeypatch.setattr(settings, "auth_invite_code", INVITE)
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(
        settings,
        "privacy_ledger_path",
        str(tmp_path / "privacy-deletions.db"),
    )
    store.init_db()
    client.cookies.clear()
    yield database
    client.cookies.clear()


def _register(email: str, password: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "invite_code": INVITE},
    )
    assert response.status_code == 201
    return response.json()["user"]


def test_export_contains_only_authenticated_user_and_no_credential_material(
    isolated_database,
):
    admin = _register("admin@example.com", ADMIN_PASSWORD)
    store.save_quiz_answer(
        admin["id"], "admin-question", "admin private answer", 5, 90
    )
    with sqlite3.connect(isolated_database) as connection:
        connection.execute(
            """
            INSERT INTO user_settings (
                user_id, llm_base_url, llm_api_key_ciphertext,
                llm_api_key_nonce, llm_api_key_version, llm_api_key_hint,
                llm_api_key_audience, llm_protocol, llm_model, force_demo, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                admin["id"],
                "https://model.example.com/v1",
                "SECRET-CIPHERTEXT",
                "SECRET-NONCE",
                "v2",
                "abcd",
                "https://model.example.com",
                "anthropic_messages",
                "safe-model",
                0,
                "2026-08-29T00:00:00Z",
            ),
        )
    client.cookies.clear()
    member = _register("member@example.com", MEMBER_PASSWORD)
    store.save_quiz_answer(
        member["id"], "member-question", "member private answer", 3, 60
    )
    client.cookies.clear()
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": ADMIN_PASSWORD},
    ).status_code == 200

    response = client.get("/api/account/export")

    assert response.status_code == 200
    assert "attachment;" in response.headers["content-disposition"]
    payload = response.json()
    serialized = response.text
    assert payload["profile"]["email"] == "admin@example.com"
    assert payload["answers"][0]["question_id"] == "admin-question"
    assert payload["settings"]["has_api_key"] is True
    assert payload["settings"]["llm_protocol"] == "anthropic_messages"
    assert "member private answer" not in serialized
    for forbidden in (
        "SECRET-CIPHERTEXT",
        "SECRET-NONCE",
        "password_hash",
        "token_hash",
        "llm_api_key_ciphertext",
        "llm_api_key_nonce",
        "llm_api_key_hint",
    ):
        assert forbidden not in serialized


def test_account_deletion_requires_password_and_removes_member_data():
    _register("admin@example.com", ADMIN_PASSWORD)
    client.cookies.clear()
    member = _register("member@example.com", MEMBER_PASSWORD)
    store.save_quiz_answer(
        member["id"], "delete-question", "delete me", 3, 60
    )

    denied = client.request(
        "DELETE",
        "/api/account",
        json={"password": "wrong password value"},
    )
    assert denied.status_code == 403

    deleted = client.request(
        "DELETE",
        "/api/account",
        json={"password": MEMBER_PASSWORD},
    )
    assert deleted.status_code == 204
    assert store.list_quiz_history(member["id"]) == []
    login = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": MEMBER_PASSWORD},
    )
    assert login.status_code == 401


def test_last_administrator_cannot_delete_account_while_members_exist():
    _register("admin@example.com", ADMIN_PASSWORD)
    client.cookies.clear()
    _register("member@example.com", MEMBER_PASSWORD)
    client.cookies.clear()
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": ADMIN_PASSWORD},
    ).status_code == 200

    response = client.request(
        "DELETE",
        "/api/account",
        json={"password": ADMIN_PASSWORD},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "last_admin"


def test_deleted_account_is_not_resurrected_by_restoring_an_older_backup(
    isolated_database,
    tmp_path,
):
    _register("admin@example.com", ADMIN_PASSWORD)
    client.cookies.clear()
    member = _register("member@example.com", MEMBER_PASSWORD)
    backup = create_backup(tmp_path / "backups")

    deleted = client.request(
        "DELETE",
        "/api/account",
        json={"password": MEMBER_PASSWORD},
    )
    assert deleted.status_code == 204
    assert store.get_user_by_id(member["id"]) is None

    restore_backup(backup.path, target_path=isolated_database)

    assert store.get_user_by_id(member["id"]) is None
    assert client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": MEMBER_PASSWORD},
    ).status_code == 401


def test_durable_deletion_request_is_accepted_when_immediate_purge_fails(
    isolated_database,
):
    _register("admin@example.com", ADMIN_PASSWORD)
    client.cookies.clear()
    member = _register("member@example.com", MEMBER_PASSWORD)
    old_session = TestClient(app)
    assert old_session.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": MEMBER_PASSWORD},
    ).status_code == 200
    with sqlite3.connect(isolated_database) as connection:
        connection.execute(
            """
            CREATE TRIGGER injected_user_delete_failure
            BEFORE DELETE ON users
            WHEN OLD.id = '%s'
            BEGIN
                SELECT RAISE(ABORT, 'injected purge failure');
            END
            """ % member["id"]
        )

    response = client.request(
        "DELETE",
        "/api/account",
        json={"password": MEMBER_PASSWORD},
    )

    assert response.status_code == 204
    assert tombstones.is_deleted(member["id"]) is True
    with sqlite3.connect(isolated_database) as connection:
        assert connection.execute(
            "SELECT id FROM users WHERE id = ?", (member["id"],)
        ).fetchone() == (member["id"],)
        connection.execute("DROP TRIGGER injected_user_delete_failure")
    assert old_session.get("/api/account/export").status_code == 401
    assert TestClient(app).post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": MEMBER_PASSWORD},
    ).status_code == 401

    assert tombstones.apply_deletions(isolated_database) == 1
    assert store.get_user_by_id(member["id"]) is None


def test_privacy_ledger_rejects_missing_or_tampered_schema(
    isolated_database,
):
    ledger = settings.privacy_ledger_path
    with sqlite3.connect(ledger) as connection:
        connection.execute("DROP TRIGGER account_deletions_no_delete")

    with pytest.raises(tombstones.PrivacyLedgerError, match="invalid"):
        tombstones.validate_ledger()
    with pytest.raises(tombstones.PrivacyLedgerError, match="invalid"):
        tombstones.apply_deletions(isolated_database)


def test_production_does_not_recreate_a_missing_privacy_ledger(
    tmp_path,
    monkeypatch,
):
    missing = tmp_path / "missing-ledger.db"
    monkeypatch.setattr(settings, "privacy_ledger_path", str(missing))
    monkeypatch.setattr(settings, "privacy_ledger_id", "deployment-ledger-2026")
    monkeypatch.setattr(settings, "app_env", "production")

    with pytest.raises(tombstones.PrivacyLedgerError, match="missing"):
        tombstones.ensure_ledger()
    assert not missing.exists()


def test_legacy_privacy_ledger_upgrade_preserves_rows_and_adds_append_only_guards():
    ledger = Path(settings.privacy_ledger_path)
    ledger.unlink()
    original_rows = [
        ("deleted-user-1", "2026-08-28T01:02:03+00:00"),
        ("deleted-user-2", "2026-08-29T04:05:06+00:00"),
    ]
    with sqlite3.connect(ledger) as connection:
        connection.execute(tombstones.DELETIONS_DDL)
        connection.executemany(
            "INSERT INTO account_deletions (user_id, deleted_at) VALUES (?, ?)",
            original_rows,
        )

    tombstones.upgrade_legacy_ledger()

    tombstones.validate_ledger()
    with sqlite3.connect(ledger) as connection:
        assert connection.execute(
            "SELECT user_id, deleted_at FROM account_deletions ORDER BY user_id"
        ).fetchall() == original_rows
        assert connection.execute(
            "SELECT schema_version, ledger_id FROM privacy_ledger_metadata"
        ).fetchall() == [
            (tombstones.LEDGER_SCHEMA_VERSION, settings.privacy_ledger_id)
        ]
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM account_deletions WHERE user_id = 'deleted-user-1'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE account_deletions SET deleted_at = 'changed'"
            )


def test_legacy_privacy_ledger_upgrade_rejects_unknown_schema_without_mutation():
    ledger = Path(settings.privacy_ledger_path)
    ledger.unlink()
    with sqlite3.connect(ledger) as connection:
        connection.execute(tombstones.DELETIONS_DDL)
        connection.execute(
            "INSERT INTO account_deletions (user_id, deleted_at) VALUES (?, ?)",
            ("deleted-user", "2026-08-29T04:05:06+00:00"),
        )
        connection.execute("CREATE TABLE unexpected_data (value TEXT NOT NULL)")

    with pytest.raises(tombstones.PrivacyLedgerError, match="legacy"):
        tombstones.upgrade_legacy_ledger()

    with sqlite3.connect(ledger) as connection:
        assert connection.execute(
            "SELECT user_id, deleted_at FROM account_deletions"
        ).fetchall() == [("deleted-user", "2026-08-29T04:05:06+00:00")]
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'privacy_ledger_metadata'"
        ).fetchone() is None


def test_privacy_ledger_cli_exposes_explicit_legacy_upgrade(monkeypatch, capsys):
    ledger = Path(settings.privacy_ledger_path)
    ledger.unlink()
    with sqlite3.connect(ledger) as connection:
        connection.execute(tombstones.DELETIONS_DDL)
        connection.execute(
            "INSERT INTO account_deletions (user_id, deleted_at) VALUES (?, ?)",
            ("deleted-user", "2026-08-29T04:05:06+00:00"),
        )
    monkeypatch.setattr(sys, "argv", ["privacy-ledger", "upgrade"])

    assert ledger_cli.main() == 0

    assert "upgraded privacy deletion ledger" in capsys.readouterr().out
    tombstones.validate_ledger()
    with sqlite3.connect(ledger) as connection:
        assert connection.execute(
            "SELECT COUNT(1) FROM account_deletions"
        ).fetchone() == (1,)


def test_privacy_ledger_rows_are_append_only(isolated_database):
    tombstones.record_deletion("deleted-user")
    with sqlite3.connect(settings.privacy_ledger_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM account_deletions WHERE user_id = 'deleted-user'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE account_deletions SET deleted_at = 'changed'"
            )


def test_request_path_tombstone_lookup_does_not_run_full_integrity_scan(
    isolated_database,
    monkeypatch,
):
    tombstones.record_deletion("deleted-user")
    monkeypatch.setattr(
        tombstones,
        "validate_ledger",
        lambda: (_ for _ in ()).throw(AssertionError("full scan on request path")),
    )

    assert tombstones.is_deleted("deleted-user") is True
    assert tombstones.is_deleted("active-user") is False
