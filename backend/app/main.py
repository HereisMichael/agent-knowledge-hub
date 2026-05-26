from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.content.daily_update import run_daily_update
from app.content.publish import publish_item, reject_item
from app.content.rollback import list_publish_logs, rollback_publish
from app.db import store
from app.interview import mock as mock_svc
from app.interview import review as review_svc
from app.interview.quiz import build_explanation, next_question, score_answer_ai
from app.interview.questions import get_question, load_questions, questions_by_vendor
from app.progress.radar import build_radar
from app.reports.pdf import build_mock_report_pdf
from app.labs.recommend import load_manifest, recommend_labs
from app.qa import service as qa_svc
from app.rag.ingest import ingest_knowledge, ingest_knowledge_incremental
from app.rag.knowledge_lookup import get_by_source_id, list_source_ids
from app.scheduler.jobs import start_scheduler, stop_scheduler


def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> None:
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(401, "Invalid or missing X-Admin-Key")


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    try:
        ingest_knowledge_incremental()
        qa_svc.get_retriever()
    except Exception as e:
        print(f"[warn] ingest skipped: {e}")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Agent Knowledge Hub API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskBody(BaseModel):
    question: str
    corpus: str = "all"
    top_k: int = 6


class SearchBody(BaseModel):
    query: str
    corpus: str = "all"
    top_k: int = 6


class QuizSubmitBody(BaseModel):
    question_id: str
    answer_text: str
    self_score: int | None = None
    user_id: str = "default"
    use_ai: bool = True


class MockCreateBody(BaseModel):
    mode: str = "free"
    vendor: str = "aliyun"
    focus: str = "architecture"
    user_id: str = "default"


class MockMessageBody(BaseModel):
    message: str
    want_hint: bool = False


class LabCompleteBody(BaseModel):
    notes: str = ""
    user_id: str = "default"


class RejectBody(BaseModel):
    note: str = ""


class ReviewGradeBody(BaseModel):
    question_id: str
    quality: int = Field(ge=0, le=5)
    user_id: str = "default"


class IngestBody(BaseModel):
    full: bool = False


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": settings.llm_model,
        "demo_mode": settings.use_demo_llm,
        "questions": len(load_questions()),
        "sources": len(list_source_ids()),
    }


@app.post("/api/ingest")
def api_ingest(body: IngestBody = IngestBody(), _: None = Depends(require_admin)):
    result = ingest_knowledge(full=body.full)
    if (
        body.full
        or result.get("files_processed", 0) > 0
        or result.get("files_removed", 0) > 0
    ):
        qa_svc.get_retriever().reload_bm25()
    return result


@app.post("/api/ask")
def api_ask(body: AskBody):
    return qa_svc.ask(body.question, corpus=body.corpus, top_k=body.top_k)


@app.post("/api/search")
def api_search(body: SearchBody):
    chunks = qa_svc.get_retriever().search(body.query, top_k=body.top_k, corpus=None if body.corpus == "all" else body.corpus)
    return {
        "results": [
            {"source_id": c.source_id, "text": c.text, "score": c.score, "path": c.path, "corpus": c.corpus}
            for c in chunks
        ]
    }


@app.get("/api/sources")
def api_sources(corpus: str | None = None):
    return {"source_ids": list_source_ids(corpus)}


@app.get("/api/sources/{source_id}")
def api_source(source_id: str):
    doc = get_by_source_id(source_id)
    if not doc:
        raise HTTPException(404, "source not found")
    return doc


@app.get("/api/content/feed")
def content_feed(limit: int = 20):
    return {"items": store.get_content_feed(limit)}


@app.get("/api/quiz/next")
def quiz_next(
    vendor: str | None = None,
    category: str | None = None,
    difficulty: int | None = None,
):
    result = next_question(vendor=vendor, category=category, difficulty=difficulty)
    if not result:
        raise HTTPException(404, "no matching question")
    return result


@app.post("/api/quiz/submit")
def quiz_submit(body: QuizSubmitBody):
    q = get_question(body.question_id)
    if not q:
        raise HTTPException(404, "question not found")
    ai_result = score_answer_ai(q, body.answer_text) if body.use_ai else {}
    store.save_quiz_answer(
        body.user_id,
        body.question_id,
        body.answer_text,
        body.self_score,
        ai_result.get("ai_score"),
    )
    score = ai_result.get("ai_score") or body.self_score
    review_card = review_svc.schedule_after_quiz(body.user_id, body.question_id, score)
    return {
        "question": q,
        "explanation": build_explanation(q),
        "review_scheduled": review_card is not None,
        **ai_result,
    }


@app.get("/api/quiz/wrong-book")
def quiz_wrong_book(user_id: str = "default"):
    return {"items": store.get_wrong_book(user_id)}


@app.get("/api/quiz/stats")
def quiz_stats(user_id: str = "default"):
    return {
        **store.quiz_stats(user_id),
        "by_vendor": questions_by_vendor(),
        "review": review_svc.review_stats(user_id),
    }


@app.get("/api/quiz/review/due")
def quiz_review_due(user_id: str = "default", limit: int = 10):
    due = review_svc.due_reviews(user_id, limit=limit)
    items = []
    for card in due:
        q = get_question(card["question_id"])
        if q:
            items.append({"card": card, "question": q})
    return {"items": items}


@app.post("/api/quiz/review/grade")
def quiz_review_grade(body: ReviewGradeBody):
    try:
        card = review_svc.grade_review(body.user_id, body.question_id, body.quality)
    except KeyError:
        raise HTTPException(404, "review card not found")
    return {"card": card}


@app.get("/api/quiz/review/calendar")
def quiz_review_calendar(
    user_id: str = "default",
    year: int | None = None,
    month: int | None = None,
):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(400, "month must be 1-12")
    return review_svc.review_calendar(user_id, y, m)


@app.get("/api/progress/radar")
def progress_radar(user_id: str = "default"):
    return build_radar(user_id)


@app.post("/api/mock/sessions")
def mock_create(body: MockCreateBody):
    session = store.create_mock_session(body.mode, body.vendor, body.focus, body.user_id)
    opener = mock_svc.start_message(session)
    transcript = [{"role": "interviewer", "content": opener}]
    store.update_mock_session(session["id"], transcript=transcript)
    session = store.get_mock_session(session["id"])
    timing = mock_svc.stage_timing(session)
    if timing:
        session["stage_timing"] = timing
    return session


@app.post("/api/mock/sessions/{session_id}/message")
def mock_message(session_id: str, body: MockMessageBody):
    try:
        return mock_svc.handle_message(session_id, body.message, body.want_hint)
    except KeyError:
        raise HTTPException(404, "session not found")


@app.post("/api/mock/sessions/{session_id}/finish")
def mock_finish(session_id: str):
    try:
        return mock_svc.finish_session(session_id)
    except KeyError:
        raise HTTPException(404, "session not found")


def _enrich_mock_session(session: dict) -> dict:
    timing = mock_svc.stage_timing(session)
    if timing:
        session["stage_timing"] = timing
    return session


@app.get("/api/mock/sessions/{session_id}")
def mock_get(session_id: str):
    try:
        return _enrich_mock_session(store.get_mock_session(session_id))
    except KeyError:
        raise HTTPException(404, "session not found")


@app.get("/api/mock/sessions/{session_id}/report.pdf")
def mock_report_pdf(session_id: str):
    try:
        session = store.get_mock_session(session_id)
    except KeyError:
        raise HTTPException(404, "session not found")
    if not session.get("report") and not session.get("scores"):
        raise HTTPException(400, "session has no report yet")
    pdf = build_mock_report_pdf(session)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="mock-{session_id[:8]}.pdf"'},
    )


@app.get("/api/mock/sessions")
def mock_list(user_id: str = "default", limit: int = 20):
    return {"sessions": store.list_mock_sessions(user_id, limit)}


@app.get("/api/labs")
def labs_list():
    return {"labs": load_manifest()}


@app.get("/api/labs/recommend")
def labs_recommend(user_id: str = "default", limit: int = 3):
    return {"labs": recommend_labs(user_id=user_id, limit=limit)}


@app.post("/api/labs/{lab_id}/complete")
def labs_complete(lab_id: str, body: LabCompleteBody):
    return store.complete_lab(body.user_id, lab_id, body.notes)


@app.get("/api/admin/content/pending", dependencies=[Depends(require_admin)])
def admin_pending():
    return {"items": store.list_content_items("pending_audit")}


@app.get("/api/admin/content/runs", dependencies=[Depends(require_admin)])
def admin_runs(limit: int = 30):
    return {"runs": store.list_content_runs(limit)}


@app.get("/api/admin/content/{item_id}", dependencies=[Depends(require_admin)])
def admin_content_detail(item_id: str):
    try:
        item = store.get_content_item(item_id)
    except KeyError:
        raise HTTPException(404, "item not found")
    from pathlib import Path

    preview = ""
    p = Path(item["source_path"])
    if p.exists():
        preview = p.read_text(encoding="utf-8")[:8000]
    return {**item, "preview": preview}


@app.post("/api/admin/content/{item_id}/approve", dependencies=[Depends(require_admin)])
def admin_approve(item_id: str):
    try:
        item = store.get_content_item(item_id)
        publish_item(item)
        return store.get_content_item(item_id)
    except KeyError:
        raise HTTPException(404, "item not found")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/content/{item_id}/reject", dependencies=[Depends(require_admin)])
def admin_reject(item_id: str, body: RejectBody):
    try:
        return reject_item(item_id, body.note)
    except KeyError:
        raise HTTPException(404, "item not found")


@app.post("/api/admin/content/run-update", dependencies=[Depends(require_admin)])
def admin_run_update():
    return run_daily_update()


@app.get("/api/admin/content/publish-logs", dependencies=[Depends(require_admin)])
def admin_publish_logs(limit: int = 30):
    return {"logs": list_publish_logs(limit)}


@app.post("/api/admin/content/rollback/{log_id}", dependencies=[Depends(require_admin)])
def admin_rollback(log_id: str):
    try:
        return rollback_publish(log_id)
    except KeyError:
        raise HTTPException(404, "publish log not found")
