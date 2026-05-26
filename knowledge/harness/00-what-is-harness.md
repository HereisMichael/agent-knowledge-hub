---
source_id: harness-what-001
corpus: tech
topic: harness
type: concept
version: 2026.05
---

# 什么是 Agent Harness

**Agent = Model + Harness**。模型提供推理能力；Harness 是模型之外的一切：状态、工具执行、反馈循环、约束。

## 关键结论

- **模型不执行工具**：只产生 tool call；Harness 执行并回填结果
- **Harness 常比换模型更影响效果**：上下文、工具 API 设计、停止条件

## 组件清单

System prompt、Tools/Skills/MCP、沙箱、编排（子 Agent）、Hooks（compaction、lint、重试）、Eval。

OpenClaw/Hermes 的 Gateway+Runtime 都是 Harness 的具体实现。


## 参考来源

- https://www.langchain.com/blog/the-anatomy-of-an-agent-harness
