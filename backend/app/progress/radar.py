"""Progress radar dimensions for quiz and mock."""

from __future__ import annotations

from collections import defaultdict

from app.db import store
from app.interview.questions import load_questions

CATEGORIES = ["architecture", "product", "behavior", "solution", "agent"]
MOCK_DIMS = ["structure", "depth", "tradeoff", "compliance", "communication"]


def build_radar(user_id: str = "default") -> dict:
    questions = load_questions()
    bank_by_cat: dict[str, int] = defaultdict(int)
    for q in questions:
        bank_by_cat[q.get("category", "other")] += 1

    attempts = store.quiz_attempts_by_category(user_id)
    quiz_axes = []
    for cat in CATEGORIES:
        total = bank_by_cat.get(cat, 0)
        tried = attempts.get(cat, 0)
        pct = round(100 * tried / total, 1) if total else 0
        quiz_axes.append({"axis": cat, "value": pct, "detail": f"{tried}/{total}"})

    mock_scores = store.mock_avg_scores(user_id)
    mock_axes = []
    for dim in MOCK_DIMS:
        mock_axes.append({"axis": dim, "value": round(mock_scores.get(dim, 0), 1)})

    return {
        "quiz": {"axes": quiz_axes, "max": 100},
        "mock": {"axes": mock_axes, "max": 100},
    }
