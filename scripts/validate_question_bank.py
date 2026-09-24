from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_FIELDS = {
    "id",
    "vendor",
    "category",
    "difficulty",
    "question",
    "key_points",
    "rubric",
    "follow_ups",
    "related_source_ids",
    "tags",
    "source_note",
}
STRING_FIELDS = {"id", "vendor", "category", "question", "source_note"}
LIST_FIELDS = {"key_points", "follow_ups", "related_source_ids", "tags"}


def validate_question_bank(path: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"JSON value on line {line_number} must be an object")
        missing = REQUIRED_FIELDS - row.keys()
        if missing:
            raise ValueError(f"missing fields on line {line_number}: {sorted(missing)}")
        for field in STRING_FIELDS:
            value = row[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string on line {line_number}")
        difficulty = row["difficulty"]
        if type(difficulty) is not int:
            raise ValueError(f"difficulty must be an integer on line {line_number}")
        for field in LIST_FIELDS:
            if not isinstance(row[field], list):
                raise ValueError(f"{field} must be a list on line {line_number}")
        question_id = row["id"].strip()
        if question_id in seen:
            raise ValueError(f"duplicate question id: {question_id}")
        seen.add(question_id)
        if not row["key_points"] or not all(
            isinstance(point, str) and point.strip() for point in row["key_points"]
        ):
            raise ValueError(f"empty key_points on line {line_number}")
        if not isinstance(row["rubric"], dict) or not row["rubric"]:
            raise ValueError(f"empty rubric on line {line_number}")
        reference_answer = row.get("reference_answer")
        if reference_answer is not None and not isinstance(reference_answer, str):
            raise ValueError(f"reference_answer must be a string or null on line {line_number}")
        rows.append(row)

    vendors = Counter(row["vendor"] for row in rows)
    categories = Counter(row["category"] for row in rows)
    reference_answers = sum(
        isinstance(row.get("reference_answer"), str)
        and bool(row["reference_answer"].strip())
        for row in rows
    )
    return {
        "records": len(rows),
        "reference_answers": reference_answers,
        "vendors": dict(sorted(vendors.items())),
        "categories": dict(sorted(categories.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the public question bank")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_question_bank(args.path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
