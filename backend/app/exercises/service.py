"""Deterministic scoring for reviewed answers; never execute submitted code."""

from __future__ import annotations

import re

from app.exercises.model import GradeResult


def _normalized(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value).strip())
    if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] in {'"', "'"}:
        text = text[1:-1]
    return text


def grade_attempt(item: dict, answers: dict[str, object], reference: dict | None = None) -> GradeResult:
    reference = reference or {}
    kind = item.get("kind")
    score: int | None = None
    status = "recorded"
    feedback: dict[str, object] = {"message": "已保存作答，请对照参考答案自行检查。"}
    if kind == "single_choice" and reference.get("choice"):
        labels = list((item.get("options") or {}).keys())
        raw = answers.get("choice")
        selected = labels[raw] if isinstance(raw, int) and 0 <= raw < len(labels) else str(raw or "").upper()
        score = 100 if selected == reference["choice"] else 0
        status = "graded"
        feedback = {"correct": score == 100, "message": "回答正确" if score == 100 else "回答不正确"}
    elif kind == "blank_fill" and item.get("answer_mode") == "normalized_blank_match":
        expected = reference.get("blanks") or {}
        keys = [blank["id"] for blank in item.get("blanks") or []]
        if keys and all(key in expected for key in keys):
            matches = {key: _normalized(answers.get(key, "")) == _normalized(expected[key]) for key in keys}
            score = round(100 * sum(matches.values()) / len(keys))
            status = "graded" if all(matches.values()) else "partially_graded"
            feedback = {"correct_blanks": [key for key, correct in matches.items() if correct], "total_blanks": len(keys)}
    payload: dict[str, object] = {"status": status, "score": score, "feedback": feedback}
    return GradeResult(status, score, feedback, payload)
