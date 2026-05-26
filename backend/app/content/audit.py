"""Automatic content quality checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import settings
from app.llm.client import chat_json

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", re.I),
]
REQUIRED_QUESTION_FIELDS = ["id", "vendor", "category", "question", "key_points", "source_note"]


def audit_markdown(path: Path, published_root: Path | None = None) -> dict:
    checks: list[dict] = []
    text = path.read_text(encoding="utf-8")
    body = text
    meta: dict = {}

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml

            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2]

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    if not meta.get("source_id"):
        add("front_matter", "fail", "缺少 source_id")
    else:
        add("front_matter", "pass")

    blen = len(body.strip())
    if blen < 300:
        add("length", "fail", f"正文过短 ({blen} 字)")
    elif blen > 8000:
        add("length", "warn", f"正文较长 ({blen} 字)")
    else:
        add("length", "pass")

    for pat in SECRET_PATTERNS:
        if pat.search(text):
            add("security", "fail", "疑似包含密钥")
            break
    else:
        add("security", "pass")

    if "## 参考来源" not in body:
        add("references", "fail", "缺少 ## 参考来源")
    else:
        add("references", "pass")

    fail_count = sum(1 for c in checks if c["status"] == "fail")
    return {
        "checks": checks,
        "passed": fail_count == 0,
        "fail_count": fail_count,
        "warn_count": sum(1 for c in checks if c["status"] == "warn"),
    }


def audit_question(item: dict, existing_ids: set[str]) -> dict:
    checks: list[dict] = []

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    for f in REQUIRED_QUESTION_FIELDS:
        if not item.get(f):
            add(f"field_{f}", "fail", f"缺少 {f}")
    if item.get("id") in existing_ids:
        add("duplicate_id", "warn", "ID 已存在（可能是修订）")
    if not item.get("key_points"):
        add("key_points", "fail", "key_points 为空")
    else:
        add("structure", "pass")

    fail_count = sum(1 for c in checks if c["status"] == "fail")
    return {"checks": checks, "passed": fail_count == 0, "fail_count": fail_count}


def ai_audit_report(item_type: str, content_preview: str, checks: dict) -> dict:
    if settings.use_demo_llm:
        score = 80 if checks.get("passed") else 55
        return {
            "quality_score": score,
            "accuracy": "demo",
            "completeness": "demo",
            "recommendation": "approve" if score >= 70 else "reject",
            "summary": "Demo 模式：仅基于自动规则估算分数。",
        }
    system = (
        "你是技术文档质检员。根据自动检查结果与内容摘要输出 JSON："
        "quality_score(0-100), accuracy, completeness, teachability, compliance, "
        "recommendation(approve|review|reject), summary"
    )
    user = f"类型：{item_type}\n自动检查：{json.dumps(checks, ensure_ascii=False)}\n内容摘要：{content_preview[:2000]}"
    return chat_json(system, user)
