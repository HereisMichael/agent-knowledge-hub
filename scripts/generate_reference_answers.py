"""
Generate reference answers for all aliyun questions using the running backend LLM.
Updates questions.jsonl in-place with a new 'reference_answer' field.
"""
import json
import os
import sys
import time
import sqlite3
import requests
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "interview" / "questions.jsonl"
DB_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "hub.db"

PROMPT_TEMPLATE = """你是一位资深的云厂商售前解决方案架构师（SA），正在面试中回答面试官的技术问题。
请用结构化、专业的方式回答以下面试题，作为高质量的参考答案。

要求：
1. 回答要体现SA的视角：技术深度 + 业务理解 + 方案落地能力
2. 使用清晰的层次结构（可以用编号或要点）
3. 适当结合阿里云的具体产品和技术细节
4. 体现架构思维：需求分析 → 方案设计 → 技术选型 → 落地实施
5. 语言简洁专业，避免空泛的描述
6. 控制在 400-600 字左右

题目：{question}

题目分类：{category}
难度：{difficulty}/5
关键要点提示：
{key_points}

请直接给出完整参考答案："""


def load_questions():
    questions = []
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def save_questions(questions):
    with open(QUESTIONS_PATH, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")


def get_llm_config():
    """Read LLM config from SQLite database."""
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", ("default",))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print("ERROR: No user settings found in database. Please configure LLM in the Settings page first.")
        sys.exit(1)

    base_url = (row["llm_base_url"] or "").strip()
    api_key = (row["llm_api_key"] or "").strip()
    model = (row["llm_model"] or "").strip()

    if not api_key or not base_url:
        print("ERROR: LLM API key or base URL not configured in database.")
        sys.exit(1)

    return base_url, api_key, model


def call_llm(base_url, api_key, model, prompt_text):
    """Call the LLM API directly."""
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一位阿里云售前解决方案架构师，擅长为客户设计技术方案。请用中文回答。"},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": 0.3,
            "max_tokens": 1200,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def main():
    questions = load_questions()
    aliyun_questions = [q for q in questions if q.get("vendor") == "aliyun"]
    already_done = [q for q in aliyun_questions if q.get("reference_answer")]
    todo = [q for q in aliyun_questions if not q.get("reference_answer")]

    print(f"Total aliyun questions: {len(aliyun_questions)}")
    print(f"Already done: {len(already_done)}")
    print(f"Remaining: {len(todo)}")

    if not todo:
        print("All done!")
        return

    base_url, api_key, model = get_llm_config()
    print(f"Using model: {model} via {base_url}")

    # Test connection
    test_prompt = PROMPT_TEMPLATE.format(
        question="测试连接", category="test", difficulty=1, key_points="- test",
    )
    try:
        test_reply = call_llm(base_url, api_key, model, test_prompt)
        print(f"  [OK] LLM connected ({len(test_reply)} chars)")
    except Exception as e:
        print(f"  [FAIL] LLM connection failed: {e}")
        return

    for i, q in enumerate(todo):
        idx = i + 1
        q_text = q["question"][:60]
        print(f"\n[{idx}/{len(todo)}] {q['id']}: {q_text}...")
        try:
            prompt = PROMPT_TEMPLATE.format(
                question=q["question"],
                category=q.get("category", ""),
                difficulty=q.get("difficulty", 3),
                key_points="\n".join(f"- {p}" for p in q.get("key_points", [])),
            )
            answer = call_llm(base_url, api_key, model, prompt)
            q["reference_answer"] = answer
            print(f"  [OK] Generated ({len(answer)} chars)")
            save_questions(questions)
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            time.sleep(3)
            continue

    done_count = sum(1 for q in aliyun_questions if q.get("reference_answer"))
    print(f"\n\nDone! {done_count}/{len(aliyun_questions)} reference answers generated.")


if __name__ == "__main__":
    main()
