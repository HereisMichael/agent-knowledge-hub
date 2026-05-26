---
source_id: hermes-overview-001
corpus: tech
topic: hermes
type: concept
version: 2026.05
---

# Hermes Agent 概述

Hermes Agent 由 Nous Research 开源，定位为 **长期运行、自改进** 的自治 Agent，而非 IDE 内嵌 copilot。

## 差异化

1. **持久记忆**：跨会话保留偏好、项目、环境
2. **Skills 自进化**：完成任务后沉淀 Skill，并在复用中改进
3. **Gateway 多平台**：Telegram/Discord/Slack/WhatsApp/CLI
4. **子 Agent 与 Cron**：并行任务与无人值守调度

## 与 OpenClaw 对比（简表）

| 维度 | OpenClaw | Hermes |
|------|----------|--------|
| 重心 | 个人本地助手 + 渠道 | 服务器常驻 + 学习循环 |
| 记忆 | 有 | 强调文件/记忆系统 |
| Skills | 按需加载 | 自动生成与改进 |

## 面试话术

强调 **closed learning loop**：经验 → 记忆/Skill → 下次更快。


## 参考来源

- https://hermes-agent.nousresearch.com
- https://github.com/NousResearch/hermes-agent
