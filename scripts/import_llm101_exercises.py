"""Import LLM-101-CN exercise Markdown into review-only structured artifacts.

The generated package is staging data. In particular, ``answers.jsonl`` must
never be mounted or copied into the web application's static assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SOURCE_URL = "https://github.com/boots-coder/LLM-101-CN"
HEADING = re.compile(r"^##\s+(.+)$")
OPTION = re.compile(r"^(?:\*\*([A-D])\.\*\*|\-\s*([A-D])\))\s*(.+)$", re.MULTILINE)
ANSWER = re.compile(r"(?:正确)?答案\s*[：:]\s*([A-D])", re.IGNORECASE)
BLANK = re.compile(r"_{5,}")
INDEX_LINK = re.compile(r"\(([^)#]+\.md)(?:#[^)]*)?\)")
SUBQUESTION = re.compile(r"^\*\*题目\s+(\d+)\*\*", re.MULTILINE)
PRIVATE_SECTION = re.compile(r"^##\s+(?:参考实现|MLM 代码训练模式)(?:\s|$)")


@dataclass(frozen=True)
class ImportResult:
    catalog: dict[str, object]
    items: list[dict[str, object]]
    manifest: dict[str, object]
    warnings: list[dict[str, object]]


def _frontmatter(raw: str) -> tuple[dict[str, Any], list[str], int]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines, 1
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("frontmatter has no closing delimiter") from exc
    data = yaml.safe_load("\n".join(lines[1:end])) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, lines[end + 1 :], end + 2


def _sections(lines: list[str], first_line: int, stem: str) -> list[tuple[str, str, int]]:
    if stem.endswith("-build"):
        title = next((line[2:].strip() for line in lines if line.startswith("# ")), stem)
        return [(title, "\n".join(lines).strip(), first_line)]

    sections: list[tuple[str, str, int]] = []
    current_title: str | None = None
    current_line = 0
    body: list[str] = []
    for offset, line in enumerate(lines):
        match = HEADING.match(line)
        if match:
            if current_title is not None:
                sections.append((current_title, "\n".join(body).strip(), current_line))
            title = match.group(1).strip()
            is_question = title.startswith("练习 ") or title.startswith("第 ")
            current_title = title if is_question else None
            current_line = first_line + offset
            body = [line] if is_question else []
        elif current_title is not None:
            body.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(body).strip(), current_line))
    expanded: list[tuple[str, str, int]] = []
    for title, body, line_number in sections:
        matches = list(SUBQUESTION.finditer(body))
        if len(matches) < 2:
            expanded.append((title, body, line_number))
            continue
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            subline = line_number + body.count("\n", 0, match.start())
            expanded.append((f"{title} / 题目 {match.group(1)}", body[match.start():end].strip(), subline))
    return expanded


def _split_details(markdown: str) -> tuple[str, str]:
    """Move HTML and VitePress answer/hint folds into the private reference."""
    prompt: list[str] = []
    answers: list[str] = []
    folded: list[str] = []
    fence: str | None = None
    detail_kind: str | None = None
    private_section = False
    for line in markdown.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
        if detail_kind is None and fence is None and stripped.startswith("## "):
            if private_section:
                answers.append("\n".join(folded).strip())
                folded = []
                private_section = False
            if PRIVATE_SECTION.match(stripped):
                private_section = True
                folded = [line]
                continue
        if private_section:
            folded.append(line)
            continue
        if detail_kind and fence is None and (
            (detail_kind == "html" and stripped.lower().startswith("</details"))
            or (detail_kind == "vitepress" and stripped == ":::")
        ):
            answers.append("\n".join(folded).strip())
            detail_kind = None
            folded = []
            continue
        if detail_kind is None and fence is None and (
            stripped.lower().startswith("<details")
            or re.match(r"^:::\s*details(?:\s|$)", stripped, re.IGNORECASE)
        ):
            detail_kind = "html" if stripped.startswith("<") else "vitepress"
            folded = []
            continue
        if detail_kind:
            folded.append(line)
        else:
            prompt.append(line)
    if detail_kind or private_section:
        answers.append("\n".join(folded).strip())
    return "\n".join(prompt).strip(), "\n\n".join(answers).strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n" for value in values),
        encoding="utf-8",
    )


def import_source(source_root: Path, output_dir: Path, commit: str | None = None) -> ImportResult:
    source_root = source_root.resolve()
    exercise_dir = source_root / "docs" / "exercises"
    if not exercise_dir.is_dir():
        raise ValueError(f"not an LLM-101-CN exercise checkout: {exercise_dir}")
    if commit is None:
        commit = subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
        ).strip()

    files = sorted(path for path in exercise_dir.glob("*.md") if path.name != "index.md")
    if not files:
        raise ValueError("no exercise pages found")
    index_text = (exercise_dir / "index.md").read_text(encoding="utf-8")
    catalog_stems = {Path(match).stem for match in INDEX_LINK.findall(index_text)}
    warnings: list[dict[str, object]] = []
    if not (source_root / "LICENSE").is_file():
        warnings.append({"code": "rights_unverified", "message": "source LICENSE missing; public publish blocked"})

    sets: list[dict[str, object]] = []
    items: list[dict[str, object]] = []
    answers: list[dict[str, object]] = []
    manifest_files: list[dict[str, object]] = []
    for path in files:
        relative = path.relative_to(source_root).as_posix()
        raw = path.read_text(encoding="utf-8")
        meta, lines, first_line = _frontmatter(raw)
        stem = path.stem
        set_id = f"llm101-{stem}"
        title = str(meta.get("title") or stem)
        topics = [str(topic) for topic in meta.get("topics", [])]
        if not topics:
            topics = [stem]
        sections = _sections(lines, first_line, stem)
        if not sections:
            warnings.append({"code": "no_exercise_sections", "path": relative})
        set_item_ids: list[str] = []
        for ordinal, (heading, body, line_number) in enumerate(sections, start=1):
            prompt, reference = _split_details(body)
            item_id = f"{set_id}-{ordinal:02d}"
            stated_level = re.search(r"Level\s*([1-4])(?:\s*[-–]\s*([1-4]))?", heading, re.IGNORECASE)
            options = {bold or listed: label for bold, listed, label in OPTION.findall(prompt)}
            correct = ANSWER.search(reference)
            if options and correct:
                kind, answer_mode = "single_choice", "choice_exact"
            elif stem.endswith("-build"):
                kind, answer_mode = "implementation_challenge", "manual_review"
            else:
                kind, answer_mode = "blank_fill", "manual_review"
            level = (
                int(stated_level.group(2) or stated_level.group(1))
                if stated_level else 4 if stem.endswith("-build") else 1 if kind == "single_choice" else 2
            )
            blank_count = len(BLANK.findall(prompt)) if kind == "blank_fill" else 0
            anchor = {"path": relative, "heading": heading, "line": line_number}
            item: dict[str, object] = {
                "id": item_id,
                "set_id": set_id,
                "title": heading,
                "kind": kind,
                "level": level,
                "topics": topics,
                "prompt_markdown": prompt,
                "options": options,
                "blanks": [{"id": f"blank-{i}"} for i in range(1, blank_count + 1)],
                "answer_mode": answer_mode,
                "validation_status": "ready" if answer_mode == "choice_exact" else "manual_review",
                "source_anchor": anchor,
            }
            items.append(item)
            answers.append({"id": item_id, "reference_markdown": reference, "choice": correct.group(1).upper() if correct else None})
            set_item_ids.append(item_id)
        sets.append({
            "id": set_id, "title": title, "topics": topics,
            "description": str(meta.get("description") or ""),
            "item_ids": set_item_ids, "source_path": relative,
        })
        manifest_files.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        if stem not in catalog_stems:
            warnings.append({"code": "not_in_catalog", "path": relative})

    catalog: dict[str, object] = {"schema_version": 1, "source": "llm101", "sets": sets}
    manifest: dict[str, object] = {
        "schema_version": 1, "source": "llm101", "source_url": SOURCE_URL, "commit": commit,
        "files": manifest_files, "rights_status": "unverified" if not (source_root / "LICENSE").is_file() else "review_required",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "catalog.json", catalog)
    _write_jsonl(output_dir / "items.jsonl", items)
    _write_jsonl(output_dir / "answers.jsonl", answers)
    _write_json(output_dir / "source-manifest.json", manifest)
    _write_jsonl(output_dir / "warnings.jsonl", warnings)
    return ImportResult(catalog, items, manifest, warnings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit")
    args = parser.parse_args()
    result = import_source(args.source, args.output, args.commit)
    print(f"imported {len(result.catalog['sets'])} sets, {len(result.items)} items, {len(result.warnings)} warnings")


if __name__ == "__main__":
    main()
