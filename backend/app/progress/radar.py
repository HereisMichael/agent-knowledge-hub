"""Progress radar dimensions for quiz and mock."""

from __future__ import annotations

from collections import defaultdict

from app.db import store
from app.exercises.catalog import load_items
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


def build_exercise_progress(user_id: str) -> dict[str, object]:
    """Keep model-engineering attempts distinct from interview radar scores."""
    items = {item["id"]: item for item in load_items()}
    rows = store.exercise_attempt_summary_rows(user_id)
    by_topic: dict[str, dict] = {}
    by_level: dict[str, dict] = {}
    scored: list[int] = []
    recorded_challenges = 0

    def add(group: dict[str, dict], key: str, score: int | None) -> None:
        bucket = group.setdefault(key, {"attempts": 0, "graded_average": None, "_scores": []})
        bucket["attempts"] += 1
        if score is not None:
            bucket["_scores"].append(score)

    for row in rows:
        item = items.get(row["exercise_id"])
        if item is None:
            continue
        score = row["score"]
        if score is not None:
            scored.append(score)
        if item.get("kind") == "implementation_challenge" and score is None:
            recorded_challenges += 1
        add(by_level, str(item.get("level", "unknown")), score)
        for topic in dict.fromkeys(item.get("topics", [])):
            add(by_topic, str(topic), score)

    for group in (by_topic, by_level):
        for bucket in group.values():
            scores = bucket.pop("_scores")
            bucket["graded_average"] = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "by_topic": by_topic,
        "by_level": by_level,
        "attempts": len(rows),
        "graded_average": round(sum(scored) / len(scored), 1) if scored else None,
        "recorded_challenges": recorded_challenges,
    }
