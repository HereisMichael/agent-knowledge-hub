from __future__ import annotations

from app.db import store
from app.interview.questions import get_question, pick_question
from app.llm.client import chat_json
from app.rag.knowledge_lookup import get_by_source_id
from app.settings.service import LlmRuntime, resolve_llm


def score_answer_demo(
    question: dict, answer_text: str, reference_answer: str | None = None
) -> dict:
    key_points = question.get("key_points", [])
    ref = reference_answer or ""
    combined = (answer_text + " " + ref).lower()
    hits = sum(1 for kp in key_points if kp.lower() in combined)
    if reference_answer:
        ref_tokens = set(reference_answer.lower().split())
        ans_tokens = set(answer_text.lower().split())
        overlap = len(ref_tokens & ans_tokens) / max(len(ref_tokens), 1)
        score = int(min(100, overlap * 70 + len(answer_text) // 40 + hits * 5))
        feedback = (
            f"Demo 评分：与你的参考答案词面重合约 {int(overlap * 100)}%，"
            "配置模型 API 后可获得语义级对比反馈。"
        )
    else:
        ratio = hits / max(len(key_points), 1)
        score = int(min(100, ratio * 100 + len(answer_text) // 50))
        feedback = "Demo 评分：根据要点命中率估算。可在设置中配置模型，并填写「我的参考答案」以对比评分。"

    return {
        "ai_score": score,
        "matched_points": [kp for kp in key_points if kp.lower() in answer_text.lower()],
        "missing_points": [kp for kp in key_points if kp.lower() not in answer_text.lower()],
        "feedback": feedback,
        "reference_used": bool(reference_answer),
    }


def score_answer_ai(
    question: dict,
    answer_text: str,
    *,
    reference_answer: str | None = None,
    runtime: LlmRuntime | None = None,
) -> dict:
    rt = runtime or resolve_llm()
    if rt.demo:
        return score_answer_demo(question, answer_text, reference_answer)

    rubric = question.get("rubric", {})
    if reference_answer:
        system = (
            "你是云厂商 SA 面试阅卷官。考生提供了「我的参考答案」作为掌握标准。"
            "请对比考生本次作答与参考答案的语义覆盖、结构完整性与可落地性，给分 0-100。"
            "输出 JSON：ai_score, coverage_vs_reference(0-100), matched_points[], "
            "missing_points[], gaps_vs_reference[], feedback, improvement_tip"
        )
        user = (
            f"题目：{question['question']}\n"
            f"我的参考答案：{reference_answer}\n"
            f"本次作答：{answer_text}\n"
            f"题目要点：{question.get('key_points')}\n"
            f"评分维度：{rubric}"
        )
    else:
        system = (
            "你是云厂商 SA 面试阅卷官。根据题目要点与评分维度给分（0-100），"
            "输出 JSON：ai_score, matched_points[], missing_points[], feedback, "
            "suggestion_to_add_reference（提醒用户可保存参考答案以便追踪进步）"
        )
        user = (
            f"题目：{question['question']}\n要点：{question.get('key_points')}\n"
            f"维度：{rubric}\n考生答案：{answer_text}"
        )

    result = chat_json(system, user, runtime=rt)
    if "ai_score" not in result:
        result["ai_score"] = 70
    result["reference_used"] = bool(reference_answer)
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


def submit_answer(
    user_id: str,
    question_id: str,
    answer_text: str,
    *,
    reference_answer: str | None = None,
    save_reference: bool = False,
    use_ai: bool = True,
    self_score: int | None = None,
) -> dict:
    q = get_question(question_id)
    if not q:
        raise KeyError(question_id)

    runtime = resolve_llm(user_id)
    ref_text = (reference_answer or "").strip()

    if save_reference and ref_text:
        store.upsert_reference_answer(user_id, question_id, ref_text)
    elif not ref_text:
        saved = store.get_reference_answer(user_id, question_id)
        if saved:
            ref_text = saved.get("reference_text") or ""

    ai_result = (
        score_answer_ai(q, answer_text, reference_answer=ref_text or None, runtime=runtime)
        if use_ai
        else score_answer_demo(q, answer_text, ref_text or None)
    )

    comparison_detail = {
        k: ai_result[k]
        for k in (
            "matched_points",
            "missing_points",
            "gaps_vs_reference",
            "coverage_vs_reference",
            "improvement_tip",
            "reference_used",
        )
        if k in ai_result
    }

    record = store.save_quiz_answer(
        user_id,
        question_id,
        answer_text,
        self_score,
        ai_result.get("ai_score"),
        reference_answer=ref_text or None,
        feedback=ai_result.get("feedback"),
        model_name=runtime.model if not runtime.demo else "demo",
        comparison_detail=comparison_detail,
    )

    from app.interview import review as review_svc

    review_card = review_svc.schedule_after_quiz(
        user_id, question_id, ai_result.get("ai_score")
    )

    return {
        "question": q,
        "explanation": build_explanation(q),
        "attempt_id": record["id"],
        "reference_saved": bool(save_reference and ref_text),
        "reference_used": bool(ref_text),
        "review_scheduled": review_card is not None,
        "score_history": store.get_question_attempt_scores(user_id, question_id),
        **ai_result,
    }
