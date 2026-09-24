"""Scoring never executes learner code or leaks hidden answers."""

from app.exercises.service import grade_attempt


def test_single_choice_grades_by_server_answer_without_leaking_it() -> None:
    item = {"id": "llm101-quiz-01", "kind": "single_choice", "options": {"A": "wrong", "B": "right"}}
    result = grade_attempt(item, {"choice": "B"}, {"choice": "B", "reference_markdown": "Secret explanation"})
    assert result.status == "graded"
    assert result.score == 100
    assert "reference_markdown" not in result.public_payload
    assert "Secret explanation" not in str(result.feedback)


def test_review_only_blank_does_not_claim_an_automatic_score() -> None:
    item = {"id": "llm101-fill-01", "kind": "blank_fill", "blanks": [{"id": "blank-1"}], "answer_mode": "manual_review"}
    result = grade_attempt(item, {"blank-1": "chunk_size - overlap"}, {"reference_markdown": "step = chunk_size - overlap"})
    assert result.status == "recorded"
    assert result.score is None
    assert "reference_markdown" not in result.public_payload


def test_structured_blank_answer_is_scored_when_reviewed_mapping_exists() -> None:
    item = {"id": "llm101-fill-02", "kind": "blank_fill", "blanks": [{"id": "blank-1"}], "answer_mode": "normalized_blank_match"}
    result = grade_attempt(item, {"blank-1": "  'hello'  "}, {"blanks": {"blank-1": '"hello"'}})
    assert result.status == "graded"
    assert result.score == 100


def test_implementation_challenge_is_recorded_without_running_code() -> None:
    item = {"id": "llm101-build-01", "kind": "implementation_challenge"}
    result = grade_attempt(item, {"submission": "while True: pass"}, {"reference_markdown": "Private solution"})
    assert result.status == "recorded"
    assert result.score is None
