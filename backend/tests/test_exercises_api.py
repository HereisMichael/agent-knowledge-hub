"""Authenticated exercise API keeps answers and attempts user-scoped."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings
from app.db import store
from app.main import app


def _configure(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    monkeypatch.setattr(settings, "privacy_ledger_path", str(tmp_path / "privacy.db"))
    monkeypatch.setattr(settings, "knowledge_path", str(tmp_path / "knowledge"))
    monkeypatch.setattr(settings, "content_root", str(tmp_path / "content"))
    monkeypatch.setattr(settings, "auth_invite_code", "llm101-test-invite")
    monkeypatch.setattr(settings, "app_env", "test")
    store.init_db()
    public = tmp_path / "knowledge" / "llm101" / "exercises"
    private = tmp_path / "content" / "published" / "llm101"
    public.mkdir(parents=True)
    private.mkdir(parents=True)
    (public / "catalog.json").write_text(json.dumps({
        "schema_version": 1, "source": "llm101",
        "sets": [{"id": "llm101-demo", "title": "Demo set", "topics": ["attention"], "item_ids": ["llm101-demo-01"], "source_path": "docs/exercises/demo.md"}],
    }), encoding="utf-8")
    (public / "items.jsonl").write_text(json.dumps({
        "id": "llm101-demo-01", "set_id": "llm101-demo", "title": "Question one",
        "kind": "single_choice", "level": 1, "topics": ["attention"],
        "prompt_markdown": "Question? **A.** Wrong **B.** Right", "options": {"A": "Wrong", "B": "Right"},
        "blanks": [], "answer_mode": "choice_exact", "source_anchor": {"path": "docs/exercises/demo.md", "line": 1},
    }) + "\n", encoding="utf-8")
    (private / "answers.jsonl").write_text(json.dumps({
        "id": "llm101-demo-01", "choice": "B", "reference_markdown": "SECRET EXPLANATION",
    }) + "\n", encoding="utf-8")


def _register(client: TestClient, email: str) -> str:
    response = client.post("/api/auth/register", json={
        "email": email, "password": "correct horse battery staple", "invite_code": "llm101-test-invite",
    })
    assert response.status_code == 201
    return response.json()["user"]["id"]


def test_public_views_and_attempts_do_not_leak_answers(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    learner = TestClient(app)
    other = TestClient(app)
    assert learner.get("/api/exercises").status_code == 401
    learner_id = _register(learner, "first@example.com")
    _register(other, "second@example.com")

    listing = learner.get("/api/exercises?level=1&topic=attention&kind=single_choice")
    detail = learner.get("/api/exercises/llm101-demo-01")
    assert listing.status_code == detail.status_code == 200
    assert len(listing.json()["items"]) == 1
    assert "SECRET EXPLANATION" not in listing.text + detail.text

    hidden = learner.post("/api/exercises/llm101-demo-01/attempts", json={
        "answers": {"choice": "B"}, "request_reveal": False,
    })
    assert hidden.status_code == 200
    assert hidden.json()["score"] == 100
    assert "reference_markdown" not in hidden.json()

    revealed = learner.post("/api/exercises/llm101-demo-01/attempts", json={
        "answers": {"choice": "A"}, "request_reveal": True,
    })
    assert revealed.status_code == 200
    assert revealed.json()["reference_markdown"] == "SECRET EXPLANATION"
    assert learner.get("/api/exercises/progress").json()["total_attempts"] == 2
    assert other.get("/api/exercises/progress").json()["total_attempts"] == 0
    exported = store.export_user_data(learner_id)
    assert len(exported["exercise_attempts"]) == 2


def test_attempt_rejects_unknown_answer_key(tmp_path: Path, monkeypatch) -> None:
    _configure(tmp_path, monkeypatch)
    learner = TestClient(app)
    _register(learner, "third@example.com")
    response = learner.post("/api/exercises/llm101-demo-01/attempts", json={
        "answers": {"reference_markdown": "forged"},
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "exercise_answer_invalid"
