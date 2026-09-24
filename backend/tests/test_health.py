from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app


client = TestClient(app)


def test_liveness_is_public_and_minimal():
    client.cookies.clear()

    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_schema_and_question_bank(tmp_path, monkeypatch):
    database = tmp_path / "ready.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    store.init_db()
    client.cookies.clear()

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["schema_version"] == "20260923_001"
    assert body["questions"] >= 120


def test_readiness_fails_closed_when_database_is_missing(tmp_path, monkeypatch):
    missing = Path(tmp_path) / "missing.db"
    monkeypatch.setattr(settings, "sqlite_path", str(missing))
    client.cookies.clear()

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
    }
    assert not missing.exists()


def test_readiness_rejects_incomplete_database_with_forged_version(
    tmp_path, monkeypatch
):
    forged = tmp_path / "forged.db"
    with sqlite3.connect(forged) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            INSERT INTO schema_migrations VALUES
              ('20260829_001', 'existing_schema_baseline', '2026-08-29'),
              ('20260829_002', 'backup_history', '2026-08-29'),
              ('20260829_003', 'content_provenance', '2026-08-29'),
              ('20260830_004', 'llm_protocol', '2026-08-30');
            """
        )
    monkeypatch.setattr(settings, "sqlite_path", str(forged))

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_readiness_rejects_database_missing_takedown_guard(tmp_path, monkeypatch):
    database = tmp_path / "missing-trigger.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    store.init_db()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER content_takedown_log_no_update")

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
