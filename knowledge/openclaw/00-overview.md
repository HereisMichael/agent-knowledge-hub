---
source_id: openclaw-overview-001
corpus: tech
topic: openclaw
type: concept
version: 2026.05
---

# OpenClaw 概述

OpenClaw 是开源、本地优先的个人 AI 助手框架。它不是 LLM 本身，而是连接 Claude/GPT/Ollama 等模型的 **Gateway + Agent Runtime**，在你已有渠道（Telegram、Slack 等）上提供可执行工具的助手能力。

## 核心定位

- **个人单用户助手**：会话、记忆、Skills 围绕一人工作流设计
- **本地控制面**：Gateway 作为 nervous system，路由消息、工具与事件
- **可扩展**：TypeScript 插件、Skills（SKILL.md）、MCP 工具

## 与聊天机器人的区别

聊天机器人以单轮/短上下文为主；OpenClaw 强调 **持久会话、工具执行、ReAct 循环** 与跨通道连续对话。

## 面试可强调

- 能说清 Gateway vs Agent Runtime vs Skills 的分工
- 能举例：如何用 Skill 封装「部署检查」而不污染 system prompt


## 参考来源

- https://docs.openclaw.ai
- https://github.com/openclaw/openclaw
