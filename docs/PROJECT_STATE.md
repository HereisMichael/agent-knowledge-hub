# Agent Knowledge Hub — 项目接续文档

> **最后更新**：2026-05-27  
> **用途**：新开 Cursor 对话时复制「接续话术」给 Agent，快速恢复上下文。  
> **项目路径**：`d:\cursor_project\agent-knowledge-hub`  
> **约束**：**不要修改**同目录下的 `presales-agent`（可选只读挂载语料）。

---

## 0. 给下一会话的接续话术（复制即用）

```
请阅读 d:\cursor_project\agent-knowledge-hub\docs\PROJECT_STATE.md 和 README.md，
在 agent-knowledge-hub 项目上继续开发。不要改 presales-agent。

当前进度：Phase 2/3 与体验增强已完成（126 题、Mock 报告 UI、复习日历、Chroma 增量 ingest）。
测试：backend 下 pytest tests/test_smoke.py 应为 9 passed。

我下一步想做：[在这里写你的需求]
```

---

## 1. 项目是什么

独立全栈：**Agent 技术知识库** + **云 SA 面试训练营**（阿里云 / 腾讯云 / AWS）+ **内容治理（staging → 审核 → 发布）**。

| 能力 | 状态 |
|------|------|
| 技术知识库 RAG（OpenClaw / Hermes / Harness） | ✅ 22 篇 Markdown |
| 面试题库 JSONL | ✅ **126 题**（每厂商 42） |
| RAG 问答 + 引用 | ✅ Chroma + BM25 混合检索 |
| 刷题 Quiz + AI/Demo 评分 | ✅ |
| SM-2 间隔复习 | ✅ 错题入卡 + 刷题页复习 + **进度页月历** |
| 模拟面试 Mock | ✅ 自由 / 结构化 + **环节倒计时** |
| Mock 报告 | ✅ **可视化 UI** + PDF 下载 |
| 进度雷达 | ✅ Quiz 覆盖 % + Mock 维度均分 |
| 实操 Lab | ✅ 8 个 + 推荐 |
| 内容治理 | ✅ staging → 审核 → 发布 |
| 发布回滚 | ✅ `content_publish_log` + 管理端一键回滚 |
| Extra 语料 diff | ✅ `INGEST_EXTRA_DIRS` → staging 待审 |
| 高置信自动发布 | ✅ `AUTO_PUBLISH_TRUSTED` + `AUTO_PUBLISH_MIN_SCORE` |
| Chroma **增量** ingest | ✅ manifest，默认增量；可全量 |
| 每日定时更新 | ✅ APScheduler 06:00（可关） |
| 前端 Impeccable 风格 | ✅ 侧栏 + OKLCH |

---

## 2. 开发历程摘要（按会话）

### 会话 A — Phase 2/3 主功能

1. **题库扩量**：`scripts/seed_content.py` → 126 题（`per_vendor_target = 42`）
2. **Mock 结构化倒计时**：`interview/stages.py` + `stage_timing` API + `Mock.tsx` 环节条/倒计时
3. **SM-2**：`interview/review.py` + `review_cards` 表 + `/api/quiz/review/*`
4. **进度雷达**：`progress/radar.py` + `RadarChart.tsx` + `/api/progress/radar`
5. **Extra diff**：`content/extra_diff.py`，每日更新时扫描 `INGEST_EXTRA_DIRS`
6. **发布回滚**：`content/rollback.py` + `content_publish_log` + 内容审核页
7. **Mock PDF**：`reports/pdf.py`（无第三方依赖的简易 PDF）
8. **自动发布**：`daily_update.py` 中 `_maybe_auto_publish`

### 会话 B — 体验增强

1. **Mock 报告 UI**：`web/src/components/MockReport.tsx`（维度条、亮点/缺口、Lab、PDF）
2. **复习日历**：`GET /api/quiz/review/calendar` + `ReviewCalendar.tsx`（进度页）
3. **Chroma 增量 ingest**：`rag/ingest.py` 重写；manifest `backend/data/ingest_manifest.json`；`POST /api/ingest` body `{ full: bool }`；内容审核页「增量/全量索引」

### 验证记录

- `pytest tests/test_smoke.py`：**9 passed**
- 本地运行：后端 `http://127.0.0.1:8001`，前端 `http://127.0.0.1:5174`
- `/api/health` 示例：`questions: 126`, `sources: 22`, `demo_mode: true`（无 LLM key 时）

---

## 3. 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11, FastAPI, SQLite, Chroma, rank-bm25, APScheduler |
| 前端 | React 18, Vite 5, TypeScript（无图表库，雷达/日历为 SVG+CSS） |
| LLM | OpenAI 兼容 API（默认 `composer-2.5`）；无 key → **Demo 模式** |
| 设计 | Impeccable → `PRODUCT.md` + `DESIGN.md` + `web/src/index.css` |

---

## 4. 目录结构（含新增文件）

```
agent-knowledge-hub/
├── knowledge/                         # 已发布 RAG 语料（ingest 主目录）
│   ├── openclaw/ hermes/ harness/ compare/ glossary/
│   └── interview/questions.jsonl      # 126 题
├── content/
│   ├── staging/tech|interview/        # 待审（gitignore）
│   └── published/backups/             # 发布前备份（回滚用）
├── backend/
│   ├── data/
│   │   ├── hub.db                     # SQLite（gitignore）
│   │   ├── chroma/                    # 向量库（gitignore）
│   │   └── ingest_manifest.json       # 增量 ingest 状态（gitignore）
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── rag/ingest.py              # 全量 + 增量 ingest
│       ├── rag/retriever.py
│       ├── interview/
│       │   ├── stages.py              # 结构化环节时长/文案
│       │   ├── mock.py
│       │   ├── review.py              # SM-2 + calendar
│       │   ├── quiz.py
│       │   └── questions.py
│       ├── progress/radar.py
│       ├── content/
│       │   ├── audit.py
│       │   ├── publish.py
│       │   ├── daily_update.py
│       │   ├── extra_diff.py
│       │   └── rollback.py
│       ├── reports/pdf.py
│       └── db/store.py
├── web/src/
│   ├── pages/                         # Learn, Quiz, Mock, Labs, Progress, ContentReview
│   └── components/
│       ├── MockReport.tsx
│       ├── RadarChart.tsx
│       └── ReviewCalendar.tsx
├── scripts/seed_content.py
├── eval/run_eval.py
├── docs/PROJECT_STATE.md              # ← 本文件
└── tests/test_smoke.py                # 9 个冒烟测试
```

---

## 5. 本地启动（Windows）

```powershell
# 终端 1 — 后端
cd d:\cursor_project\agent-knowledge-hub\backend
# 首次：copy .env.example .env
$env:KNOWLEDGE_PATH="d:\cursor_project\agent-knowledge-hub\knowledge"
$env:PROJECT_ROOT="d:\cursor_project\agent-knowledge-hub"
$env:CONTENT_ROOT="d:\cursor_project\agent-knowledge-hub\content"
$env:CONTENT_SCHEDULER_ENABLED="false"   # 开发时可关 cron
$env:DEMO_MODE="true"                      # 或无 LLM_API_KEY 即 Demo
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# 终端 2 — 前端
cd d:\cursor_project\agent-knowledge-hub\web
npm run dev
```

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:5174 | 前端（Vite 代理 `/api` → 8001） |
| http://127.0.0.1:8001/docs | OpenAPI |
| http://127.0.0.1:8001/api/health | 健康检查 |

**重建语料**（knowledge 为空或需重置题库）：

```powershell
python d:\cursor_project\agent-knowledge-hub\scripts\seed_content.py
# 然后管理端或 API 全量索引：POST /api/ingest {"full": true}
```

---

## 6. 环境变量（`backend/.env`）

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | 空 → Demo 模式（规则评分/模拟面试官） |
| `KNOWLEDGE_PATH` | 默认 `../knowledge` |
| `INGEST_EXTRA_DIRS` | 逗号分隔路径；变更会 diff 到 staging（见 `extra_diff.py`） |
| `ADMIN_API_KEY` | 管理 API Header `X-Admin-Key` |
| `CONTENT_SCHEDULER_ENABLED` | `false` 关闭每日 06:00 任务 |
| `AUTO_PUBLISH_TRUSTED` | `true` 时高置信自动发布 |
| `AUTO_PUBLISH_MIN_SCORE` | 默认 `85` |
| `CHROMA_PATH` / `SQLITE_PATH` | 默认 `./data/chroma`、`./data/hub.db` |

---

## 7. API 速查

### 公开

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 状态、题量、sources、demo_mode |
| POST | `/api/ask` | RAG 问答 `{ question, corpus, top_k }` |
| GET | `/api/quiz/next` | 下一题 |
| POST | `/api/quiz/submit` | 提交；低分自动入复习卡 |
| GET | `/api/quiz/review/due` | 到期复习列表 |
| POST | `/api/quiz/review/grade` | SM-2 打分 `{ question_id, quality: 0-5 }` |
| GET | `/api/quiz/review/calendar` | `?year=&month=` 月历聚合 |
| GET | `/api/progress/radar` | Quiz/Mock 雷达数据 |
| POST | `/api/mock/sessions` | 创建；结构化返回 `stage_timing` |
| POST | `/api/mock/sessions/{id}/message` | 对话 |
| POST | `/api/mock/sessions/{id}/finish` | 生成 report |
| GET | `/api/mock/sessions/{id}/report.pdf` | PDF 下载 |

### 管理（`X-Admin-Key`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ingest` | `{ "full": false }` 增量（默认）或全量 |
| POST | `/api/admin/content/run-update` | 每日更新 + extra diff |
| POST | `/api/admin/content/{id}/approve` | 发布 → 增量 ingest |
| POST | `/api/admin/content/rollback/{log_id}` | 从备份回滚 |
| GET | `/api/admin/content/publish-logs` | 可回滚记录 |

---

## 8. 数据模型（SQLite `hub.db`）

| 表 | 用途 |
|----|------|
| `user_answers` | 刷题记录 |
| `mock_sessions` | 面试 transcript / report；`stage_started_at` |
| `review_cards` | SM-2：easiness, interval_days, next_review_at |
| `content_items` | 审核状态机 |
| `content_publish_log` | 发布备份路径，供回滚 |
| `content_runs` / `content_changelog` | 任务日志 / 前端「最近发布」 |
| `lab_completions` | Lab 打卡 |

---

## 9. 关键实现说明

### 增量 ingest

- 文件：`backend/app/rag/ingest.py`
- 按 **文件绝对路径 + mtime** 判断变更；删除文件会删对应 Chroma chunk
- Manifest：`Path(chroma_path).parent / ingest_manifest.json`
- 发布/回滚/启动：`ingest_knowledge(full=False)`；有变更才 `reload_bm25()`
- BM25 仍为全目录重载（未做按文件局部更新）

### Mock 结构化

- 环节定义：`interview/stages.py`（INTRO 5min → ARCH 15min …）
- 倒计时：前端每秒递减 + 接口 `stage_timing.remaining_sec` 校准
- 推进：模型回复含 `[NEXT_STAGE]` 或架构环节手动说「下一环节」

### SM-2

- 入卡：Quiz 得分 < 70（`interview/review.py` → `schedule_after_quiz`）
- 日历：逾期卡归并到「今天」格子（`review_calendar`）

---

## 10. 测试

```powershell
cd d:\cursor_project\agent-knowledge-hub\backend
$env:KNOWLEDGE_PATH="d:\cursor_project\agent-knowledge-hub\knowledge"
$env:SQLITE_PATH="d:\cursor_project\agent-knowledge-hub\backend\data\test_hub.db"
$env:CHROMA_PATH="d:\cursor_project\agent-knowledge-hub\backend\data\chroma_test"
$env:PROJECT_ROOT="d:\cursor_project\agent-knowledge-hub"
$env:CONTENT_ROOT="d:\cursor_project\agent-knowledge-hub\content"
$env:DEMO_MODE="true"
$env:CONTENT_SCHEDULER_ENABLED="false"
$env:ADMIN_API_KEY="change-me-admin-key"
.\.venv\Scripts\python -m pytest tests\test_smoke.py -q
```

**当前：9 passed**（health, ask, quiz, mock, structured timing, radar, ingest incremental, review calendar, review flow）

---

## 11. 已知限制

- Demo 模式下 Quiz/Mock 评分为规则估算，需配置 `LLM_API_KEY` 才有完整 LLM 反馈
- `daily_update` 每次 run 可能对 staging 重复登记 content_item（未按 path 去重）
- PDF 报告为单页简易排版，中文长文可能截断
- 复习日历点击日期暂不能展开当日题目列表（仅显示数量）
- Docker 未在本会话验证；`docker-compose.yml` 端口 8001 / 5174

---

## 12. 后续计划（Phase 4+，未做）

按优先级建议：

### P1 — 质量与数据

- [ ] **题库质量**：126 题为 synthetic 模板生成，需人工润色或接入真实面经
- [ ] **daily_update 去重**：同一 `source_path` 已 pending 时不再新建 item
- [ ] **eval 回归**：扩 golden set，CI 跑 `eval/run_eval.py`
- [ ] **配置 LLM**：`.env` 填 `LLM_API_KEY` 后验证 Mock/Quiz 完整链路

### P2 — 体验

- [ ] **复习日历**：点击日期展示当日卡片 + 跳转刷题
- [ ] **Mock 报告**：历史会话列表、对比两次面试分数
- [ ] **BM25 增量**：`retriever.reload_bm25()` 仅重载变更文件
- [ ] **错题本页面**：独立 Tab，与 SM-2 打通

### P3 — 平台

- [ ] **多用户**：`user_id` 从前端登录态传入（现为 `default`）
- [ ] **Docker / 部署**：生产 env、持久卷、健康检查
- [ ] **presales 语料**：配置 `INGEST_EXTRA_DIRS` 并验证 diff → 审核 → 发布闭环
- [ ] **通知**：复习到期提醒（邮件/本地推送）

### P4 — 可选增强

- [ ] 结构化 Mock：超时自动 `[NEXT_STAGE]` 或提醒
- [ ] 报告 PDF 美化（fpdf2 / HTML→PDF）
- [ ] 题库按标签/难度智能出题（避免重复）
- [ ] 技术文档增量：RSS/feed 自动拉取（`feeds.yaml` 仅 local_seed）

---

## 13. 与 presales-agent

- **不合并代码库**
- 可选：`INGEST_EXTRA_DIRS=D:\cursor_project\presales-agent\knowledge` 作为第二 RAG 源；变更进入 **staging 审核**，不直接进生产索引

---

## 14. 原始产品目标（备忘）

- Agent 知识 + 云 SA 面试训练营 + 内容每日更新与审核
- 厂商：阿里云、腾讯云、AWS
- 模拟面试：自由 + 结构化全流程

---

*维护约定：完成功能后更新 §1 表格、§2 历程、§12 待办，并跑 pytest 更新 §10 通过数。*
