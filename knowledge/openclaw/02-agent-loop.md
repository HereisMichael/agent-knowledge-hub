---
source_id: openclaw-agent-loop-001
corpus: tech
topic: openclaw
type: concept
version: 2026.05
---

# OpenClaw Agent 循环

官方描述的一次 **agentic loop**：

`intake → context assembly → model inference → tool execution → streaming replies → persistence`

即 **ReAct（Reason + Act）**：模型推理 → 若需工具则执行 → 结果回填上下文 → 直至产出最终回复。

## 与 Harness 五支柱的关系

- **Context Assembly**：组装 system、历史、Skills 索引（非全量 Skill 正文）
- **Tool Integrity**：schema 校验与可恢复错误
- **Loop Discipline**：明确 stop / continue 信号
- **Policy**：敏感工具需授权
- **Lifecycle**：上下文压缩与 compaction

## 面试答法

画图：用户消息 → Gateway → Runtime 拼 prompt → LLM → tool? → loop → 通道回复。


## 参考来源

- https://docs.openclaw.ai/concepts/agent
