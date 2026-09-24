import json
from pathlib import Path

import pytest

from scripts.validate_question_bank import validate_question_bank


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "knowledge/interview/questions.jsonl"
QUESTION_BANK_PAGE = ROOT / "web/src/pages/QuestionBank.tsx"
QUESTION_CATALOG = ROOT / "web/src/questions/catalog.ts"


def _valid_row() -> dict[str, object]:
    return {
        "id": "question-1",
        "vendor": "aliyun",
        "category": "rag",
        "difficulty": 3,
        "question": "How?",
        "key_points": ["one"],
        "rubric": {"depth": 100},
        "follow_ups": [],
        "related_source_ids": [],
        "tags": [],
        "source_note": "test",
    }


def _write_rows(path: Path, *rows: object) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_migrated_question_bank_has_expected_contract() -> None:
    stats = validate_question_bank(BANK)
    assert stats["records"] == 183
    assert stats["reference_answers"] == 95
    assert stats["vendors"] == {
        "aliyun": 58,
        "aws": 44,
        "general": 37,
        "tencent": 44,
    }
    assert stats["categories"] == {
        "agent": 21,
        "ai-arch": 18,
        "ai-safety": 12,
        "ai-scenario": 12,
        "cloud-ai": 13,
        "inference": 61,
        "llm": 19,
        "prompt": 6,
        "rag": 21,
    }


def test_published_ai_infra_questions_all_have_reference_answers() -> None:
    rows = [
        json.loads(line)
        for line in BANK.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ai_infra = [row for row in rows if row["id"].startswith("general-ai-infra-")]

    assert len(ai_infra) == 37
    assert all(row.get("reference_answer", "").strip() for row in ai_infra)


def test_question_bank_page_exposes_every_published_vendor() -> None:
    rows = [
        json.loads(line)
        for line in BANK.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    published_vendors = {row["vendor"] for row in rows}
    page_source = QUESTION_BANK_PAGE.read_text(encoding="utf-8")
    catalog_source = QUESTION_CATALOG.read_text(encoding="utf-8")
    source_order = catalog_source.split("QUESTION_SOURCES", 1)[1].split(";", 1)[0]

    for vendor in published_vendors:
        assert f'{vendor}: "' in catalog_source
        assert f'"{vendor}"' in source_order

    assert 'from "../questions/catalog"' in page_source
    assert "QUESTION_SOURCES" in page_source


def test_validator_rejects_duplicate_ids(tmp_path: Path) -> None:
    row = _valid_row()
    row["id"] = "duplicate"
    path = tmp_path / "duplicate.jsonl"
    _write_rows(path, row, row)

    with pytest.raises(ValueError, match="duplicate question id"):
        validate_question_bank(path)


def test_validator_rejects_non_object_json_row(tmp_path: Path) -> None:
    path = tmp_path / "scalar.jsonl"
    _write_rows(path, ["not", "an", "object"])

    with pytest.raises(ValueError, match="must be an object"):
        validate_question_bank(path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 123),
        ("vendor", ""),
        ("category", None),
        ("difficulty", True),
        ("question", "  "),
        ("source_note", []),
        ("key_points", []),
        ("key_points", [1]),
        ("rubric", {}),
        ("follow_ups", {}),
        ("related_source_ids", "source"),
        ("tags", None),
    ],
)
def test_validator_rejects_malformed_required_field_types(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    row = _valid_row()
    row[field] = value
    path = tmp_path / "malformed.jsonl"
    _write_rows(path, row)

    with pytest.raises(ValueError, match=field):
        validate_question_bank(path)


def test_null_reference_answer_is_valid_but_not_counted(tmp_path: Path) -> None:
    row = _valid_row()
    row["reference_answer"] = None
    path = tmp_path / "null-reference.jsonl"
    _write_rows(path, row)

    assert validate_question_bank(path)["reference_answers"] == 0


def test_non_string_reference_answer_is_rejected(tmp_path: Path) -> None:
    row = _valid_row()
    row["reference_answer"] = 123
    path = tmp_path / "numeric-reference.jsonl"
    _write_rows(path, row)

    with pytest.raises(ValueError, match="reference_answer"):
        validate_question_bank(path)
