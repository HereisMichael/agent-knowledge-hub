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
        bp = Path(backup)
        dp = Path(dest)
        if not bp.exists():
            continue
        dp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bp, dp)
        restored.append(str(dp))

    ingest_knowledge(full=False)
    reload_retriever()
    store.add_changelog("rollback", log.get("item_id", ""), f"回滚 {len(restored)} 个文件")
    store.mark_publish_log_rolled_back(log_id)
    return {"log_id": log_id, "restored": restored}
