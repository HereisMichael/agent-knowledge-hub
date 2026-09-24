"""Rollback published content from backups."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.config import settings
from app.db import store
from app.rag.ingest import ingest_knowledge
from app.content.publish import reload_retriever


def list_publish_logs(limit: int = 30) -> list[dict]:
    return store.list_publish_logs(limit)


def rollback_publish(log_id: str) -> dict:
    log = store.get_publish_log(log_id)
    backups = json.loads(log.get("backup_paths") or "[]")
    dests = json.loads(log.get("dest_paths") or "[]")

    restored = []
    for backup, dest in zip(backups, dests):
        dp = Path(dest)
        resolved = dp.resolve()
        allowed_roots = (settings.knowledge_dir.resolve(), (settings.content_dir / "published").resolve())
        if not any(resolved.is_relative_to(root) and resolved != root for root in allowed_roots):
            raise ValueError("rollback destination outside published roots")
        if backup:
            bp = Path(backup)
            if not bp.is_file():
                raise FileNotFoundError(bp)
            dp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bp, dp)
        elif dp.is_file():
            dp.unlink()
        restored.append(str(dp))

    ingest_knowledge(full=False)
    reload_retriever()
    item = store.get_content_item(log["item_id"])
    if item["item_type"] == "exercise" and not any(backups):
        for source in store.list_content_sources():
            if source.get("content_item_id") == item["id"] and source["status"] == "active":
                store.record_content_takedown(source["id"], None, "removed", "Exercise publish rolled back")
        store.update_content_item(item["id"], status="changes_requested")
    store.add_changelog("rollback", log.get("item_id", ""), f"回滚 {len(restored)} 个文件")
    store.mark_publish_log_rolled_back(log_id)
    return {"log_id": log_id, "restored": restored}
