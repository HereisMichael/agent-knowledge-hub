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
LLM101_SOURCE_URL = "https://github.com/boots-coder/LLM-101-CN"
PROMPT_INJECTION_PATTERN = re.compile(
    r"ignore (?:all )?(?:previous|prior) instructions|忽略(?:以上|之前)(?:所有)?指令",
    re.IGNORECASE,
)
REQUIRED_QUESTION_FIELDS = ["id", "vendor", "category", "question", "key_points", "source_note"]


def audit_exercise_package(staging_dir: Path) -> dict[str, object]:
    """Audit an imported package; source rights require a separate review note."""
    checks: list[dict[str, str]] = []

    def add(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    try:
        catalog = json.loads((staging_dir / "catalog.json").read_text(encoding="utf-8"))
        manifest = json.loads((staging_dir / "source-manifest.json").read_text(encoding="utf-8"))
        items = [json.loads(line) for line in (staging_dir / "items.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        answers = [json.loads(line) for line in (staging_dir / "answers.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError, TypeError) as exc:
        add("package", "fail", f"invalid package: {exc}")
        return {"checks": checks, "passed": False, "fail_count": 1, "warn_count": 0}

    if catalog.get("schema_version") == 1 and manifest.get("schema_version") == 1:
        add("schema", "pass")
    else:
        add("schema", "fail", "unsupported schema_version")
    commit = str(manifest.get("commit") or "")
    files = manifest.get("files") or []
    valid_files = bool(files) and all(
        isinstance(entry, dict)
        and re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256") or ""))
        and str(entry.get("path") or "").startswith("docs/exercises/")
        for entry in files
    )
    if (manifest.get("source_url") == LLM101_SOURCE_URL
            and re.fullmatch(r"[0-9a-f]{40}", commit) and valid_files):
        add("source", "pass")
    else:
        add("source", "fail", "source URL, commit or SHA-256 manifest invalid")

    item_ids = [item.get("id") for item in items]
    answer_ids = [answer.get("id") for answer in answers]
    if (items and len(item_ids) == len(set(item_ids)) and set(item_ids) == set(answer_ids)
            and all(item.get("prompt_markdown") and item.get("title") and item.get("topics") for item in items)
            and all(
                "reference_markdown" not in item
                and "<details" not in item.get("prompt_markdown", "").lower()
                and not re.search(r"(?m)^\s*:::\s*details(?:\s|$)", item.get("prompt_markdown", ""), re.IGNORECASE)
                and not re.search(r"(?m)^##\s+(?:参考实现|MLM 代码训练模式)(?:\s|$)", item.get("prompt_markdown", ""))
                for item in items
            )):
        add("items", "pass")
    else:
        add("items", "fail", "empty/duplicate items, answer mismatch, or answer leak")
    sets = catalog.get("sets") or []
    set_ids = [entry.get("id") for entry in sets]
    valid_sets = bool(sets) and len(set_ids) == len(set(set_ids)) and all(
        re.fullmatch(r"llm101-[a-z0-9-]+", str(entry.get("id") or ""))
        and entry.get("title") and entry.get("topics")
        and re.fullmatch(r"docs/exercises/[a-z0-9-]+\.md", str(entry.get("source_path") or ""))
        for entry in sets
    )
    if valid_sets and all(item.get("set_id") in set_ids for item in items):
        add("sets", "pass")
    else:
        add("sets", "fail", "invalid set ID, source path or item relation")

    approval_path = staging_dir / "rights-approval.json"
    approval: dict = {}
    if approval_path.is_file():
        try:
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    if (approval.get("source_commit") == commit
            and len(str(approval.get("rights_note") or "").strip()) >= 20
            and str(approval.get("reviewed_by") or "").strip()):
        add("rights", "pass")
    else:
        add("rights", "fail", "manual rights approval for this exact commit required")

    prompts = "\n".join(str(item.get("prompt_markdown") or "") for item in items)
    if any(pattern.search(prompts) for pattern in SECRET_PATTERNS):
        add("security", "fail", "possible secret in prompt")
    else:
        add("security", "pass")
    if PROMPT_INJECTION_PATTERN.search(prompts):
        add("prompt_injection", "warn", "instruction-like source text requires review")
    else:
        add("prompt_injection", "pass")
    fail_count = sum(check["status"] == "fail" for check in checks)
    return {
        "checks": checks,
        "passed": fail_count == 0,
        "fail_count": fail_count,
        "warn_count": sum(check["status"] == "warn" for check in checks),
    }


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
