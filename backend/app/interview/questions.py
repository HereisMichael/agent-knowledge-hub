"""Load and query interview question bank."""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.config import settings

_questions_cache: list[dict] | None = None


def questions_path() -> Path:
    return settings.knowledge_dir / "interview" / "questions.jsonl"


def load_questions(reload: bool = False) -> list[dict]:
    global _questions_cache
    if _questions_cache is not None and not reload:
        return _questions_cache
    path = questions_path()
    if not path.exists():
        _questions_cache = []
        return _questions_cache
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    _questions_cache = items
    return items


def get_question(question_id: str) -> dict | None:
    for q in load_questions():
        if q["id"] == question_id:
            return q
    return None


def pick_question(
    vendor: str | None = None,
    category: str | None = None,
    difficulty: int | None = None,
    exclude_ids: list[str] | None = None,
) -> dict | None:
    pool = load_questions()
    exclude = set(exclude_ids or [])
    filtered = []
    for q in pool:
        if q["id"] in exclude:
            continue
        if vendor and q.get("vendor") != vendor:
            continue
        if category and q.get("category") != category:
            continue
        if difficulty is not None and q.get("difficulty") != difficulty:
            continue
        filtered.append(q)
    if not filtered:
        return None
    return random.choice(filtered)


def questions_by_vendor() -> dict[str, int]:
    counts: dict[str, int] = {}
    for q in load_questions():
        v = q.get("vendor", "unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts
