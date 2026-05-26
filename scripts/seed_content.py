#!/usr/bin/env python3
"""Seed knowledge markdown and interview questions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TECH_ARTICLES = {
    "openclaw/00-overview.md": {
        "source_id": "openclaw-overview-001",
        "topic": "openclaw",
        "title": "OpenClaw 概述",
        "body": """# OpenClaw 概述

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
""",
        "refs": ["https://docs.openclaw.ai", "https://github.com/openclaw/openclaw"],
    },
    "openclaw/01-gateway.md": {
        "source_id": "openclaw-gateway-001",
        "topic": "openclaw",
        "title": "Gateway 控制面",
        "body": """# OpenClaw Gateway

Gateway 是 OpenClaw 的**单一控制平面**：管理会话、渠道路由、工具调用与事件。默认监听本地端口（如 18789），把来自 IM 的消息转给 Agent Runtime。

## 职责

1. **会话管理**：隔离 workspace、多 Agent 路由
2. **通道接入**：Telegram、Discord、Slack 等
3. **工具与事件**：browser、canvas、cron、nodes

## 多 Agent 路由

可按 channel/account/peer 将流量路由到不同 workspace，实现「工作 Agent」与「私人 Agent」隔离。

## Harness 视角

Gateway 属于 **Harness 的编排层**：决定消息如何进入 loop、状态如何持久化，而非模型权重本身。
""",
        "refs": ["https://docs.openclaw.ai/gateway"],
    },
    "openclaw/02-agent-loop.md": {
        "source_id": "openclaw-agent-loop-001",
        "topic": "openclaw",
        "title": "Agent 循环（ReAct）",
        "body": """# OpenClaw Agent 循环

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
""",
        "refs": ["https://docs.openclaw.ai/concepts/agent"],
    },
    "openclaw/03-skills-mcp.md": {
        "source_id": "openclaw-skills-001",
        "topic": "openclaw",
        "title": "Skills 与 MCP",
        "body": """# Skills 与 MCP

## Skills

Skills 是目录 + `SKILL.md` 的任务说明。OpenClaw **不会**把所有 Skill 全文塞进 system prompt，而是注入**紧凑列表**（名称、描述、路径），由模型按需 `read` 相关 Skill——节省 token、减少干扰。

## MCP

Model Context Protocol 用于挂载外部工具与数据源。Harness 负责注册、描述与调用边界；模型只产出 tool call 意图。

## 最佳实践

- Skill 聚焦单一场景（如「K8s 发布检查」）
- 工具描述面向模型可读，含失败示例
- 与 Eval Harness 结合：用 golden 任务回归 Skill 变更
""",
        "refs": ["https://docs.openclaw.ai/tools/skills"],
    },
    "openclaw/04-channels-tools.md": {
        "source_id": "openclaw-channels-001",
        "topic": "openclaw",
        "title": "通道与工具",
        "body": """# 通道与一等工具

## 通道

Telegram、Slack、Discord、WhatsApp 等通过 Gateway 统一接入，用户可在手机上触发本地/VPS 上运行的 Agent。

## 一等工具

- **Browser**：自动化浏览与抓取
- **Canvas**：可视化工作区（A2UI）
- **Cron**：定时任务
- **Sessions**：子会话管理

## 安全注意

工具可访问文件与网络，生产环境需 **Policy Enforcement**（权限门）、沙箱与审计日志。
""",
        "refs": ["https://docs.openclaw.ai/tools"],
    },
    "openclaw/05-deployment.md": {
        "source_id": "openclaw-deploy-001",
        "topic": "openclaw",
        "title": "部署与安全",
        "body": """# 部署与安全边界

## 部署选项

- 本机 macOS/Linux；Windows 建议 WSL2
- VPS 常开：适合 Telegram 远程触发
- `openclaw onboard` 向导配置 Gateway、渠道、Skills

## 数据边界

- BYOM：可接 Ollama 离线模型
- 密钥存本地配置，勿提交仓库
- 无默认遥测；企业场景仍需自审工具权限

## SA 面试场景

客户问「能否私有化 IM 助手」：答 OpenClaw 类架构 = 自建 Gateway + 内网 LLM + 审计。
""",
        "refs": ["https://docs.openclaw.ai/start/wizard"],
    },
    "hermes/00-overview.md": {
        "source_id": "hermes-overview-001",
        "topic": "hermes",
        "title": "Hermes Agent 概述",
        "body": """# Hermes Agent 概述

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
""",
        "refs": ["https://hermes-agent.nousresearch.com", "https://github.com/NousResearch/hermes-agent"],
    },
    "hermes/01-memory-skills.md": {
        "source_id": "hermes-memory-001",
        "topic": "hermes",
        "title": "记忆与 Skills",
        "body": """# 持久记忆与 Skills 系统

## 记忆

Hermes 将重要信息写入持久存储，新会话无需重复背景。适合健康追踪、长期项目运维等场景。

## Skills

- 兼容 agentskills.io 思路
- 复杂任务完成后可保存为 Skill 供 `call`
- 使用中遇错可 **更新 Skill**（自改进）

## Harness 视角

记忆管理属于 **Context Lifecycle**；Skill 库属于 **Context Delivery**（按需加载能力描述）。
""",
        "refs": ["https://hermes-agent.nousresearch.com"],
    },
    "hermes/02-gateway-platforms.md": {
        "source_id": "hermes-gateway-001",
        "topic": "hermes",
        "title": "Gateway 与多平台",
        "body": """# Hermes Gateway

单进程 Gateway 连接多 IM 平台，支持 **跨端续聊**（Telegram 开始、CLI 继续）。

## 配置

`hermes setup` 交互配置渠道与模型；可 systemd 常驻。

## 与售前场景

销售/SA 在外场用手机提问，Agent 在服务器执行查文档、跑脚本，结果推回 IM。
""",
        "refs": ["https://github.com/NousResearch/hermes-agent"],
    },
    "hermes/03-subagents-cron.md": {
        "source_id": "hermes-subagents-001",
        "topic": "hermes",
        "title": "子 Agent 与 Cron",
        "body": """# 子 Agent 与定时任务

## 子 Agent

隔离会话与终端，并行多工作流；可通过 RPC 将多步流水线折叠为低上下文成本调用。

## Cron

自然语言创建定时任务：日报、备份巡检、周报摘要，结果投递到任意渠道。

## 编排

属于 Harness **Task Runners & Orchestration** 能力在企业助手场景的落地。
""",
        "refs": ["https://hermes-agent.nousresearch.com"],
    },
    "hermes/04-sandbox-tools.md": {
        "source_id": "hermes-sandbox-001",
        "topic": "hermes",
        "title": "沙箱与工具",
        "body": """# 沙箱与工具注册表

Hermes 支持多种执行后端：本地、Docker、SSH、Singularity、Modal 等，并强调容器加固。

## 工具

40+ 内置工具 + MCP；通过 registry.register 扩展，在 toolsets 中启用。

## 安全

SA 面试常问：生产 Agent 如何防越权？答 **Policy + Sandbox + 最小权限工具集**。
""",
        "refs": ["https://github.com/NousResearch/hermes-agent"],
    },
    "hermes/05-setup.md": {
        "source_id": "hermes-setup-001",
        "topic": "hermes",
        "title": "安装与配置",
        "body": """# 安装与配置

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup
```

支持 Linux/macOS/WSL2。MIT 协议。

## 实操 Lab 建议

在 VPS 部署 Gateway + Telegram，完成一次「会议纪要总结」并写入记忆。
""",
        "refs": ["https://hermes-agent.nousresearch.com"],
    },
    "harness/00-what-is-harness.md": {
        "source_id": "harness-what-001",
        "topic": "harness",
        "title": "什么是 Agent Harness",
        "body": """# 什么是 Agent Harness

**Agent = Model + Harness**。模型提供推理能力；Harness 是模型之外的一切：状态、工具执行、反馈循环、约束。

## 关键结论

- **模型不执行工具**：只产生 tool call；Harness 执行并回填结果
- **Harness 常比换模型更影响效果**：上下文、工具 API 设计、停止条件

## 组件清单

System prompt、Tools/Skills/MCP、沙箱、编排（子 Agent）、Hooks（compaction、lint、重试）、Eval。

OpenClaw/Hermes 的 Gateway+Runtime 都是 Harness 的具体实现。
""",
        "refs": ["https://www.langchain.com/blog/the-anatomy-of-an-agent-harness"],
    },
    "harness/01-five-pillars.md": {
        "source_id": "harness-five-pillars-001",
        "topic": "harness",
        "title": "Harness 五支柱",
        "body": """# Harness 五支柱

| # | 支柱 | 保证 |
|---|------|------|
| 1 | Context Assembly | 每次调用 token 效用最大化 |
| 2 | Tool Integrity | schema 校验、可行动错误信息 |
| 3 | Loop Discipline | 显式 continue/retry/stop |
| 4 | Policy Enforcement | 副作用前权限门 |
| 5 | Context Lifecycle | 窗口当有限资源主动管理 |

缺任一支柱，多步任务易失控：幻觉工具调用、死循环、越权、上下文淹没。
""",
        "refs": ["https://github.com/All-The-Vibes/Agent-Harness"],
    },
    "harness/02-harness-components.md": {
        "source_id": "harness-components-001",
        "topic": "harness",
        "title": "Harness 组件",
        "body": """# Harness 组件详解

## System Prompts

定义角色、输出格式、工具使用规范。

## Tools / Skills / MCP

工具描述质量决定调用成功率；应用「面向模型的 API 设计」。

## 编排

子 Agent、handoff、模型路由（强模型规划、弱模型执行）。

## Hooks

确定性逻辑：compaction、测试钩子、Ralph Loop（完成后注入继续信号）。

##  bundled 基础设施

文件系统、浏览器、代码沙箱——Agent 的「手脚」。
""",
        "refs": ["https://www.langchain.com/blog/the-anatomy-of-an-agent-harness"],
    },
    "harness/03-agent-loop.md": {
        "source_id": "harness-agent-loop-001",
        "topic": "harness",
        "title": "Agent Loop 对照",
        "body": """# Agent Loop 对照

通用循环：

1. Harness 组装 prompt
2. 调用模型
3. 若 tool call → Harness 执行 → 结果回填
4. 直至 stop 或达 max steps

## OpenClaw / Hermes

二者均实现 ReAct，差异在记忆策略、Skill 进化、沙箱与渠道集成深度。

## SA 面试

客户问「智能售前助手」：答 **RAG + Harness（HITL 门 + 合规规则）+ 专用 Agent**，而非裸 ChatGPT。
""",
        "refs": ["https://docs.openclaw.ai/concepts/agent"],
    },
    "harness/04-eval-harness.md": {
        "source_id": "harness-eval-001",
        "topic": "harness",
        "title": "Eval Harness",
        "body": """# Eval Harness（评测 Harness）

用于批量评测 Agent/RAG：**golden 数据集 → 运行 → 指标 → CI 门禁**。

## 指标

- 检索：recall@k、MRR
- 生成：LLM-as-judge、规则检查
- Agent：任务成功率、步数、成本

## 与本项目

`eval/golden_tech.jsonl` / `golden_interview.jsonl` + `run_eval.py` 在发布内容后回归检索质量。

## 面试

体现「质量意识」：改 prompt/知识库必须跑 eval，避免体感上线。
""",
        "refs": ["https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents"],
    },
    "compare/openclaw-vs-hermes.md": {
        "source_id": "compare-oc-hermes-001",
        "topic": "compare",
        "title": "OpenClaw vs Hermes",
        "body": """# OpenClaw vs Hermes 选型

- **选 OpenClaw**：强调本地个人助手、Canvas、多渠道、Skills 按需加载、社区插件
- **选 Hermes**：强调服务器常驻、记忆与 Skill 自进化、子 Agent/Cron、多沙箱后端

二者都可作为学习 **Harness 工程** 的样本代码库。
""",
        "refs": ["https://docs.openclaw.ai", "https://hermes-agent.nousresearch.com"],
    },
    "compare/where-harness-lives.md": {
        "source_id": "compare-harness-loc-001",
        "topic": "compare",
        "title": "Harness 在哪里",
        "body": """# Harness 在架构中的位置

```
User → Channel → Gateway → [Harness: 上下文/工具/策略/循环] → LLM
```

OpenClaw Gateway、Hermes Gateway、本项目的 FastAPI 编排（Quiz/Mock/RAG）都是 Harness 的不同产品形态。
""",
        "refs": ["https://www.langchain.com/blog/the-anatomy-of-an-agent-harness"],
    },
    "glossary/glossary.md": {
        "source_id": "glossary-agent-001",
        "topic": "glossary",
        "title": "术语表",
        "body": """# Agent 术语表

- **Gateway**：消息与会话控制面
- **Skill**：任务级指令包（常含 SKILL.md）
- **MCP**：模型上下文协议，标准化工具接入
- **ReAct**：推理与行动交替的 Agent 循环
- **Harness**：围绕模型的编排与治理层
- **Eval Harness**：自动化评测与 CI 门禁
- **RAG**：检索增强生成
""",
        "refs": ["https://github.com/ai-boost/awesome-harness-engineering"],
    },
    "interview/guides/architecture-interview.md": {
        "source_id": "interview-guide-arch-001",
        "corpus": "interview",
        "topic": "interview",
        "title": "架构题面试攻略",
        "body": """# 架构题面试攻略（云 SA）

## 答题结构（5 步）

1. 澄清业务：用户量、合规、预算、地域
2. 非功能需求：可用性、RPO/RTO、扩展性
3. 逻辑架构：接入层 / 应用层 / 数据层 / 安全层
4. 物理映射：具体云产品（SLB、ECS/ACK、RDS、OSS、WAF）
5. 风险与演进：单点、成本、运维、迁移

## 画图要点

- 标注流量方向与协议
- 多 AZ / 主备 / 只读副本
- 等保/个保合规组件

## 反问

项目阶段、上线时间、现有 IDC 资产、招标评分权重。
""",
        "refs": ["https://help.aliyun.com/"],
    },
    "interview/vendors/slb-compare.md": {
        "source_id": "interview-vendor-slb-001",
        "corpus": "interview",
        "topic": "interview",
        "title": "三厂商负载均衡对照",
        "body": """# 负载均衡产品对照

| 能力 | 阿里云 | 腾讯云 | AWS |
|------|--------|--------|-----|
| 七层 LB | ALB | CLB(七层) | ALB |
| 四层 LB | NLB/SLB | CLB | NLB |
| 全球加速 | GA | GAAP | Global Accelerator |

面试时先问 **HTTP vs TCP、健康检查、会话保持、QUIC** 需求，再映射产品。
""",
        "refs": ["https://aws.amazon.com/elasticloadbalancing/", "https://www.alibabacloud.com/product/slb"],
    },
}


def write_md(rel: str, meta: dict) -> None:
    refs = meta.get("refs", [])
    ref_block = "\n".join(f"- {u}" for u in refs)
    fm = {
        "source_id": meta["source_id"],
        "corpus": meta.get("corpus", "tech"),
        "topic": meta["topic"],
        "type": "concept",
        "version": "2026.05",
    }
    lines = [f"{k}: {v}" for k, v in fm.items()]
    front = "\n".join(lines)
    content = f"---\n{front}\n---\n\n{meta['body']}\n\n## 参考来源\n\n{ref_block}\n"
    path = ROOT / "knowledge" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def seed_questions() -> None:
    vendors = [("aliyun", "阿里云"), ("tencent", "腾讯云"), ("aws", "AWS")]
    templates = [
        ("architecture", "ha", "为 {v} 设计互联网医院 {n} 万并发架构，含多 AZ 与等保三级。"),
        ("architecture", "dr", "{v} 上数据库 RPO/RTO 如何设计？说明备份与切换。"),
        ("architecture", "micro", "{v} 微服务从单体迁移，如何拆分边界与治理？"),
        ("architecture", "data", "{v} 数据湖与数仓一体架构如何选型？"),
        ("architecture", "edge", "{v} 边缘节点 + 中心云混合架构如何设计？"),
        ("architecture", "cost", "{v} 架构降本 30% 可从哪些层入手？"),
        ("product", "compute", "对比 {v} ECS/虚拟机与容器服务在医教场景的选型。"),
        ("product", "network", "{v} SLB 与 CDN 如何抗突发流量？"),
        ("product", "security", "等保三级在 {v} 需要哪些安全组件？"),
        ("product", "storage", "{v} 对象存储与块存储在备份场景如何搭配？"),
        ("product", "db", "{v} 关系库 vs NoSQL 在订单系统的取舍？"),
        ("product", "obs", "{v} 可观测性（日志/指标/链路）产品如何落地？"),
        ("behavior", "star", "用 STAR 描述你在 {v} 项目中的技术异议处理。"),
        ("behavior", "conflict", "客户坚持错误方案，你如何在 {v} 项目中沟通？"),
        ("behavior", "stakeholder", "多部门需求冲突时，你在 {v} 项目如何排优先级？"),
        ("behavior", "mentor", "如何带初级 SA 在 {v} 项目中成长？"),
        ("solution", "bid", "{v} 投标 99.95% SLA 如何响应？"),
        ("solution", "compete", "{v} 与竞品同时 POC，如何做差异化？"),
        ("solution", "migration", "{v} IDC 迁云分阶段方案如何设计？"),
        ("solution", "finops", "{v} FinOps 与资源标签治理如何推行？"),
        ("agent", "rag", "如何用 RAG+Harness 提升 {v} 售前效率？"),
        ("agent", "eval", "在 {v} 客户场景如何设计 Agent 评测门禁？"),
        ("agent", "mcp", "{v} 私有化场景 MCP 工具安全边界如何划定？"),
    ]
    extra_arch = [
        "为 {v} 设计跨区域灾备与流量调度方案。",
        "{v} 多租户 SaaS 隔离与配额如何设计？",
        "{v} 零信任接入企业内网应用如何落地？",
        "{v} 大促峰值 10 倍流量弹性架构怎么画？",
        "{v} 视频直播低延迟链路如何选型？",
        "{v} 混合云专线与 VPN 备份链路如何设计？",
        "{v} 敏感数据分级与 KMS 密钥轮换方案？",
        "{v} Serverless 事件驱动批处理架构示例？",
        "{v} 全球化合规（GDPR/个保）数据驻留方案？",
        "{v} 成本可观测的架构评审清单有哪些？",
        "{v} 核心交易双活 vs 主备如何决策？",
        "{v} 消息队列削峰填谷在订单场景的用法？",
        "{v} 灰度发布与金丝雀在 {v} 上的实践？",
        "{v} 混沌工程在云上如何小步试点？",
        "{v} 遗留 Oracle 迁 {v} 托管库的路径？",
        "{v} AI 推理服务 GPU 弹性与队列如何设计？",
        "{v} 物联网百万设备接入 {v} 的架构要点？",
    ]
    questions = []
    per_vendor_target = 42
    for vendor, vname in vendors:
        n = 0
        for cat, sub, tmpl in templates:
            n += 1
            questions.append(_make_q(vendor, vname, cat, sub, n, tmpl))
        idx = 0
        while sum(1 for q in questions if q["vendor"] == vendor) < per_vendor_target:
            idx += 1
            tmpl = extra_arch[(idx - 1) % len(extra_arch)]
            n = sum(1 for q in questions if q["vendor"] == vendor) + 1
            questions.append(
                _make_q(
                    vendor,
                    vname,
                    "architecture",
                    "general",
                    n,
                    tmpl,
                    key_points=["多 Region", "DNS/GTM", "数据同步", "演练"],
                )
            )
    path = ROOT / "knowledge" / "interview" / "questions.jsonl"
    path.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} questions ({per_vendor_target} per vendor)")


def _make_q(
    vendor: str,
    vname: str,
    cat: str,
    sub: str,
    n: int,
    tmpl: str,
    key_points: list[str] | None = None,
) -> dict:
    return {
        "id": f"{vendor}-sa-{cat}-{n:03d}",
        "vendor": vendor,
        "category": cat,
        "subcategory": sub,
        "difficulty": 2 + (n % 3),
        "question": tmpl.format(v=vname, n=3 + n % 5),
        "key_points": key_points or ["场景澄清", "分层架构", "高可用", "安全合规", "成本SLA"],
        "rubric": {
            "structure": 20,
            "depth": 30,
            "tradeoff": 25,
            "compliance": 15,
            "communication": 10,
        },
        "follow_ups": ["量化指标？", "预算？"],
        "related_source_ids": ["harness-five-pillars-001", "interview-guide-arch-001"],
        "tags": ["sa", vendor],
        "source_note": "synthetic",
    }


def main() -> None:
    for rel, meta in TECH_ARTICLES.items():
        write_md(rel, meta)
    seed_questions()
    print(f"Wrote {len(TECH_ARTICLES)} markdown articles")


if __name__ == "__main__":
    main()
