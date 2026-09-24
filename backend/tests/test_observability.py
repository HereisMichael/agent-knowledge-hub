from __future__ import annotations

import importlib
import logging

from fastapi.testclient import TestClient

from app.config import settings
from app.llm.client import record_model_usage
from app.llm.protocols import ModelUsage
from app.main import app


client = TestClient(app)


def test_request_id_is_publicly_returned_and_validated():
    client.cookies.clear()

    supplied = client.get(
        "/api/health/live",
        headers={"X-Request-ID": "deploy-check-123"},
    )
    rejected = client.get(
        "/api/health/live",
        headers={"X-Request-ID": "bad id with spaces"},
    )

    assert supplied.headers["X-Request-ID"] == "deploy-check-123"
    assert rejected.headers["X-Request-ID"] != "bad id with spaces"
    assert len(rejected.headers["X-Request-ID"]) == 32


def test_request_log_excludes_query_and_marks_server_failures(
    tmp_path, monkeypatch, caplog
):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "missing.db"))
    client.cookies.clear()
    caplog.set_level(logging.INFO, logger="akh.request")

    response = client.get(
        "/api/health/ready?api_key=must-never-appear",
        headers={"X-Request-ID": "incident-123456"},
    )

    assert response.status_code == 503
    record = next(
        item for item in caplog.records if item.getMessage() == "request_failed"
    )
    assert record.request_id == "incident-123456"
    assert record.path == "/api/health/ready"
    assert record.status_code == 503
    assert "must-never-appear" not in record.getMessage()


def test_large_model_usage_emits_sanitized_warning(monkeypatch, caplog):
    monkeypatch.setattr(settings, "model_token_alert_threshold", 100)
    usage = ModelUsage(prompt_tokens=80, completion_tokens=50, total_tokens=130)
    caplog.set_level(logging.INFO, logger="akh.model")

    record_model_usage(usage, model="safe-model-name")

    record = next(
        item
        for item in caplog.records
        if item.getMessage() == "model_token_threshold_exceeded"
    )
    assert record.levelno == logging.WARNING
    assert record.total_tokens == 130
    assert record.prompt_tokens == 80
    assert record.completion_tokens == 50
    assert not hasattr(record, "prompt")
    assert not hasattr(record, "api_key")


def test_request_log_uses_route_template_instead_of_dynamic_secret(
    tmp_path,
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "routes.db"))
    monkeypatch.setattr(settings, "auth_invite_code", "observability-invite")
    from app.db import store

    store.init_db()
    authenticated = TestClient(app)
    registered = authenticated.post(
        "/api/auth/register",
        json={
            "email": "logs@example.com",
            "password": "observability password",
            "invite_code": "observability-invite",
        },
    )
    assert registered.status_code == 201
    caplog.set_level(logging.INFO, logger="akh.request")

    response = authenticated.get(
        "/api/mock/sessions/secret-path-value",
        headers={"X-Request-ID": "route-template-123"},
    )

    assert response.status_code == 404
    record = next(
        item
        for item in caplog.records
        if getattr(item, "request_id", "") == "route-template-123"
    )
    assert record.path == "/api/mock/sessions/{session_id}"
    assert "secret-path-value" not in record.path


def test_unhandled_error_response_keeps_request_id(monkeypatch):
    main_module = importlib.import_module("app.main")

    def explode():
        raise RuntimeError("private failure details")

    monkeypatch.setattr(main_module, "readiness", explode)
    failing_client = TestClient(app, raise_server_exceptions=False)

    response = failing_client.get(
        "/api/health/ready",
        headers={"X-Request-ID": "exception-path-123"},
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "exception-path-123"
    assert response.json() == {"detail": "internal_server_error"}
    assert "private failure details" not in response.text
