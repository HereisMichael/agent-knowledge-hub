"""Publish approved staging content to knowledge base."""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from app.config import settings
from app.db import store
from app.rag.ingest import ingest_knowledge
from app.rag.retriever import HybridRetriever

_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def reload_retriever() -> None:
    global _retriever
    _retriever = HybridRetriever()


def staging_dir() -> Path:
    return settings.content_dir / "staging"


def _backup_dir() -> Path:
    d = settings.content_dir / "published" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _backup_file(dest: Path, item_id: str) -> str | None:
    if not dest.exists():
        return None
    backup = _backup_dir() / f"{item_id}-{dest.name}"
    shutil.copy2(dest, backup)
    return str(backup.resolve())


def _publish_exercise_package(
    item: dict, source: Path, dest_paths: list[str], backup_paths: list[str]
) -> None:
    package = source.parent
    catalog = json.loads(source.read_text(encoding="utf-8"))
    manifest = json.loads((package / "source-manifest.json").read_text(encoding="utf-8"))
    items = [json.loads(line) for line in (package / "items.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_set: dict[str, list[dict]] = {}
    for exercise in items:
        by_set.setdefault(exercise["set_id"], []).append(exercise)

    copies = (
        (package / "catalog.json", settings.knowledge_dir / "llm101" / "exercises" / "catalog.json"),
        (package / "items.jsonl", settings.knowledge_dir / "llm101" / "exercises" / "items.jsonl"),
        (package / "answers.jsonl", settings.content_dir / "published" / "llm101" / "answers.jsonl"),
    )
    for origin, dest in copies:
        dest.parent.mkdir(parents=True, exist_ok=True)
        backup_paths.append(_backup_file(dest, item["id"]) or "")
        dest_paths.append(str(dest.resolve()))
        shutil.copy2(origin, dest)

    for exercise_set in catalog["sets"]:
        set_id = exercise_set["id"]
        source_path = exercise_set["source_path"]
        source_link = f"{manifest['source_url']}/blob/{manifest['commit']}/{source_path}"
        header = yaml.safe_dump({
            "source_id": set_id,
            "corpus": "llm101",
            "type": "exercise",
            "topic": exercise_set["topics"][0],
            "source_commit": manifest["commit"],
        }, allow_unicode=True, sort_keys=False).strip()
        body = "\n\n".join(exercise["prompt_markdown"] for exercise in by_set.get(set_id, []))
        text = f"---\n{header}\n---\n\n# {exercise_set['title']}\n\n{body}\n\n## 参考来源\n\n[{source_path}]({source_link})\n"
        dest = settings.knowledge_dir / "llm101" / "pages" / f"{set_id}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        backup_paths.append(_backup_file(dest, item["id"]) or "")
        dest_paths.append(str(dest.resolve()))
        dest.write_text(text, encoding="utf-8")



def _restore_exercise_files(dest_paths: list[str], backup_paths: list[str]) -> None:
    for destination, backup in reversed(list(zip(dest_paths, backup_paths))):
        dest = Path(destination)
        if backup:
            shutil.copy2(backup, dest)
        elif dest.is_file():
            dest.unlink()


def publish_item(item: dict) -> None:
    source = Path(item["source_path"])
    if not source.exists():
        raise FileNotFoundError(source)
    if item["item_type"] == "exercise":
        from app.content.audit import audit_exercise_package

        if source.name != "catalog.json" or source.resolve().parent != (staging_dir() / "llm101").resolve():
            raise ValueError("exercise package must come from LLM101 staging")
        if not audit_exercise_package(source.parent)["passed"]:
            raise ValueError("exercise audit or rights approval failed")

    dest_paths: list[str] = []
    backup_paths: list[str] = []

    if item["item_type"] == "exercise":
        try:
            _publish_exercise_package(item, source, dest_paths, backup_paths)
            ingest_knowledge(full=False)
            reload_retriever()
            manifest = json.loads((source.parent / "source-manifest.json").read_text(encoding="utf-8"))
            approval = json.loads((source.parent / "rights-approval.json").read_text(encoding="utf-8"))
            if not any(row.get("content_item_id") == item["id"] for row in store.list_content_sources()):
                store.create_content_source(
                    source_path="docs/exercises",
                    source_url=manifest["source_url"],
                    source_title="LLM-101-CN exercises",
                    publisher="boots-coder",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    rights_note=approval["rights_note"],
                    content_item_id=item["id"],
                )
            store.create_publish_log(item["id"], dest_paths, backup_paths)
            store.update_content_item(item["id"], status="approved")
            store.add_changelog("published", item["id"], item.get("title") or "LLM101 exercises")
        except Exception:
            _restore_exercise_files(dest_paths, backup_paths)
            raise
        return

    if item["item_type"] == "markdown":
        rel = source.relative_to(staging_dir()) if staging_dir() in source.parents else source.name
        dest = settings.knowledge_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        bk = _backup_file(dest, item["id"])
        shutil.copy2(source, dest)
        dest_paths.append(str(dest.resolve()))
        backup_paths.append(bk or "")
        store.add_changelog("published", item["id"], item.get("title") or dest.name)
    elif item["item_type"] == "question":
        q = json.loads(source.read_text(encoding="utf-8"))
        bank = settings.knowledge_dir / "interview" / "questions.jsonl"
        bank.parent.mkdir(parents=True, exist_ok=True)
        bk = _backup_file(bank, item["id"])
        existing = []
        if bank.exists():
            for line in bank.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing.append(json.loads(line))
        existing = [x for x in existing if x.get("id") != q["id"]]
        existing.append(q)
        bank.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in existing) + "\n",
            encoding="utf-8",
        )
        dest_paths.append(str(bank.resolve()))
        backup_paths.append(bk or "")
        store.add_changelog("published", item["id"], q.get("id", "question"))

    snapshot = settings.content_dir / "published" / date.today().isoformat()
    snapshot.mkdir(parents=True, exist_ok=True)
    if source.exists():
        snap_dest = snapshot / source.name
        shutil.copy2(source, snap_dest)

    store.create_publish_log(item["id"], dest_paths, backup_paths)
    store.update_content_item(item["id"], status="approved")
    ingest_knowledge(full=False)
    reload_retriever()


def reject_item(item_id: str, note: str) -> dict:
    return store.update_content_item(
        item_id, status="changes_requested", reviewer_note=note
    )
