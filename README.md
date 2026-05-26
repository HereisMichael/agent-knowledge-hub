# Agent Knowledge Hub

Agent 技术知识库（OpenClaw / Hermes Agent / Harness）+ 云厂商 SA 面试训练营（阿里云 / 腾讯云 / AWS）。

**新开对话继续开发？** 请先让 Agent 阅读 [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md)（**接续话术、已完成工作、API、环境变量、Phase 4 待办**）。Phase 2/3 与体验增强已完成。

## 功能

- **学习**：混合 RAG 问答（Chroma + BM25），带引用来源
- **刷题**：126 道结构化面试题，SM-2 间隔复习，要点解析与 AI/Demo 评分
- **模拟面试**：自由多轮 + 结构化流程（环节倒计时），PDF 报告与 Lab 推荐
- **学习进度**：题库覆盖统计 + Quiz/Mock 能力雷达图
- **实操 Lab**：8 个 2–8 小时小项目指引
- **内容治理**：staging → 自动质检 → 人工审核 → 发布 → 索引重建；支持每日定时更新

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env：LLM_API_KEY、ADMIN_API_KEY

cd ..
python scripts/seed_content.py   # 若 knowledge 为空

cd backend
uvicorn app.main:app --reload --port 8001
```

### 前端

```bash
cd web
npm install
npm run dev
```

浏览器打开 http://localhost:5174

### Docker

```bash
docker compose up --build
```

API: http://localhost:8001 · Web: http://localhost:5174

## 内容审核

1. 在「内容审核」页填入 `ADMIN_API_KEY`（与 backend `.env` 一致）
2. 「手动触发每日更新」扫描 `content/staging/`
3. 批准后写入 `knowledge/` 并**增量**重建向量索引（亦可手动「增量索引 / 全量重建」）

每日 cron 默认 06:00（`CONTENT_SCHEDULER_ENABLED=true`），可在 `.env` 关闭。

### 提交候选内容

- Markdown → `content/staging/tech/` 或 `interview/`
- 题库增量 → `content/staging/questions.patch.jsonl`

## 评测

```bash
pip install -r backend/requirements.txt
python eval/run_eval.py
```

## 可选：挂载 presales-agent 语料

```env
INGEST_EXTRA_DIRS=D:\cursor_project\presales-agent\knowledge
```

## 目录

```
agent-knowledge-hub/
├── knowledge/       # 已发布语料
├── content/         # feeds、staging、published
├── labs/            # 实操 Lab manifest
├── backend/         # FastAPI
├── web/             # React + Vite
├── eval/            # 检索 golden set
└── scripts/         # seed_content、daily_update
```

## Impeccable（前端设计 Skill）

已用推荐方式安装：

```bash
npx skills add pbakaus/impeccable
```

技能目录：

- `.agents/skills/impeccable/`（skills CLI 安装）
- `.cursor/skills/impeccable/`（Cursor 项目技能，与上一致）

在 Agent 对话中可使用 `/impeccable teach`、`/impeccable audit`、`/impeccable polish` 等命令美化 `web/` 界面。需 **Cursor Nightly** 且开启 **Settings → Rules → Agent Skills**。

## License

MIT
