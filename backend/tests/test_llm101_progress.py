"""LLM101 progress is independent of interview scores and gated by publication."""

from __future__ import annotations

import json

from app.config import settings
from app.db import store
from app.labs.recommend import load_manifest, recommend_labs
from app.progress.radar import build_exercise_progress


def _published_items(tmp_path, monkeypatch, items: list[dict]) -> None:
    monkeypatch.setattr(settings, "knowledge_path", str(tmp_path / "knowledge"))
    path = settings.knowledge_dir / "llm101" / "exercises" / "items.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n", encoding="utf-8")


def _user(tmp_path, monkeypatch) -> str:
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    store.init_db()
    return store.create_user("progress@example.com", "hash")["id"]


def test_progress_groups_exercises_without_inventing_a_score(tmp_path, monkeypatch) -> None:
    _published_items(tmp_path, monkeypatch, [
        {"id": "llm101-rag-build-01", "kind": "implementation_challenge", "level": 4, "topics": ["RAG", "Agent"]},
        {"id": "llm101-rag-fill-01", "kind": "blank_fill", "level": 3, "topics": ["RAG"]},
    ])
    user_id = _user(tmp_path, monkeypatch)
    store.create_exercise_attempt(user_id, "llm101-rag-build-01", {"submission": "repo"}, "recorded", None, "")
    store.create_exercise_attempt(user_id, "llm101-rag-fill-01", {"blank-1": "x"}, "graded", 80, "")

    result = build_exercise_progress(user_id)

    assert result["attempts"] == 2
    assert result["recorded_challenges"] == 1
    assert result["graded_average"] == 80
    assert result["by_topic"]["RAG"]["attempts"] == 2
    assert result["by_level"]["4"]["attempts"] == 1
    assert result["by_level"]["4"]["graded_average"] is None


def test_llm101_labs_only_exist_after_publish_and_completed_lab_is_not_recommended(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "project_root", str(tmp_path))
    manifest = tmp_path / "labs" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps([
        {"id": "lab-existing", "title": "Existing", "effort_hours": 2, "weakness_tags": ["rag"], "steps": ["Build"]},
        {"id": "lab-llm101-rag-build", "title": "RAG build", "effort_hours": 4, "source_exercise_id": "llm101-rag-build-01", "weakness_tags": ["rag"], "steps": ["Build"]},
    ]), encoding="utf-8")
    _published_items(tmp_path, monkeypatch, [])
    user_id = _user(tmp_path, monkeypatch)
    assert [lab["id"] for lab in load_manifest()] == ["lab-existing"]

    _published_items(tmp_path, monkeypatch, [{"id": "llm101-rag-build-01", "kind": "implementation_challenge", "level": 4, "topics": ["RAG"]}])
    assert len(load_manifest()) == 2
    assert recommend_labs(weakness_tags=["rag"], user_id=user_id, limit=2)[0]["id"] in {"lab-existing", "lab-llm101-rag-build"}
    store.complete_lab(user_id, "lab-llm101-rag-build", "done")
    assert [lab["id"] for lab in recommend_labs(weakness_tags=["rag"], user_id=user_id, limit=2)] == ["lab-existing"]
