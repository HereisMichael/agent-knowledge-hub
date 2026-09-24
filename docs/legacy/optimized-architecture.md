# Architecture & Operations

Technical reference for deploying and extending Agent Knowledge Hub.

## System overview

- **Web**: React SPA (Vite), proxies `/api` to the backend in development.
- **API**: FastAPI application (`backend/app/main.py`) — RAG, quiz, mock interview, labs, content admin.
- **Retrieval**: Hybrid search — Chroma vector similarity + BM25 lexical scores, merged by score.
- **Persistence**: SQLite for user progress, mock sessions, review cards, content workflow.
- **Knowledge**: Markdown under `knowledge/` with YAML front matter (`source_id`, `corpus`, `topic`).

## Public API (summary)

| Endpoint | Description |
|----------|-------------|
| `POST /api/ask` | RAG Q&A with citations |
| `GET /api/quiz/next` | Next question (filters: vendor, category, difficulty) |
| `POST /api/quiz/submit` | Submit answer; may schedule SM-2 review card |
| `GET /api/quiz/review/calendar` | Monthly review schedule |
| `POST /api/mock/sessions` | Start mock interview (free or structured) |
| `GET /api/mock/sessions/{id}/report.pdf` | Download interview report |
| `POST /api/ingest` | Rebuild index (`{ "full": true \| false }`, admin) |

Interactive schema: `http://localhost:8001/docs` when the server is running.

## Content governance

1. Contributors drop files in `content/staging/`.
2. `run-update` (manual or cron) runs rule checks + optional LLM quality report.
3. Admin approves → file copied to `knowledge/` → incremental Chroma ingest + BM25 reload.
4. Publish backups stored under `content/published/backups/` for rollback.

Staging content is **never** indexed until approved.

## Incremental indexing

- Manifest: `backend/data/ingest_manifest.json` (created at runtime, gitignored).
- Compares file mtime/size; upserts changed chunks; deletes removed files.
- Full rebuild: `POST /api/ingest` with `{ "full": true }`.

## SQLite tables

| Table | Purpose |
|-------|---------|
| `user_answers` | Quiz attempts |
| `mock_sessions` | Interview transcripts and reports |
| `review_cards` | SM-2 spaced repetition |
| `content_items` | Audit workflow state |
| `content_publish_log` | Rollback metadata |

## Structured mock interview stages

Defined in `backend/app/interview/stages.py`:

`INTRO` → `PROJECT` → `ARCH` → `PRODUCT` → `QA_USER` → `DEBRIEF`

Each stage has a suggested time budget; the API exposes `stage_timing` for the UI countdown.

## Deployment notes

- Default ports: API `8001`, Web `5174` (see `docker-compose.yml`).
- Set `LLM_API_KEY` in production for full scoring and interviewer behavior.
- Persist `backend/data/` (SQLite + Chroma) on a volume.
- Disable `CONTENT_SCHEDULER_ENABLED` if you do not want automatic staging scans.

## Evaluation

Golden sets in `eval/golden_tech.jsonl` and `eval/golden_interview.jsonl`. Run `python eval/run_eval.py` after changing retrieval or corpus.
