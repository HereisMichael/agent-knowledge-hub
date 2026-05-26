"""Structured mock interview stages and timing."""

from __future__ import annotations

STRUCTURED_STAGES = ["INTRO", "PROJECT", "ARCH", "PRODUCT", "QA_USER", "DEBRIEF"]

STAGE_LABELS: dict[str, str] = {
    "INTRO": "自我介绍",
    "PROJECT": "项目经历",
    "ARCH": "架构设计",
    "PRODUCT": "产品选型",
    "QA_USER": "候选人提问",
    "DEBRIEF": "复盘总结",
}

# 秒
STAGE_DURATION_SEC: dict[str, int] = {
    "INTRO": 5 * 60,
    "PROJECT": 10 * 60,
    "ARCH": 15 * 60,
    "PRODUCT": 10 * 60,
    "QA_USER": 5 * 60,
    "DEBRIEF": 5 * 60,
}

STAGE_PROMPTS = {
    "INTRO": "请用 2 分钟介绍你自己，突出与云售前/架构相关的经历。",
    "PROJECT": "请选一个你主导的云上项目，用 STAR 法则说明你的角色与结果。",
    "ARCH": "场景架构题（根据厂商与行业）",
    "PRODUCT": "请对比该场景下核心云产品的选型理由与竞品差异。",
    "QA_USER": "你有什么问题想问我们团队？",
}
