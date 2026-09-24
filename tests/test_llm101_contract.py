"""Reproducible LLM101 import contract without publishing unlicensed source text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.exercises.service import grade_attempt
from scripts.import_llm101_exercises import import_source
from scripts.validate_llm101_exercises import validate_package


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "LLM-101-CN"
CASES = ROOT / "eval" / "llm101_exercises.jsonl"


@pytest.fixture()
def package(tmp_path: Path):
    if not SOURCE.is_dir():
        pytest.skip("separate LLM-101-CN checkout unavailable")
    return import_source(SOURCE, tmp_path)


def test_public_import_shape_privacy_and_release_gate(package, tmp_path: Path) -> None:
    report = validate_package(tmp_path)
    assert report["valid"] is True
    assert report["publishable"] is False  # No authoritative source license in this checkout.
    assert len(package.catalog["sets"]) == 25
    assert len(package.items) >= 100
    assert len({item["id"] for item in package.items}) == len(package.items)
    assert all("reference_markdown" not in item and "::: details" not in item["prompt_markdown"] for item in package.items)


def test_evaluation_cases_cover_scoring_and_manual_review(package, tmp_path: Path) -> None:
    fixtures = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(fixtures) >= 6
    items = {item["id"]: item for item in package.items}
    answers = {answer["id"]: answer for answer in (json.loads(line) for line in (tmp_path / "answers.jsonl").read_text(encoding="utf-8").splitlines())}
    for fixture in fixtures:
        item = items[fixture["id"]]
        reference = answers[item["id"]]
        submission = (
            {"choice": reference["choice"]} if item["kind"] == "single_choice" else
            {blank["id"]: "not graded automatically" for blank in item["blanks"]} if item["kind"] == "blank_fill" else
            {"submission": "implementation link"}
        )
        result = grade_attempt(item, submission, reference)
        assert result.status == fixture["expected_status"], fixture["id"]
        assert result.score == fixture["expected_score"], fixture["id"]
        assert "reference_markdown" not in result.public_payload
