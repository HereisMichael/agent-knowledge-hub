from __future__ import annotations

import json
from datetime import datetime, timezone

from app.config import settings
from app.db import store
from app.interview.questions import pick_question
from app.interview.stages import (
    STAGE_DURATION_SEC,
    STAGE_LABELS,
    STAGE_PROMPTS,
    STRUCTURED_STAGES,
)
from app.labs.recommend import recommend_labs
from app.llm.client import chat_json, chat_text

COACH_SYSTEM = """你是阿里云/腾讯云/AWS 的资深 SA 面试官。
规则：一次只问一个问题；根据候选人上一轮回答追问 1-2 次（挑战假设、要求量化）。
不要一次给出标准答案。语气专业、简洁。
若候选人请求提示，给阶梯提示而非完整答案。"""


def _vendor_name(vendor: str) -> str:
    return {"aliyun": "阿里云", "tencent": "腾讯云", "aws": "AWS"}.get(vendor, vendor)


def stage_timing(session: dict) -> dict | None:
    if session.get("mode") != "structured":
        return None
    stage = session.get("stage", "INTRO")
    duration = STAGE_DURATION_SEC.get(stage, 300)
    started = session.get("stage_started_at")
    elapsed = 0
    if started:
        try:
            t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
            elapsed = int((datetime.now(timezone.utc) - t0).total_seconds())
        except Exception:
            elapsed = 0
    remaining = max(0, duration - elapsed)
    idx = STRUCTURED_STAGES.index(stage) if stage in STRUCTURED_STAGES else 0
    return {
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, stage),
        "duration_sec": duration,
        "elapsed_sec": elapsed,
        "remaining_sec": remaining,
        "stage_index": idx,
        "total_stages": len(STRUCTURED_STAGES) - 1,
        "stages": [
            {"id": s, "label": STAGE_LABELS.get(s, s), "duration_sec": STAGE_DURATION_SEC.get(s, 0)}
            for s in STRUCTURED_STAGES
            if s != "DEBRIEF"
        ],
    }


def _with_timing(session: dict, payload: dict) -> dict:
    timing = stage_timing(session)
    if timing:
        payload["stage_timing"] = timing
    return payload


def start_message(session: dict) -> str:
    vendor = _vendor_name(session.get("vendor", "aliyun"))
    if session["mode"] == "structured":
        mins = STAGE_DURATION_SEC.get("INTRO", 300) // 60
        return (
            f"欢迎参加{vendor} SA 结构化模拟面试。当前环节：自我介绍（约 {mins} 分钟）。\n\n"
            f"{STAGE_PROMPTS['INTRO']}"
        )
    return (
        f"欢迎参加{vendor} SA 模拟面试（自由多轮）。请先说明你的背景，"
        f"然后我会从「{session.get('focus', '综合')}」方向提问。"
    )


def handle_message(session_id: str, user_message: str, want_hint: bool = False) -> dict:
    session = store.get_mock_session(session_id)
    transcript = session["transcript"]
    transcript.append({"role": "user", "content": user_message})

    if session["mode"] == "structured":
        reply, new_stage = _structured_turn(session, user_message, want_hint)
        if new_stage:
            store.update_mock_session(
                session_id,
                stage=new_stage,
                stage_started_at=datetime.now(timezone.utc).isoformat(),
            )
            session["stage"] = new_stage
            session["stage_started_at"] = datetime.now(timezone.utc).isoformat()
    else:
        reply = _free_turn(session, user_message, want_hint)

    transcript.append({"role": "interviewer", "content": reply})
    store.update_mock_session(session_id, transcript=transcript)
    session = store.get_mock_session(session_id)
    return _with_timing(
        session,
        {"reply": reply, "stage": session.get("stage"), "transcript": transcript},
    )


def _free_turn(session: dict, user_message: str, want_hint: bool) -> str:
    history = "\n".join(
        f"{t['role']}: {t['content'][:500]}" for t in session["transcript"][-8:]
    )
    if want_hint:
        user_message = f"[候选人请求提示] {user_message}"
    prompt = f"厂商：{session.get('vendor')}\n历史：\n{history}\n\n候选人最新：{user_message}"
    return chat_text(COACH_SYSTEM, prompt)


def _structured_turn(session: dict, user_message: str, want_hint: bool) -> tuple[str, str | None]:
    stage = session.get("stage", "INTRO")
    idx = STRUCTURED_STAGES.index(stage) if stage in STRUCTURED_STAGES else 0

    if want_hint:
        return chat_text(COACH_SYSTEM, f"环节 {stage}，给阶梯提示，不要泄题：{user_message}"), None

    if stage == "ARCH":
        q = pick_question(vendor=session.get("vendor"), category="architecture")
        qtext = q["question"] if q else "请设计一个高可用三层 Web 架构并说明容灾。"
        reply = chat_text(
            COACH_SYSTEM,
            f"环节：架构题\n题目：{qtext}\n候选人回答：{user_message}\n请追问或进入下一环节。",
        )
        return reply + "\n\n（架构环节结束后可说「下一环节」进入产品题）", None

    history = "\n".join(
        f"{t['role']}: {t['content'][:400]}" for t in session["transcript"][-6:]
    )
    reply = chat_text(
        COACH_SYSTEM,
        f"当前环节：{stage}\n历史：{history}\n候选人：{user_message}\n"
        "若本环节信息足够，在回复末尾写 [NEXT_STAGE]",
    )

    new_stage = None
    if "[NEXT_STAGE]" in reply:
        reply = reply.replace("[NEXT_STAGE]", "").strip()
        if idx + 1 < len(STRUCTURED_STAGES) - 1:
            new_stage = STRUCTURED_STAGES[idx + 1]
            nxt = STAGE_PROMPTS.get(new_stage, "")
            label = STAGE_LABELS.get(new_stage, new_stage)
            mins = STAGE_DURATION_SEC.get(new_stage, 300) // 60
            reply += f"\n\n---\n进入下一环节：{label}（约 {mins} 分钟）\n{nxt}"
    return reply, new_stage


def finish_session(session_id: str) -> dict:
    session = store.get_mock_session(session_id)
    transcript = session["transcript"]
    history = json.dumps(transcript[-20:], ensure_ascii=False)

    if settings.use_demo_llm:
        report = {
            "scores": {"structure": 75, "depth": 70, "communication": 78},
            "highlights": ["表达较清晰", "有项目经历"],
            "gaps": ["架构量化指标可加强", "竞品对比不够"],
            "answer_rewrite": "建议在架构题中补充 RPO/RTO 与成本估算。",
            "suggested_lab_ids": ["lab-draw-arch-mermaid", "lab-vendor-slb-compare"],
        }
    else:
        system = (
            "根据模拟面试 transcript 输出 JSON："
            "scores{structure,depth,tradeoff,compliance,communication}, "
            "highlights[], gaps[], answer_rewrite, suggested_lab_ids[]"
        )
        report = chat_json(COACH_SYSTEM, f"生成面试报告：\n{history}")

    labs = recommend_labs(gaps=report.get("gaps", []), limit=3)
    report["recommended_labs"] = labs
    lab_ids = [l["id"] for l in labs]
    store.update_mock_session(
        session_id,
        stage="DEBRIEF",
        scores=report.get("scores"),
        report=report,
        recommended_lab_ids=lab_ids,
    )
    return store.get_mock_session(session_id)
