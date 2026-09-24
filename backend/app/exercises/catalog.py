"""Read only reviewed, published exercise artifacts."""

from __future__ import annotations

import json

from app.config import settings


PUBLIC_FIELDS = frozenset({
    "id", "set_id", "title", "kind", "level", "topics", "prompt_markdown",
    "options", "blanks", "answer_mode", "validation_status", "source_anchor",
    "estimated_minutes", "starter_code",
})


def _public_item(item: dict) -> dict:
    return {key: value for key, value in item.items() if key in PUBLIC_FIELDS}


def load_items() -> list[dict]:
    path = settings.knowledge_dir / "llm101" / "exercises" / "items.jsonl"
    if not path.is_file():
        return []
    return [_public_item(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def list_exercises(*, level: int | None = None, topic: str | None = None, kind: str | None = None) -> list[dict]:
    items = load_items()
    if level is not None:
        items = [item for item in items if item.get("level") == level]
    if topic:
        needle = topic.casefold()
        items = [item for item in items if any(needle == str(value).casefold() for value in item.get("topics", []))]
    if kind:
        items = [item for item in items if item.get("kind") == kind]
    return items


def get_exercise(exercise_id: str) -> dict | None:
    return next((item for item in load_items() if item.get("id") == exercise_id), None)


def load_answer(exercise_id: str) -> dict | None:
    path = settings.content_dir / "published" / "llm101" / "answers.jsonl"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            answer = json.loads(line)
            if answer.get("id") == exercise_id:
                return answer
    return None
