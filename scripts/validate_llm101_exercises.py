"""Validate a review-only LLM-101-CN exercise import package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_package(package_dir: Path) -> dict[str, object]:
    catalog = json.loads((package_dir / "catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((package_dir / "source-manifest.json").read_text(encoding="utf-8"))
    items = _jsonl(package_dir / "items.jsonl")
    answers = _jsonl(package_dir / "answers.jsonl")
    warnings = _jsonl(package_dir / "warnings.jsonl")
    errors: list[str] = []
    ids = [item.get("id") for item in items]
    if len(ids) != len(set(ids)):
        errors.append("duplicate item IDs")
    answer_ids = {answer.get("id") for answer in answers}
    if set(ids) != answer_ids:
        errors.append("item/answer ID mismatch")
    paths = {entry["path"] for entry in manifest["files"]}
    for item in items:
        if not item.get("title") or not item.get("topics") or not item.get("prompt_markdown"):
            errors.append(f"incomplete public item: {item.get('id')}")
        prompt = item.get("prompt_markdown", "")
        if (
            "reference_markdown" in item
            or "<details" in prompt.lower()
            or re.search(r"(?m)^\s*:::\s*details(?:\s|$)", prompt, re.IGNORECASE)
            or re.search(r"(?m)^##\s+(?:参考实现|MLM 代码训练模式)(?:\s|$)", prompt)
        ):
            errors.append(f"answer leaked into public item: {item.get('id')}")
        if item.get("source_anchor", {}).get("path") not in paths:
            errors.append(f"source anchor has no manifest file: {item.get('id')}")
    set_ids = {entry["id"] for entry in catalog["sets"]}
    if len(set_ids) != len(catalog["sets"]):
        errors.append("duplicate set IDs")
    if any(item.get("set_id") not in set_ids for item in items):
        errors.append("orphan item")
    approval_path = package_dir / "rights-approval.json"
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8")) if approval_path.is_file() else {}
    except (OSError, ValueError):
        approval = {}
    rights_verified = (
        approval.get("source_commit") == manifest.get("commit")
        and len(str(approval.get("rights_note") or "").strip()) >= 20
        and bool(str(approval.get("reviewed_by") or "").strip())
    )
    return {
        "valid": not errors,
        "publishable": not errors and rights_verified,
        "rights_verified": rights_verified,
        "sets": len(catalog["sets"]),
        "items": len(items),
        "warnings": warnings,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path)
    args = parser.parse_args()
    report = validate_package(args.package_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
