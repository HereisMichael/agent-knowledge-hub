---
source_id: openclaw-skills-001
corpus: tech
topic: openclaw
type: concept
version: 2026.05
---

# Skills 与 MCP

## Skills

Skills 是目录 + `SKILL.md` 的任务说明。OpenClaw **不会**把所有 Skill 全文塞进 system prompt，而是注入**紧凑列表**（名称、描述、路径），由模型按需 `read` 相关 Skill——节省 token、减少干扰。

## MCP

Model Context Protocol 用于挂载外部工具与数据源。Harness 负责注册、描述与调用边界；模型只产出 tool call 意图。

## 最佳实践

- Skill 聚焦单一场景（如「K8s 发布检查」）
- 工具描述面向模型可读，含失败示例
- 与 Eval Harness 结合：用 golden 任务回归 Skill 变更


## 参考来源

- https://docs.openclaw.ai/tools/skills
