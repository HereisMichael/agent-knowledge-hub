---
source_id: harness-agent-loop-001
corpus: tech
topic: harness
type: concept
version: 2026.05
---

# Agent Loop 对照

通用循环：

1. Harness 组装 prompt
2. 调用模型
3. 若 tool call → Harness 执行 → 结果回填
4. 直至 stop 或达 max steps

## OpenClaw / Hermes

二者均实现 ReAct，差异在记忆策略、Skill 进化、沙箱与渠道集成深度。

## SA 面试

客户问「智能售前助手」：答 **RAG + Harness（HITL 门 + 合规规则）+ 专用 Agent**，而非裸 ChatGPT。


## 参考来源

- https://docs.openclaw.ai/concepts/agent
