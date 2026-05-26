---
source_id: harness-eval-001
corpus: tech
topic: harness
type: concept
version: 2026.05
---

# Eval Harness（评测 Harness）

用于批量评测 Agent/RAG：**golden 数据集 → 运行 → 指标 → CI 门禁**。

## 指标

- 检索：recall@k、MRR
- 生成：LLM-as-judge、规则检查
- Agent：任务成功率、步数、成本

## 与本项目

`eval/golden_tech.jsonl` / `golden_interview.jsonl` + `run_eval.py` 在发布内容后回归检索质量。

## 面试

体现「质量意识」：改 prompt/知识库必须跑 eval，避免体感上线。


## 参考来源

- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
