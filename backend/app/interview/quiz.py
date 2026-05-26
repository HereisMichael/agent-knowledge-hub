from __future__ import annotations

from app.config import settings
from app.interview.questions import get_question, pick_question
from app.llm.client import chat_json
from app.rag.knowledge_lookup import get_by_source_id


def score_answer_demo(question: dict, answer_text: str) -> dict:
    key_points = question.get("key_points", [])
    hits = sum(1 for kp in key_points if kp.lower() in answer_text.lower())
    ratio = hits / max(len(key_points), 1)
    score = int(min(100, ratio * 100 + len(answer_text) // 50))
    return {
        "ai_score": score,
        "matched_points": [kp for kp in key_points if kp.lower() in answer_text.lower()],
        "missing_points": [kp for kp in key_points if kp.lower() not in answer_text.lower()],
        "feedback": "Demo 评分：根据要点命中率估算。配置 LLM 后可获得详细反馈。",
    }


def score_answer_ai(question: dict, answer_text: str) -> dict:
    if settings.use_demo_llm:
        return score_answer_demo(question, answer_text)
    rubric = question.get("rubric", {})
    system = (
        "你是云厂商 SA 面试阅卷官。根据题目要点与评分维度给分（0-100），"
        "输出 JSON：ai_score, matched_points[], missing_points[], feedback"
    )
    user = f"题目：{question['question']}\n要点：{question.get('key_points')}\n维度：{rubric}\n考生答案：{answer_text}"
    result = chat_json(system, user)
    if "ai_score" not in result:
        result["ai_score"] = 70
    return result


def build_explanation(question: dict) -> dict:
    related = []
    for sid in question.get("related_source_ids", [])[:3]:
        doc = get_by_source_id(sid)
        if doc:
            related.append({"source_id": sid, "excerpt": doc["full_text"][:400]})
    return {
        "key_points": question.get("key_points", []),
        "follow_ups": question.get("follow_ups", []),
        "related": related,
    }


def next_question(**filters) -> dict | None:
    q = pick_question(**filters)
    if not q:
        return None
    return {"question": q, "explanation_available": True}
