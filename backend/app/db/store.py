"""SQLite persistence for quiz, mock, content governance, labs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


def _conn() -> sqlite3.Connection:
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_answers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                question_id TEXT NOT NULL,
                answer_text TEXT,
                self_score INTEGER,
                ai_score INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mock_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                mode TEXT NOT NULL,
                vendor TEXT,
                focus TEXT,
                stage TEXT,
                transcript TEXT,
                scores TEXT,
                report TEXT,
                recommended_lab_ids TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lab_completions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'default',
                lab_id TEXT NOT NULL,
                notes TEXT,
                completed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS content_items (
                id TEXT PRIMARY KEY,
                item_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                status TEXT NOT NULL,
                title TEXT,
                audit_checks TEXT,
                audit_report TEXT,
                quality_score REAL,
                reviewer_note TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS content_runs (
                id TEXT PRIMARY KEY,
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT,
                items_created INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS content_changelog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                item_id TEXT,
                title TEXT,
                published_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_cards (
                user_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                easiness REAL NOT NULL DEFAULT 2.5,
                repetitions INTEGER NOT NULL DEFAULT 0,
                interval_days INTEGER NOT NULL DEFAULT 1,
                next_review_at TEXT NOT NULL,
                last_quality INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, question_id)
            );
            CREATE TABLE IF NOT EXISTS content_publish_log (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                dest_paths TEXT NOT NULL,
                backup_paths TEXT NOT NULL,
                published_at TEXT NOT NULL,
                rolled_back INTEGER NOT NULL DEFAULT 0
            );
            """
        )
    _migrate_columns()


def _migrate_columns() -> None:
    with _conn() as c:
        cols = {row[1] for row in c.execute("PRAGMA table_info(mock_sessions)").fetchall()}
        if "stage_started_at" not in cols:
            c.execute("ALTER TABLE mock_sessions ADD COLUMN stage_started_at TEXT")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Quiz ---


def save_quiz_answer(
    user_id: str,
    question_id: str,
    answer_text: str,
    self_score: int | None,
    ai_score: int | None,
) -> dict:
    aid = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            """INSERT INTO user_answers (id, user_id, question_id, answer_text, self_score, ai_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (aid, user_id, question_id, answer_text, self_score, ai_score, _now()),
        )
    return {"id": aid, "question_id": question_id}


def get_wrong_book(user_id: str = "default", max_score: int = 60) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT question_id, MAX(COALESCE(ai_score, self_score, 0)) as best
               FROM user_answers WHERE user_id = ? GROUP BY question_id HAVING best < ?""",
            (user_id, max_score),
        ).fetchall()
    return [{"question_id": r["question_id"], "best_score": r["best"]} for r in rows]


def quiz_stats(user_id: str = "default") -> dict:
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM user_answers WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        avg = c.execute(
            "SELECT AVG(COALESCE(ai_score, self_score)) FROM user_answers WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    return {"total_attempts": total, "avg_score": round(avg or 0, 1)}


# --- Mock ---


def create_mock_session(
    mode: str, vendor: str, focus: str, user_id: str = "default"
) -> dict:
    sid = str(uuid.uuid4())
    stage = "INTRO" if mode == "structured" else "FREE"
    now = _now()
    row = {
        "id": sid,
        "user_id": user_id,
        "mode": mode,
        "vendor": vendor,
        "focus": focus,
        "stage": stage,
        "stage_started_at": now,
        "transcript": [],
        "scores": None,
        "report": None,
        "recommended_lab_ids": [],
        "created_at": now,
        "updated_at": now,
    }
    with _conn() as c:
        c.execute(
            """INSERT INTO mock_sessions
               (id, user_id, mode, vendor, focus, stage, transcript, scores, report,
                recommended_lab_ids, created_at, updated_at, stage_started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sid,
                user_id,
                mode,
                vendor,
                focus,
                stage,
                json.dumps([]),
                None,
                None,
                json.dumps([]),
                now,
                now,
                now,
            ),
        )
    return row


def get_mock_session(session_id: str) -> dict:
    with _conn() as c:
        r = c.execute("SELECT * FROM mock_sessions WHERE id = ?", (session_id,)).fetchone()
    if not r:
        raise KeyError(session_id)
    return _mock_row_to_dict(r)


def _mock_row_to_dict(r: sqlite3.Row) -> dict:
    keys = r.keys()
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "mode": r["mode"],
        "vendor": r["vendor"],
        "focus": r["focus"],
        "stage": r["stage"],
        "stage_started_at": r["stage_started_at"] if "stage_started_at" in keys else None,
        "transcript": json.loads(r["transcript"] or "[]"),
        "scores": json.loads(r["scores"]) if r["scores"] else None,
        "report": json.loads(r["report"]) if r["report"] else None,
        "recommended_lab_ids": json.loads(r["recommended_lab_ids"] or "[]"),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def update_mock_session(session_id: str, **kwargs: Any) -> dict:
    allowed = {
        "stage",
        "transcript",
        "scores",
        "report",
        "recommended_lab_ids",
        "stage_started_at",
    }
    sets = []
    vals: list[Any] = []
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if k in ("transcript", "scores", "report", "recommended_lab_ids"):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(session_id)
    with _conn() as c:
        c.execute(f"UPDATE mock_sessions SET {', '.join(sets)} WHERE id = ?", vals)
    return get_mock_session(session_id)


def list_mock_sessions(user_id: str = "default", limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM mock_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [_mock_row_to_dict(r) for r in rows]


# --- Labs ---


def complete_lab(user_id: str, lab_id: str, notes: str = "") -> dict:
    lid = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            "INSERT INTO lab_completions (id, user_id, lab_id, notes, completed_at) VALUES (?, ?, ?, ?, ?)",
            (lid, user_id, lab_id, notes, _now()),
        )
    return {"id": lid, "lab_id": lab_id}


def list_completed_labs(user_id: str = "default") -> list[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT lab_id FROM lab_completions WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [r["lab_id"] for r in rows]


# --- Content governance ---


def create_content_item(
    item_type: str,
    source_path: str,
    title: str,
    status: str = "pending_audit",
) -> dict:
    cid = str(uuid.uuid4())
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO content_items
               (id, item_type, source_path, status, title, audit_checks, audit_report, quality_score, reviewer_note, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, item_type, source_path, status, title, None, None, None, None, now, now),
        )
    return get_content_item(cid)


def get_content_item(item_id: str) -> dict:
    with _conn() as c:
        r = c.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
    if not r:
        raise KeyError(item_id)
    return _content_row_to_dict(r)


def _content_row_to_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "item_type": r["item_type"],
        "source_path": r["source_path"],
        "status": r["status"],
        "title": r["title"],
        "audit_checks": json.loads(r["audit_checks"]) if r["audit_checks"] else None,
        "audit_report": json.loads(r["audit_report"]) if r["audit_report"] else None,
        "quality_score": r["quality_score"],
        "reviewer_note": r["reviewer_note"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def list_content_items(status: str | None = None) -> list[dict]:
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM content_items WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM content_items ORDER BY created_at DESC"
            ).fetchall()
    return [_content_row_to_dict(r) for r in rows]


def update_content_item(item_id: str, **kwargs: Any) -> dict:
    allowed = {
        "status",
        "audit_checks",
        "audit_report",
        "quality_score",
        "reviewer_note",
        "title",
    }
    sets = []
    vals: list[Any] = []
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if k in ("audit_checks", "audit_report"):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = ?")
    vals.append(_now())
    vals.append(item_id)
    with _conn() as c:
        c.execute(f"UPDATE content_items SET {', '.join(sets)} WHERE id = ?", vals)
    return get_content_item(item_id)


def create_content_run(run_type: str, status: str, summary: str = "") -> dict:
    rid = str(uuid.uuid4())
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO content_runs (id, run_type, status, summary, items_created, started_at, finished_at)
               VALUES (?, ?, ?, ?, 0, ?, NULL)""",
            (rid, run_type, status, summary, now),
        )
    return {"id": rid, "run_type": run_type, "status": status, "started_at": now}


def finish_content_run(run_id: str, status: str, summary: str, items_created: int) -> None:
    with _conn() as c:
        c.execute(
            """UPDATE content_runs SET status = ?, summary = ?, items_created = ?, finished_at = ?
               WHERE id = ?""",
            (status, summary, items_created, _now(), run_id),
        )


def list_content_runs(limit: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM content_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def add_changelog(action: str, item_id: str, title: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO content_changelog (action, item_id, title, published_at) VALUES (?, ?, ?, ?)",
            (action, item_id, title, _now()),
        )


def get_content_feed(limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM content_changelog ORDER BY published_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --- SM-2 review ---


def upsert_review_card(user_id: str, question_id: str, quality: int = 2) -> dict:
    now = _now()
    next_at = now
    with _conn() as c:
        c.execute(
            """INSERT INTO review_cards
               (user_id, question_id, easiness, repetitions, interval_days, next_review_at, last_quality, updated_at)
               VALUES (?, ?, 2.5, 0, 1, ?, ?, ?)
               ON CONFLICT(user_id, question_id) DO UPDATE SET
                 repetitions = 0, interval_days = 1, next_review_at = excluded.next_review_at,
                 last_quality = excluded.last_quality, updated_at = excluded.updated_at""",
            (user_id, question_id, next_at, quality, now),
        )
    return get_review_card(user_id, question_id)


def get_review_card(user_id: str, question_id: str) -> dict:
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM review_cards WHERE user_id = ? AND question_id = ?",
            (user_id, question_id),
        ).fetchone()
    if not r:
        raise KeyError(question_id)
    return dict(r)


def update_review_card(
    user_id: str,
    question_id: str,
    *,
    easiness: float,
    repetitions: int,
    interval_days: int,
    next_review_at: str,
    last_quality: int,
) -> dict:
    with _conn() as c:
        c.execute(
            """UPDATE review_cards SET easiness = ?, repetitions = ?, interval_days = ?,
               next_review_at = ?, last_quality = ?, updated_at = ?
               WHERE user_id = ? AND question_id = ?""",
            (
                easiness,
                repetitions,
                interval_days,
                next_review_at,
                last_quality,
                _now(),
                user_id,
                question_id,
            ),
        )
    return get_review_card(user_id, question_id)


def list_due_reviews(user_id: str = "default", limit: int = 10) -> list[dict]:
    now = _now()
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM review_cards WHERE user_id = ? AND next_review_at <= ?
               ORDER BY next_review_at ASC LIMIT ?""",
            (user_id, now, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def review_stats(user_id: str = "default") -> dict:
    now = _now()
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM review_cards WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        due = c.execute(
            "SELECT COUNT(*) FROM review_cards WHERE user_id = ? AND next_review_at <= ?",
            (user_id, now),
        ).fetchone()[0]
    return {"total_cards": total, "due_now": due}


def list_review_cards(user_id: str = "default") -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM review_cards WHERE user_id = ? ORDER BY next_review_at ASC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Progress radar helpers ---


def quiz_attempts_by_category(user_id: str = "default") -> dict[str, int]:
    from app.interview.questions import get_question

    with _conn() as c:
        rows = c.execute(
            "SELECT DISTINCT question_id FROM user_answers WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    counts: dict[str, int] = {}
    for r in rows:
        q = get_question(r["question_id"])
        if not q:
            continue
        cat = q.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def mock_avg_scores(user_id: str = "default") -> dict[str, float]:
    dims: dict[str, list[float]] = {}
    with _conn() as c:
        rows = c.execute(
            "SELECT scores FROM mock_sessions WHERE user_id = ? AND scores IS NOT NULL",
            (user_id,),
        ).fetchall()
    for r in rows:
        scores = json.loads(r["scores"])
        if not isinstance(scores, dict):
            continue
        for k, v in scores.items():
            try:
                dims.setdefault(k, []).append(float(v))
            except (TypeError, ValueError):
                pass
    return {k: sum(v) / len(v) for k, v in dims.items() if v}


# --- Publish rollback log ---


def create_publish_log(item_id: str, dest_paths: list[str], backup_paths: list[str]) -> dict:
    lid = str(uuid.uuid4())
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO content_publish_log (id, item_id, dest_paths, backup_paths, published_at, rolled_back)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (
                lid,
                item_id,
                json.dumps(dest_paths, ensure_ascii=False),
                json.dumps(backup_paths, ensure_ascii=False),
                now,
            ),
        )
    return get_publish_log(lid)


def get_publish_log(log_id: str) -> dict:
    with _conn() as c:
        r = c.execute("SELECT * FROM content_publish_log WHERE id = ?", (log_id,)).fetchone()
    if not r:
        raise KeyError(log_id)
    return dict(r)


def list_publish_logs(limit: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM content_publish_log ORDER BY published_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_publish_log_rolled_back(log_id: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE content_publish_log SET rolled_back = 1 WHERE id = ?",
            (log_id,),
        )
