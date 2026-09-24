import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["KNOWLEDGE_PATH"] = str(ROOT / "knowledge")
os.environ["SQLITE_PATH"] = str(ROOT / "backend" / "data" / "test_hub.db")
os.environ["CHROMA_PATH"] = str(ROOT / "backend" / "data" / "chroma_test")
os.environ["PROJECT_ROOT"] = str(ROOT)
os.environ["CONTENT_ROOT"] = str(ROOT / "content")
os.environ["DEMO_MODE"] = "true"
os.environ["CONTENT_SCHEDULER_ENABLED"] = "false"
os.environ["AUTH_INVITE_CODE"] = "test-invite-2026"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.store import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rag.ingest import ingest_knowledge  # noqa: E402
from app.interview.questions import load_questions  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def setup():
    database = Path(os.environ["SQLITE_PATH"])
    privacy_ledger = database.with_name("test_smoke_privacy_ledger.db")
    if database.exists():
        database.unlink()
    if privacy_ledger.exists():
        privacy_ledger.unlink()
    settings.sqlite_path = str(database)
    settings.privacy_ledger_path = str(privacy_ledger)
    settings.privacy_ledger_id = "test-smoke-ledger"
    settings.auth_invite_code = "test-invite-2026"
    settings.app_env = "test"
    init_db()
    ingest_knowledge()
    load_questions(reload=True)
    client.cookies.clear()
    response = client.post(
        "/api/auth/register",
        json={
            "email": "smoke-admin@example.com",
            "password": "correct horse battery staple",
            "invite_code": "test-invite-2026",
        },
    )
    assert response.status_code == 201


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["questions"] >= 120


def test_ask():
    r = client.post("/api/ask", json={"question": "什么是 Harness", "corpus": "tech"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert body["citation_details"]
    assert {"source_id", "path", "excerpt"} <= body["citation_details"][0].keys()


def test_quiz_flow():
    r = client.get("/api/quiz/next?vendor=aliyun")
    assert r.status_code == 200
    qid = r.json()["question"]["id"]
    r2 = client.post(
        "/api/quiz/submit",
        json={"question_id": qid, "answer_text": "多 AZ SLB RDS 等保", "use_ai": False},
    )
    assert r2.status_code == 200


def test_mock_session():
    r = client.post(
        "/api/mock/sessions",
        json={"mode": "free", "vendor": "aliyun", "focus": "architecture"},
    )
    assert r.status_code == 200
    sid = r.json()["id"]
    r2 = client.post(
        f"/api/mock/sessions/{sid}/message",
        json={"message": "我有三年售前经验", "want_hint": False},
    )
    assert r2.status_code == 200


def test_structured_mock_timing():
    r = client.post(
        "/api/mock/sessions",
        json={"mode": "structured", "vendor": "aliyun", "focus": "architecture"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "stage_timing" in data
    assert data["stage_timing"]["remaining_sec"] > 0


def test_progress_radar():
    r = client.get("/api/progress/radar")
    assert r.status_code == 200
    body = r.json()
    assert "quiz" in body and "mock" in body
    assert len(body["quiz"]["axes"]) >= 5


def test_ingest_incremental():
    r = client.post("/api/ingest", json={"full": False})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "incremental"
    assert "chunks_indexed" in body


def test_review_calendar():
    r = client.get("/api/quiz/review/calendar?year=2026&month=5")
    assert r.status_code == 200
    assert r.json()["year"] == 2026


def test_settings_and_reference():
    r = client.put(
        "/api/settings",
        json={"llm_model": "test-model", "force_demo": True},
    )
    assert r.status_code == 200
    r2 = client.get("/api/quiz/next?vendor=aliyun")
    qid = r2.json()["question"]["id"]
    client.put(
        f"/api/quiz/questions/{qid}/reference",
        json={"reference_text": "多 AZ、SLB、RDS 主备、等保三级 WAF"},
    )
    r3 = client.post(
        "/api/quiz/submit",
        json={
            "question_id": qid,
            "answer_text": "使用 SLB 和 RDS",
            "reference_answer": "多 AZ、SLB、RDS 主备、等保三级 WAF",
            "save_reference": True,
            "use_ai": False,
        },
    )
    assert r3.status_code == 200
    assert r3.json().get("reference_used") is True
    r4 = client.get("/api/quiz/analytics")
    assert r4.status_code == 200
    assert r4.json()["summary"]["total_attempts"] >= 1


def test_review_flow():
    r = client.get("/api/quiz/next?vendor=aliyun")
    qid = r.json()["question"]["id"]
    client.post(
        "/api/quiz/submit",
        json={"question_id": qid, "answer_text": "x", "use_ai": False, "self_score": 40},
    )
    r2 = client.get("/api/quiz/review/due")
    assert r2.status_code == 200
