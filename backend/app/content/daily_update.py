"""Daily content update: scan staging seeds and register pending items."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.config import settings
from app.content.audit import ai_audit_report, audit_markdown, audit_question
from app.content.extra_diff import scan_extra_dirs
from app.content.publish import publish_item
from app.db import store


def _maybe_auto_publish(item: dict, score: float, checks: dict) -> bool:
    if not settings.auto_publish_trusted:
        return False
    if score < settings.auto_publish_min_score:
        return False
    if checks.get("fail_count", 1) > 0:
        return False
    try:
        publish_item(item)
        return True
    except Exception as e:
        print(f"[warn] auto-publish failed for {item['id']}: {e}")
        return False


def run_daily_update() -> dict:
    run = store.create_content_run("daily_update", "running", "每日更新开始")
    created = 0
    auto_published = 0
    staging = settings.content_dir / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    extra_result = scan_extra_dirs()

    for sub in ("tech", "interview"):
        folder = staging / sub
        folder.mkdir(parents=True, exist_ok=True)
        for md in folder.glob("*.md"):
            title = md.stem
            checks = audit_markdown(md)
            item = store.create_content_item("markdown", str(md.resolve()), title)
            report = ai_audit_report("markdown", md.read_text(encoding="utf-8")[:3000], checks)
            score = float(report.get("quality_score", 0))
            store.update_content_item(
                item["id"],
                audit_checks=checks,
                audit_report=report,
                quality_score=score,
                status="pending_audit",
            )
            created += 1
            if _maybe_auto_publish(store.get_content_item(item["id"]), score, checks):
                auto_published += 1

    patch = staging / "questions.patch.jsonl"
    if patch.exists():
        existing_ids = set()
        bank = settings.knowledge_dir / "interview" / "questions.jsonl"
        if bank.exists():
            import json

            for line in bank.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing_ids.add(json.loads(line)["id"])
        import json

        for line in patch.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            q = json.loads(line)
            qpath = staging / f"question_{q['id']}.json"
            qpath.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
            checks = audit_question(q, existing_ids)
            item = store.create_content_item("question", str(qpath.resolve()), q["id"])
            report = ai_audit_report("question", json.dumps(q, ensure_ascii=False), checks)
            score = float(report.get("quality_score", 0))
            store.update_content_item(
                item["id"],
                audit_checks=checks,
                audit_report=report,
                quality_score=score,
            )
            created += 1
            if _maybe_auto_publish(store.get_content_item(item["id"]), score, checks):
                auto_published += 1

    feeds = settings.content_dir / "feeds.yaml"
    if feeds.exists():
        _process_feeds(feeds)

    summary = (
        f"登记 {created} 条待审；extra：{extra_result.get('message', '')}；"
        f"自动发布 {auto_published} 条"
    )
    store.finish_content_run(run["id"], "completed", summary, created)
    return {
        "run_id": run["id"],
        "items_created": created,
        "auto_published": auto_published,
        "extra_diff": extra_result,
        "summary": summary,
    }


def _process_feeds(feeds_path: Path) -> None:
    data = yaml.safe_load(feeds_path.read_text(encoding="utf-8")) or {}
    for feed in data.get("feeds", []):
        if feed.get("type") != "local_seed":
            continue
        seed_dir = Path(feed.get("path", ""))
        if not seed_dir.is_absolute():
            seed_dir = settings.content_dir / seed_dir
        if not seed_dir.exists():
            continue
        staging = settings.content_dir / "staging" / feed.get("target", "tech")
        staging.mkdir(parents=True, exist_ok=True)
        for md in seed_dir.glob("*.md"):
            dest = staging / md.name
            if not dest.exists() or md.stat().st_mtime > dest.stat().st_mtime:
                dest.write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
