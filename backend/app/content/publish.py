"""Publish approved staging content to knowledge base."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

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


def publish_item(item: dict) -> None:
    source = Path(item["source_path"])
    if not source.exists():
        raise FileNotFoundError(source)

    dest_paths: list[str] = []
    backup_paths: list[str] = []

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
