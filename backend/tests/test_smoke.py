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

from fastapi.testclient import TestClient  # noqa: E402

from app.db.store import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.rag.ingest import ingest_knowledge  # noqa: E402
from app.interview.questions import load_questions  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def setup():
    init_db()
    ingest_knowledge()
    load_questions(reload=True)


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["questions"] >= 120


def test_ask():
    r = client.post("/api/ask", json={"question": "什么是 Harness", "corpus": "tech"})
    assert r.status_code == 200
    assert "answer" in r.json()


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
    r = client.post("/api/ingest", json={"full": False}, headers={"X-Admin-Key": "change-me-admin-key"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "incremental"
    assert "chunks_indexed" in body


def test_review_calendar():
    r = client.get("/api/quiz/review/calendar?year=2026&month=5")
    assert r.status_code == 200
    assert r.json()["year"] == 2026


def test_review_flow():
    r = client.get("/api/quiz/next?vendor=aliyun")
    qid = r.json()["question"]["id"]
    client.post(
        "/api/quiz/submit",
        json={"question_id": qid, "answer_text": "x", "use_ai": False, "self_score": 40},
    )
    r2 = client.get("/api/quiz/review/due")
    assert r2.status_code == 200
