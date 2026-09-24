from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth.router import (
    enforce_session,
    require_admin,
    require_identity,
    router as auth_router,
)
from app.auth.service import Identity
from app.config import settings
from app.health import NotReady, readiness
from app.observability import configure_structured_logging, request_telemetry
from app.privacy.router import router as privacy_router
from app.content.daily_update import run_daily_update
from app.content.provenance_router import router as provenance_router
from app.content.publish import publish_item, reject_item
from app.content.rollback import list_publish_logs, rollback_publish
from app.db import store
from app.exercises.router import router as exercises_router
from app.interview import mock as mock_svc
from app.interview import review as review_svc
from app.interview.analytics import build_quiz_analytics
from app.interview.quiz import build_explanation, next_question, score_answer_ai, submit_answer
from app.llm.client import ModelEndpointError
from app.settings import service as settings_svc
from app.security.credential_vault import CredentialVaultUnavailable
from app.security.outbound_url import UnsafeOutboundUrl
from app.interview.questions import get_question, load_questions, questions_by_vendor
from app.progress.radar import build_radar
from app.reports.pdf import build_mock_report_pdf
from app.labs.recommend import load_manifest, recommend_labs
from app.qa import service as qa_svc
from app.rag.ingest import ingest_knowledge, ingest_knowledge_incremental
from app.rag.knowledge_lookup import get_by_source_id, list_source_ids
from app.scheduler.jobs import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init_db()
    settings_svc.migrate_legacy_llm_keys()
    settings_svc.migrate_unbound_llm_keys()
    try:
        ingest_knowledge_incremental()
        qa_svc.get_retriever()
    except Exception as e:
        print(f"[warn] ingest skipped: {e}")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Agent Knowledge Hub API", version="0.1.0", lifespan=lifespan)
configure_structured_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(enforce_session)
app.middleware("http")(request_telemetry)
app.include_router(auth_router)
app.include_router(privacy_router)
app.include_router(provenance_router)
app.include_router(exercises_router)


MODEL_TEST_MESSAGES = {
    "model_auth_failed": "认证失败，请检查 API Key",
    "model_rate_limited": "模型服务限流，请稍后重试",
    "model_request_invalid": "模型名称或请求参数无效",
    "model_endpoint_blocked": "模型地址不安全",
    "model_endpoint_unreachable": "无法连接模型服务",
    "model_request_deadline_exceeded": "模型服务响应超时",
    "model_response_too_large": "模型服务响应过大",
    "model_response_encoding_unsupported": "模型服务响应编码不受支持",
    "model_capacity_exhausted": "模型调用繁忙，请稍后重试",
    "model_response_invalid": "模型服务返回了无效响应",
}

@app.exception_handler(ModelEndpointError)
async def model_endpoint_error_handler(
    _request: Request,
    exc: ModelEndpointError,
) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": exc.code})


@app.exception_handler(settings_svc.CredentialEndpointMismatch)
async def credential_endpoint_error_handler(
    _request: Request,
    _exc: settings_svc.CredentialEndpointMismatch,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "model_key_required_for_endpoint"},
    )


@app.exception_handler(store.SettingsWriteConflict)
async def settings_write_conflict_handler(
    _request: Request,
    _exc: store.SettingsWriteConflict,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "settings_changed_retry"},
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
    reference_answer: str = ""
    save_reference: bool = False
    self_score: int | None = None
    use_ai: bool = True


class AssessmentGradeBody(BaseModel):
    question: str
    answer_text: str
    key_points: list[str] = Field(default_factory=list)
    rubric: dict[str, int] = Field(default_factory=dict)
    reference_answer: str = ""


class SettingsBody(BaseModel):
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_protocol: str | None = None
    force_demo: bool = False


class ReferenceAnswerBody(BaseModel):
    reference_text: str


class MockCreateBody(BaseModel):
    mode: str = "free"
    vendor: str = "aliyun"
    focus: str = "architecture"


class MockMessageBody(BaseModel):
    message: str
    want_hint: bool = False


class LabCompleteBody(BaseModel):
    notes: str = ""


class RejectBody(BaseModel):
    note: str = ""


class ReviewGradeBody(BaseModel):
    question_id: str
    quality: int = Field(ge=0, le=5)


class IngestBody(BaseModel):
    full: bool = False


@app.get("/api/health")
def health():
    rt = settings_svc.resolve_llm()
    return {
        "status": "ok",
        "model": rt.model,
        "demo_mode": rt.demo,
        "questions": len(load_questions()),
        "sources": len(list_source_ids()),
    }


@app.post("/api/ingest")
def api_ingest(
    body: IngestBody = IngestBody(),
    _identity: Identity = Depends(require_admin),
):
    result = ingest_knowledge(full=body.full)
    if (
        body.full
        or result.get("files_processed", 0) > 0
        or result.get("files_removed", 0) > 0
    ):
        qa_svc.get_retriever().reload_bm25()
    return result


@app.post("/api/ask")
def api_ask(body: AskBody, _identity: Identity = Depends(require_identity)):
    return qa_svc.ask(body.question, corpus=body.corpus, top_k=body.top_k)


@app.post("/api/search")
def api_search(body: SearchBody, _identity: Identity = Depends(require_identity)):
    chunks = qa_svc.get_retriever().search(body.query, top_k=body.top_k, corpus=None if body.corpus == "all" else body.corpus)
    return {
        "results": [
            {"source_id": c.source_id, "text": c.text, "score": c.score, "path": c.path, "corpus": c.corpus}
            for c in chunks
        ]
    }


@app.get("/api/sources")
def api_sources(
    corpus: str | None = None,
    _identity: Identity = Depends(require_identity),
):
    return {"source_ids": list_source_ids(corpus)}


@app.get("/api/sources/{source_id}")
def api_source(source_id: str, _identity: Identity = Depends(require_identity)):
    doc = get_by_source_id(source_id)
    if not doc:
        raise HTTPException(404, "source not found")
    return doc


@app.get("/api/content/feed")
def content_feed(limit: int = 20, _identity: Identity = Depends(require_identity)):
    return {"items": store.get_content_feed(limit)}


@app.get("/api/quiz/next")
def quiz_next(
    vendor: str | None = None,
    category: str | None = None,
    difficulty: int | None = None,
    identity: Identity = Depends(require_identity),
):
    result = next_question(vendor=vendor, category=category, difficulty=difficulty)
    if not result:
        raise HTTPException(404, "no matching question")
    qid = result["question"]["id"]
    ref = store.get_reference_answer(identity.user_id, qid)
    if ref:
        result["saved_reference"] = ref.get("reference_text", "")
    history = store.get_question_attempt_scores(identity.user_id, qid)
    if history:
        result["score_history"] = history
    return result


@app.post("/api/quiz/submit")
def quiz_submit(body: QuizSubmitBody, identity: Identity = Depends(require_identity)):
    try:
        return submit_answer(
            identity.user_id,
            body.question_id,
            body.answer_text,
            reference_answer=body.reference_answer or None,
            save_reference=body.save_reference,
            use_ai=body.use_ai,
            self_score=body.self_score,
        )
    except KeyError:
        raise HTTPException(404, "question not found")


@app.post("/api/assessment/grade")
def assessment_grade(
    body: AssessmentGradeBody,
    identity: Identity = Depends(require_identity),
):
    """Grade an open-ended assessment answer against inline criteria.

    Reuses the quiz LLM grader without any DB persistence or review
    scheduling, so skill-assessment attempts stay separate from quiz history.
    Falls back to the heuristic demo grader when no LLM key is configured.
    """
    question = {
        "question": body.question,
        "key_points": body.key_points,
        "rubric": body.rubric,
    }
    runtime = settings_svc.resolve_llm(identity.user_id)
    result = score_answer_ai(
        question,
        body.answer_text,
        reference_answer=body.reference_answer or None,
        runtime=runtime,
    )
    score = result.get("ai_score", 70)
    return {
        "ai_score": score,
        "matched_points": result.get("matched_points", []),
        "missing_points": result.get("missing_points", []),
        "feedback": result.get("feedback", ""),
        "demo": runtime.demo,
    }


@app.get("/api/quiz/questions/{question_id}/reference")
def quiz_get_reference(
    question_id: str,
    identity: Identity = Depends(require_identity),
):
    ref = store.get_reference_answer(identity.user_id, question_id)
    return {"reference": ref}


@app.put("/api/quiz/questions/{question_id}/reference")
def quiz_put_reference(
    question_id: str,
    body: ReferenceAnswerBody,
    identity: Identity = Depends(require_identity),
):
    if not get_question(question_id):
        raise HTTPException(404, "question not found")
    ref = store.upsert_reference_answer(
        identity.user_id,
        question_id,
        body.reference_text,
    )
    return {"reference": ref}


@app.get("/api/quiz/history")
def quiz_history(
    limit: int = 50,
    identity: Identity = Depends(require_identity),
):
    items = store.list_quiz_history(identity.user_id, limit=limit)
    enriched = []
    for row in items:
        q = get_question(row["question_id"])
        enriched.append({**row, "question_meta": q})
    return {"items": enriched}


@app.get("/api/quiz/analytics")
def quiz_analytics(identity: Identity = Depends(require_identity)):
    return build_quiz_analytics(identity.user_id)


@app.get("/api/settings")
def api_get_settings(identity: Identity = Depends(require_identity)):
    return settings_svc.get_settings_public(identity.user_id)


@app.put("/api/settings")
def api_put_settings(
    body: SettingsBody,
    identity: Identity = Depends(require_identity),
):
    payload = {}
    if body.llm_base_url is not None:
        payload["llm_base_url"] = body.llm_base_url
    if body.llm_model is not None:
        payload["llm_model"] = body.llm_model
    if body.llm_protocol is not None:
        payload["llm_protocol"] = body.llm_protocol
    if body.llm_api_key:
        payload["llm_api_key"] = body.llm_api_key
    payload["force_demo"] = int(body.force_demo)
    try:
        return settings_svc.update_settings(identity.user_id, payload)
    except CredentialVaultUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="credential_encryption_unavailable",
        ) from exc
    except UnsafeOutboundUrl as exc:
        raise HTTPException(
            status_code=422,
            detail="unsafe_llm_base_url",
        ) from exc
    except settings_svc.CredentialEndpointMismatch as exc:
        raise HTTPException(
            status_code=422,
            detail="model_key_required_for_endpoint",
        ) from exc
    except ValueError as exc:
        if str(exc) == "unsupported_llm_protocol":
            raise HTTPException(
                status_code=422,
                detail="unsupported_llm_protocol",
            ) from exc
        raise


@app.post("/api/settings/test")
def api_test_settings(identity: Identity = Depends(require_identity)):
    from app.llm.client import chat_text
    from app.settings.service import resolve_llm

    response = {"protocol": "", "model": ""}
    try:
        rt = resolve_llm(identity.user_id)
        response = {"protocol": rt.protocol, "model": rt.model}
        if rt.demo:
            return {
                "ok": False,
                "code": "demo_mode_active",
                "message": "当前为 Demo 模式，未向外部模型服务发起请求",
                **response,
            }
        reply = chat_text(
            "你是助手。",
            "回复 JSON 字符串 {\"status\":\"ok\"}",
            runtime=rt,
        )
        return {
            "ok": True,
            "code": "connected",
            "message": "连接成功",
            **response,
            "preview": reply[:200],
        }
    except ModelEndpointError as exc:
        code = (
            exc.code
            if exc.code in MODEL_TEST_MESSAGES
            else "model_endpoint_unreachable"
        )
        return {
            "ok": False,
            "code": code,
            "message": MODEL_TEST_MESSAGES[code],
            **response,
        }
    except Exception:
        code = "model_endpoint_unreachable"
        return {
            "ok": False,
            "code": code,
            "message": MODEL_TEST_MESSAGES[code],
            **response,
        }

@app.get("/api/quiz/wrong-book")
def quiz_wrong_book(identity: Identity = Depends(require_identity)):
    return {"items": store.get_wrong_book(identity.user_id)}


@app.get("/api/quiz/stats")
def quiz_stats(identity: Identity = Depends(require_identity)):
    return {
        **store.quiz_stats(identity.user_id),
        "by_vendor": questions_by_vendor(),
        "review": review_svc.review_stats(identity.user_id),
    }


@app.get("/api/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/api/health/ready")
def health_ready():
    try:
        return readiness()
    except NotReady:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )


@app.get("/api/questions/all")
def questions_all(_identity: Identity = Depends(require_identity)):
    """Return all questions grouped by vendor with reference answers."""
    return {"questions": load_questions()}


@app.get("/api/quiz/review/due")
def quiz_review_due(
    limit: int = 10,
    identity: Identity = Depends(require_identity),
):
    due = review_svc.due_reviews(identity.user_id, limit=limit)
    items = []
    for card in due:
        q = get_question(card["question_id"])
        if q:
            items.append({"card": card, "question": q})
    return {"items": items}


@app.post("/api/quiz/review/grade")
def quiz_review_grade(
    body: ReviewGradeBody,
    identity: Identity = Depends(require_identity),
):
    try:
        card = review_svc.grade_review(
            identity.user_id,
            body.question_id,
            body.quality,
        )
    except KeyError:
        raise HTTPException(404, "review card not found")
    return {"card": card}


@app.get("/api/quiz/review/calendar")
def quiz_review_calendar(
    year: int | None = None,
    month: int | None = None,
    identity: Identity = Depends(require_identity),
):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    if m < 1 or m > 12:
        raise HTTPException(400, "month must be 1-12")
    return review_svc.review_calendar(identity.user_id, y, m)


@app.get("/api/progress/radar")
def progress_radar(identity: Identity = Depends(require_identity)):
    return build_radar(identity.user_id)


@app.post("/api/mock/sessions")
def mock_create(
    body: MockCreateBody,
    identity: Identity = Depends(require_identity),
):
    session = store.create_mock_session(
        body.mode,
        body.vendor,
        body.focus,
        identity.user_id,
    )
    opener = mock_svc.start_message(session)
    transcript = [{"role": "interviewer", "content": opener}]
    store.update_mock_session(
        session["id"],
        identity.user_id,
        transcript=transcript,
    )
    session = store.get_mock_session(session["id"], identity.user_id)
    timing = mock_svc.stage_timing(session)
    if timing:
        session["stage_timing"] = timing
    return session


@app.post("/api/mock/sessions/{session_id}/message")
def mock_message(
    session_id: str,
    body: MockMessageBody,
    identity: Identity = Depends(require_identity),
):
    try:
        return mock_svc.handle_message(
            session_id,
            identity.user_id,
            body.message,
            body.want_hint,
        )
    except KeyError:
        raise HTTPException(404, "session not found")


@app.post("/api/mock/sessions/{session_id}/finish")
def mock_finish(
    session_id: str,
    identity: Identity = Depends(require_identity),
):
    try:
        return mock_svc.finish_session(session_id, identity.user_id)
    except KeyError:
        raise HTTPException(404, "session not found")


def _enrich_mock_session(session: dict) -> dict:
    timing = mock_svc.stage_timing(session)
    if timing:
        session["stage_timing"] = timing
    return session


@app.get("/api/mock/sessions/{session_id}")
def mock_get(
    session_id: str,
    identity: Identity = Depends(require_identity),
):
    try:
        return _enrich_mock_session(
            store.get_mock_session(session_id, identity.user_id)
        )
    except KeyError:
        raise HTTPException(404, "session not found")


@app.get("/api/mock/sessions/{session_id}/report.pdf")
def mock_report_pdf(
    session_id: str,
    identity: Identity = Depends(require_identity),
):
    try:
        session = store.get_mock_session(session_id, identity.user_id)
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
def mock_list(
    limit: int = 20,
    identity: Identity = Depends(require_identity),
):
    return {"sessions": store.list_mock_sessions(identity.user_id, limit)}


@app.get("/api/labs")
def labs_list(_identity: Identity = Depends(require_identity)):
    return {"labs": load_manifest()}


@app.get("/api/labs/recommend")
def labs_recommend(
    limit: int = 3,
    identity: Identity = Depends(require_identity),
):
    return {"labs": recommend_labs(user_id=identity.user_id, limit=limit)}


@app.post("/api/labs/{lab_id}/complete")
def labs_complete(
    lab_id: str,
    body: LabCompleteBody,
    identity: Identity = Depends(require_identity),
):
    return store.complete_lab(identity.user_id, lab_id, body.notes)


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
