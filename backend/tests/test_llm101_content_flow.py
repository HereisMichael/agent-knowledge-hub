"""Exercise packages must stay private until source rights are reviewed."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.config import settings
from app.content.audit import audit_exercise_package
from app.content.publish import publish_item
from app.content.rollback import rollback_publish
from app.content.daily_update import register_llm101_package
from app.db import store
from app.rag.knowledge_lookup import list_source_ids


def _package(root: Path, *, approved: bool) -> Path:
    root.mkdir(parents=True)
    source = b"# Example source\n"
    digest = hashlib.sha256(source).hexdigest()
    (root / "catalog.json").write_text(
        json.dumps({"schema_version": 1, "source": "llm101", "sets": [{"id": "llm101-demo", "title": "Demo", "topics": ["test"], "item_ids": ["llm101-demo-01"], "source_path": "docs/exercises/demo.md"}]}),
        encoding="utf-8",
    )
    (root / "items.jsonl").write_text(
        json.dumps({"id": "llm101-demo-01", "set_id": "llm101-demo", "title": "Demo question", "topics": ["test"], "kind": "single_choice", "prompt_markdown": "## Demo\nQuestion?\n**A.** Yes\n**B.** No", "options": {"A": "Yes", "B": "No"}, "source_anchor": {"path": "docs/exercises/demo.md", "line": 1, "heading": "Demo"}}) + "\n",
        encoding="utf-8",
    )
    (root / "answers.jsonl").write_text(
        json.dumps({"id": "llm101-demo-01", "choice": "A", "reference_markdown": "**正确答案：A**"}) + "\n",
        encoding="utf-8",
    )
    (root / "warnings.jsonl").write_text("", encoding="utf-8")
    (root / "source-manifest.json").write_text(
        json.dumps({"schema_version": 1, "source": "llm101", "source_url": "https://github.com/boots-coder/LLM-101-CN", "commit": "a" * 40, "rights_status": "unverified", "files": [{"path": "docs/exercises/demo.md", "sha256": digest}]}),
        encoding="utf-8",
    )
    if approved:
        (root / "rights-approval.json").write_text(
            json.dumps({"source_commit": "a" * 40, "rights_note": "Owner confirmed permission to republish this learning material.", "reviewed_by": "admin@example.com"}),
            encoding="utf-8",
        )
    return root


def test_llm101_without_license_stays_blocked(tmp_path: Path) -> None:
    staging = _package(tmp_path / "llm101", approved=False)
    result = audit_exercise_package(staging)
    assert result["passed"] is False
    assert any(check["name"] == "rights" and check["status"] == "fail" for check in result["checks"])


def test_reviewed_package_passes_audit(tmp_path: Path) -> None:
    staging = _package(tmp_path / "llm101", approved=True)
    result = audit_exercise_package(staging)
    assert result["passed"] is True


def test_audit_rejects_path_like_set_id(tmp_path: Path) -> None:
    staging = _package(tmp_path / "llm101", approved=True)
    catalog = json.loads((staging / "catalog.json").read_text(encoding="utf-8"))
    catalog["sets"][0]["id"] = "../../private"
    (staging / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    result = audit_exercise_package(staging)
    assert result["passed"] is False


def test_audit_rejects_vitepress_hint_in_public_prompt(tmp_path: Path) -> None:
    staging = _package(tmp_path / "llm101", approved=True)
    path = staging / "items.jsonl"
    item = json.loads(path.read_text(encoding="utf-8"))
    item["prompt_markdown"] += "\n::: details 提示\n答案\n:::"
    path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
    result = audit_exercise_package(staging)
    assert result["passed"] is False
    assert any(check["name"] == "items" and check["status"] == "fail" for check in result["checks"])


def test_audit_rejects_reference_section_in_public_prompt(tmp_path: Path) -> None:
    staging = _package(tmp_path / "llm101", approved=True)
    path = staging / "items.jsonl"
    item = json.loads(path.read_text(encoding="utf-8"))
    item["prompt_markdown"] += "\n## 参考实现\n答案不应公开"
    path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")

    result = audit_exercise_package(staging)
    assert result["passed"] is False
    assert any(check["name"] == "items" and check["status"] == "fail" for check in result["checks"])


def test_unreviewed_package_cannot_be_published(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content_root = tmp_path / "content"
    staging = _package(content_root / "staging" / "llm101", approved=False)
    monkeypatch.setattr(settings, "content_root", str(content_root))
    monkeypatch.setattr(settings, "knowledge_path", str(tmp_path / "knowledge"))
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    monkeypatch.setattr(settings, "privacy_ledger_path", str(tmp_path / "privacy.db"))
    store.init_db()
    item = store.create_content_item("exercise", str(staging / "catalog.json"), "LLM101")
    with pytest.raises(ValueError, match="rights|audit"):
        publish_item(item)
    assert not (tmp_path / "knowledge" / "llm101").exists()


def test_reviewed_package_publishes_private_answers_and_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content_root = tmp_path / "content"
    staging = _package(content_root / "staging" / "llm101", approved=True)
    knowledge = tmp_path / "knowledge"
    monkeypatch.setattr(settings, "content_root", str(content_root))
    monkeypatch.setattr(settings, "knowledge_path", str(knowledge))
    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    monkeypatch.setattr(settings, "privacy_ledger_path", str(tmp_path / "privacy.db"))
    store.init_db()
    item = store.create_content_item("exercise", str(staging / "catalog.json"), "LLM101")

    publish_item(item)

    public = knowledge / "llm101" / "exercises"
    assert (public / "catalog.json").is_file()
    assert (public / "items.jsonl").is_file()
    assert "正确答案" not in (public / "items.jsonl").read_text(encoding="utf-8")
    assert (content_root / "published" / "llm101" / "answers.jsonl").is_file()
    assert "llm101-demo" in list_source_ids("llm101")
    assert store.list_content_sources()[0]["rights_note"].startswith("Owner confirmed")

    log = store.list_publish_logs()[0]
    rollback_publish(log["id"])
    assert not (public / "catalog.json").exists()
    assert not (public / "items.jsonl").exists()
    assert not (content_root / "published" / "llm101" / "answers.jsonl").exists()
    assert store.list_content_sources()[0]["status"] == "removed"


def test_staging_scan_registers_one_review_item_per_source_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staging = _package(tmp_path / "content" / "staging" / "llm101", approved=False)
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    monkeypatch.setattr(settings, "privacy_ledger_path", str(tmp_path / "privacy.db"))
    store.init_db()

    first = register_llm101_package(staging)
    second = register_llm101_package(staging)

    assert first is not None
    assert first["item_type"] == "exercise"
    assert first["status"] == "pending_audit"
    assert first["audit_checks"]["passed"] is False
    assert second is None
    assert len(store.list_content_items()) == 1


def test_failed_exercise_publish_removes_partial_public_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content_root = tmp_path / "content"
    staging = _package(content_root / "staging" / "llm101", approved=True)
    knowledge = tmp_path / "knowledge"
    monkeypatch.setattr(settings, "content_root", str(content_root))
    monkeypatch.setattr(settings, "knowledge_path", str(knowledge))
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "hub.db"))
    monkeypatch.setattr(settings, "privacy_ledger_path", str(tmp_path / "privacy.db"))
    store.init_db()
    item = store.create_content_item("exercise", str(staging / "catalog.json"), "LLM101")
    original_copy = shutil.copy2

    def interrupted_copy(source, destination, *args, **kwargs):
        if Path(source).name == "answers.jsonl":
            raise OSError("simulated disk interruption")
        return original_copy(source, destination, *args, **kwargs)

    monkeypatch.setattr("app.content.publish.shutil.copy2", interrupted_copy)
    with pytest.raises(OSError, match="disk interruption"):
        publish_item(item)
    assert not (knowledge / "llm101" / "exercises" / "catalog.json").exists()
    assert not (knowledge / "llm101" / "exercises" / "items.jsonl").exists()
    assert store.list_publish_logs() == []
