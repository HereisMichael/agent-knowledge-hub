"""Diff INGEST_EXTRA_DIRS against published knowledge → staging candidates."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from app.config import settings
from app.content.audit import ai_audit_report, audit_markdown
from app.db import store

_STATE_FILE = ".extra_diff_state.json"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_state(content_dir: Path) -> dict[str, str]:
    import json

    p = content_dir / _STATE_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(content_dir: Path, state: dict[str, str]) -> None:
    import json

    p = content_dir / _STATE_FILE
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel_key(extra_root: Path, path: Path) -> str:
    rel = path.relative_to(extra_root)
    return f"{extra_root.name}/{rel.as_posix()}"


def scan_extra_dirs() -> dict:
    """Copy new/changed files from extra knowledge dirs into staging for audit."""
    extra_dirs = settings.extra_knowledge_dirs
    if not extra_dirs:
        return {"scanned": 0, "staged": 0, "message": "INGEST_EXTRA_DIRS 未配置"}

    content_dir = settings.content_dir
    staging_tech = content_dir / "staging" / "tech"
    staging_tech.mkdir(parents=True, exist_ok=True)
    state = _load_state(content_dir)
    new_state = dict(state)
    staged = 0
    scanned = 0

    pending_paths = {
        Path(i["source_path"]).resolve()
        for i in store.list_content_items("pending_audit")
    }

    for extra_root in extra_dirs:
        if not extra_root.exists():
            continue
        for md in extra_root.rglob("*.md"):
            if md.name.startswith("."):
                continue
            scanned += 1
            key = _rel_key(extra_root, md)
            digest = _file_hash(md)
            if state.get(key) == digest:
                continue

            dest_name = f"extra-{extra_root.name}-{md.stem}.md"
            dest = staging_tech / dest_name
            shutil.copy2(md, dest)
            new_state[key] = digest
            staged += 1

            if dest.resolve() in pending_paths:
                continue

            checks = audit_markdown(dest)
            item = store.create_content_item(
                "markdown",
                str(dest.resolve()),
                title=f"[extra] {md.stem}",
            )
            preview = dest.read_text(encoding="utf-8")[:3000]
            report = ai_audit_report("markdown", preview, checks)
            score = float(report.get("quality_score", 0))
            store.update_content_item(
                item["id"],
                audit_checks=checks,
                audit_report=report,
                quality_score=score,
            )

    _save_state(content_dir, new_state)
    return {
        "scanned": scanned,
        "staged": staged,
        "message": f"extra diff：扫描 {scanned} 个文件，登记 {staged} 条变更",
    }
