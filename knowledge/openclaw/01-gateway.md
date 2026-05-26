---
source_id: openclaw-gateway-001
corpus: tech
topic: openclaw
type: concept
version: 2026.05
---

# OpenClaw Gateway

Gateway 是 OpenClaw 的**单一控制平面**：管理会话、渠道路由、工具调用与事件。默认监听本地端口（如 18789），把来自 IM 的消息转给 Agent Runtime。

## 职责

1. **会话管理**：隔离 workspace、多 Agent 路由
2. **通道接入**：Telegram、Discord、Slack 等
3. **工具与事件**：browser、canvas、cron、nodes

## 多 Agent 路由

可按 channel/account/peer 将流量路由到不同 workspace，实现「工作 Agent」与「私人 Agent」隔离。

## Harness 视角

Gateway 属于 **Harness 的编排层**：决定消息如何进入 loop、状态如何持久化，而非模型权重本身。


## 参考来源

- https://docs.openclaw.ai/gateway
