"""Regression tests for importing the external LLM-101-CN exercise source."""

from pathlib import Path
import json

import pytest

from scripts.import_llm101_exercises import _split_details, import_source
from scripts.validate_llm101_exercises import validate_package


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "LLM-101-CN"


@pytest.mark.skipif(not SOURCE_ROOT.is_dir(), reason="external source checkout unavailable")
def test_import_inventory_includes_all_current_exercise_pages(tmp_path: Path) -> None:
    result = import_source(SOURCE_ROOT, tmp_path)
    assert len(result.catalog["sets"]) == 25
    assert {item["kind"] for item in result.items} == {
        "single_choice", "blank_fill", "implementation_challenge"
    }
    assert result.manifest["commit"].startswith("e139bb6")
    assert result.manifest["schema_version"] == 1
    assert result.catalog["schema_version"] == 1
    assert len(result.manifest["files"]) == 25
    assert len([warning for warning in result.warnings if warning["code"] == "not_in_catalog"]) == 6
    assert {warning["code"] for warning in result.warnings} >= {"rights_unverified"}
    assert validate_package(tmp_path)["valid"] is True
    assert all("::: details" not in item["prompt_markdown"] for item in result.items)
    by_id = {item["id"]: item for item in result.items}
    assert by_id["llm101-rag-agent-fill-03"]["level"] == 3
    assert by_id["llm101-distributed-fill-02"]["level"] == 3


def test_import_separates_student_prompt_from_reference_answer(tmp_path: Path) -> None:
    source = tmp_path / "source"
    exercises = source / "docs" / "exercises"
    exercises.mkdir(parents=True)
    (exercises / "index.md").write_text("[Quiz](quiz.md)\n", encoding="utf-8")
    (exercises / "quiz.md").write_text(
        "---\ntitle: Quiz\ntopics: [attention]\n---\n"
        "# Quiz\n## 第 1 题：测试\n问题？\n**A.** 错\n**B.** 对\n"
        "<details>\n<summary>查看答案</summary>\n**正确答案：B**\n解析。\n</details>\n",
        encoding="utf-8",
    )
    result = import_source(source, tmp_path / "out", commit="test-commit")
    item = result.items[0]
    assert item["id"] == "llm101-quiz-01"
    assert item["kind"] == "single_choice"
    assert item["options"] == {"A": "错", "B": "对"}
    assert "正确答案" not in item["prompt_markdown"]
    assert "reference_markdown" not in item
    assert validate_package(tmp_path / "out")["valid"] is True
    assert validate_package(tmp_path / "out")["publishable"] is False
    (tmp_path / "out" / "rights-approval.json").write_text(
        json.dumps({"source_commit": "test-commit", "rights_note": "Owner granted public redistribution for this pinned source revision.", "reviewed_by": "test-reviewer"}),
        encoding="utf-8",
    )
    assert validate_package(tmp_path / "out")["publishable"] is True


def test_import_splits_multiple_choice_questions_in_one_section(tmp_path: Path) -> None:
    exercises = tmp_path / "source" / "docs" / "exercises"
    exercises.mkdir(parents=True)
    (exercises / "index.md").write_text("[Quiz](mixed-fill.md)\n", encoding="utf-8")
    (exercises / "mixed-fill.md").write_text(
        "---\ntitle: Quiz\ntopics: [alignment]\n---\n# Quiz\n"
        "## 练习 1：概念题\n"
        "**题目 1**：第一个问题？\n- A) 错\n- B) 对\n"
        "<details>\n<summary>答案</summary>\n**答案：B**\n</details>\n"
        "**题目 2**：第二个问题？\n- A) 对\n- B) 错\n"
        "<details>\n<summary>答案</summary>\n**答案：A**\n</details>\n",
        encoding="utf-8",
    )
    result = import_source(tmp_path / "source", tmp_path / "out", commit="test-commit")
    assert [item["kind"] for item in result.items] == ["single_choice", "single_choice"]
    assert [item["id"] for item in result.items] == ["llm101-mixed-fill-01", "llm101-mixed-fill-02"]
    assert [item["options"]["A"] for item in result.items] == ["错", "对"]


def test_vitepress_hint_is_private_even_with_code_fences() -> None:
    prompt, reference = _split_details(
        "题面\n```python\nprint('::: details literal')\n```\n"
        "::: details 提示\n答案是 42\n```python\nsecret = 42\n```\n:::\n继续练习"
    )
    assert "答案是 42" not in prompt
    assert "secret = 42" not in prompt
    assert "::: details literal" in prompt
    assert "继续练习" in prompt
    assert "答案是 42" in reference


def test_build_reference_sections_stay_private_without_hiding_later_tasks(tmp_path: Path) -> None:
    exercises = tmp_path / "source" / "docs" / "exercises"
    exercises.mkdir(parents=True)
    (exercises / "index.md").write_text("[Build](demo-build.md)\n", encoding="utf-8")
    (exercises / "demo-build.md").write_text(
        "# Demo challenge\n## 挑战目标\n实现一个模型。\n"
        "## 参考实现\n```python\nanswer_one = 42\n```\n"
        "## 进阶思考\n尝试更大的模型。\n"
        "## MLM 代码训练模式\n```python\nanswer_two = 43\n```\n"
        "## 推荐资源\n继续阅读。\n",
        encoding="utf-8",
    )

    result = import_source(tmp_path / "source", tmp_path / "out", commit="test-commit")
    prompt = result.items[0]["prompt_markdown"]
    answer = json.loads((tmp_path / "out" / "answers.jsonl").read_text(encoding="utf-8"))["reference_markdown"]
    assert "answer_one = 42" not in prompt
    assert "answer_two = 43" not in prompt
    assert "进阶思考" in prompt
    assert "推荐资源" in prompt
    assert "answer_one = 42" in answer
    assert "answer_two = 43" in answer


def test_validator_rejects_a_public_vitepress_hint(tmp_path: Path) -> None:
    source = tmp_path / "source" / "docs" / "exercises"
    source.mkdir(parents=True)
    (source / "index.md").write_text("[Demo](demo.md)\n", encoding="utf-8")
    (source / "demo.md").write_text("# Demo\n## 练习 1\n题目", encoding="utf-8")
    output = tmp_path / "out"
    import_source(tmp_path / "source", output, commit="test")
    items_path = output / "items.jsonl"
    item = json.loads(items_path.read_text(encoding="utf-8"))
    item["prompt_markdown"] += "\n::: details 提示\n泄露\n:::"
    items_path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")
    report = validate_package(output)
    assert report["valid"] is False
    assert any("answer leaked" in error for error in report["errors"])


def test_validator_rejects_a_public_reference_section(tmp_path: Path) -> None:
    source = tmp_path / "source" / "docs" / "exercises"
    source.mkdir(parents=True)
    (source / "index.md").write_text("[Demo](demo-build.md)\n", encoding="utf-8")
    (source / "demo-build.md").write_text("# Demo\n## 挑战目标\n题目", encoding="utf-8")
    output = tmp_path / "out"
    import_source(tmp_path / "source", output, commit="test")
    items_path = output / "items.jsonl"
    item = json.loads(items_path.read_text(encoding="utf-8"))
    item["prompt_markdown"] += "\n## 参考实现\nsecret solution"
    items_path.write_text(json.dumps(item, ensure_ascii=False) + "\n", encoding="utf-8")

    report = validate_package(output)
    assert report["valid"] is False
    assert any("answer leaked" in error for error in report["errors"])
