"""SQLite persistence for quiz, mock, content governance, labs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.config import settings
from app.security.credential_vault import EncryptedSecret


_SETTINGS_REVISION_UNSET = object()


class SettingsWriteConflict(RuntimeError):
    """Raised when a settings profile changed after it was read."""


def _conn() -> sqlite3.Connection:
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA secure_delete = ON")
    return conn


def init_db() -> None:
    with closing(_conn()) as c:
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
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash
                ON auth_sessions(token_hash);
            """
        )
    _migrate_columns()
    from app.db.migrations import run_migrations

    with closing(_conn()) as c:
        run_migrations(c)
    from app.privacy.tombstones import apply_deletions, ensure_ledger

    ensure_ledger()
    apply_deletions(settings.sqlite_path)


def _migrate_columns() -> None:
    with closing(_conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            cols = {row[1] for row in c.execute("PRAGMA table_info(mock_sessions)").fetchall()}
            if "stage_started_at" not in cols:
                c.execute("ALTER TABLE mock_sessions ADD COLUMN stage_started_at TEXT")

            ua_cols = {row[1] for row in c.execute("PRAGMA table_info(user_answers)").fetchall()}
            for col, ddl in (
                ("reference_answer", "TEXT"),
                ("feedback", "TEXT"),
                ("model_name", "TEXT"),
                ("comparison_detail", "TEXT"),
            ):
                if col not in ua_cols:
                    c.execute(f"ALTER TABLE user_answers ADD COLUMN {col} {ddl}")

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                llm_base_url TEXT,
                llm_api_key TEXT,
                llm_api_key_ciphertext TEXT,
                llm_api_key_nonce TEXT,
                llm_api_key_version TEXT,
                llm_api_key_hint TEXT,
                llm_api_key_audience TEXT,
                llm_protocol TEXT NOT NULL DEFAULT 'openai_chat'
                    CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages')),
                llm_model TEXT,
                force_demo INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
                )
                """
            )
            settings_cols = {
                row[1] for row in c.execute("PRAGMA table_info(user_settings)").fetchall()
            }
            for col in (
                "llm_api_key_ciphertext",
                "llm_api_key_nonce",
                "llm_api_key_version",
                "llm_api_key_hint",
                "llm_api_key_audience",
            ):
                if col not in settings_cols:
                    c.execute(f"ALTER TABLE user_settings ADD COLUMN {col} TEXT")
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS user_reference_answers (
                user_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                reference_text TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, question_id)
                )
                """
            )
            c.commit()
        except Exception:
            c.rollback()
            raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Authentication ---


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _public_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def create_user(
    email: str,
    password_hash: str,
    *,
    rewrap_credential: (
        Callable[[EncryptedSecret, str, str], EncryptedSecret] | None
    ) = None,
) -> dict:
    user_id = str(uuid.uuid4())
    normalized_email = _normalize_email(email)
    now = _now()
    try:
        with _conn() as c:
            c.execute("BEGIN IMMEDIATE")
            user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            role = "admin" if user_count == 0 else "member"
            c.execute(
                """INSERT INTO users
                   (id, email, password_hash, role, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, normalized_email, password_hash, role, now, now),
            )
            if role == "admin":
                _claim_legacy_user_data(
                    c,
                    user_id,
                    rewrap_credential=rewrap_credential,
                )
            row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise ValueError("email_exists") from exc
    return _public_user(row)


def get_user_by_email(email: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
            (_normalize_email(email),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def export_user_data(user_id: str) -> dict:
    with closing(_conn()) as c:
        c.execute("BEGIN")
        try:
            user = c.execute(
                """
                SELECT id, email, role, created_at, updated_at
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
            if user is None:
                raise ValueError("user_not_found")

            def rows(table: str) -> list[dict]:
                return [
                    dict(row)
                    for row in c.execute(
                        f"SELECT * FROM {table} WHERE user_id = ?",
                        (user_id,),
                    ).fetchall()
                ]

            settings_row = c.execute(
                """
                SELECT llm_base_url, llm_protocol, llm_model, force_demo, updated_at,
                       CASE
                         WHEN llm_api_key_ciphertext IS NOT NULL
                              AND llm_api_key_ciphertext != ''
                         THEN 1 ELSE 0
                       END AS has_api_key
                FROM user_settings WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return {
                "profile": dict(user),
                "settings": (
                    {
                        **dict(settings_row),
                        "force_demo": bool(settings_row["force_demo"]),
                        "has_api_key": bool(settings_row["has_api_key"]),
                    }
                    if settings_row
                    else {
                        "llm_base_url": None,
                        "llm_protocol": "openai_chat",
                        "llm_model": None,
                        "force_demo": False,
                        "updated_at": None,
                        "has_api_key": False,
                    }
                ),
                "answers": rows("user_answers"),
                "exercise_attempts": rows("exercise_attempts"),
                "mock_sessions": rows("mock_sessions"),
                "lab_completions": rows("lab_completions"),
                "review_cards": rows("review_cards"),
                "reference_answers": rows("user_reference_answers"),
            }
        finally:
            c.rollback()


def delete_user_account(
    user_id: str,
    before_delete: Callable[[str], None] | None = None,
) -> None:
    deletion_recorded = False
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            user = c.execute(
                "SELECT role FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if user is None:
                raise ValueError("user_not_found")
            if user["role"] == "admin":
                administrator_count = c.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin'"
                ).fetchone()[0]
                other_user_count = c.execute(
                    "SELECT COUNT(*) FROM users WHERE id != ?",
                    (user_id,),
                ).fetchone()[0]
                if administrator_count == 1 and other_user_count > 0:
                    raise ValueError("last_admin")
            if before_delete is not None:
                before_delete(user_id)
                deletion_recorded = True
            from app.privacy.tombstones import USER_OWNED_TABLES

            for table in USER_OWNED_TABLES:
                c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
            c.execute("DELETE FROM users WHERE id = ?", (user_id,))
            c.commit()
        except Exception:
            c.rollback()
            if deletion_recorded:
                return
            raise


def create_auth_session(user_id: str, token_hash: str, expires_at: str) -> dict:
    session_id = str(uuid.uuid4())
    created_at = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO auth_sessions
               (id, user_id, token_hash, expires_at, created_at, revoked_at)
               VALUES (?, ?, ?, ?, ?, NULL)""",
            (session_id, user_id, token_hash, expires_at, created_at),
        )
    return {
        "id": session_id,
        "user_id": user_id,
        "expires_at": expires_at,
        "created_at": created_at,
    }


def get_identity_by_token_hash(token_hash: str, now: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            """SELECT users.id AS user_id, users.email, users.role
               FROM auth_sessions
               JOIN users ON users.id = auth_sessions.user_id
               WHERE auth_sessions.token_hash = ?
                 AND auth_sessions.revoked_at IS NULL
                 AND auth_sessions.expires_at > ?""",
            (token_hash, now),
        ).fetchone()
    return dict(row) if row else None


def revoke_auth_session(token_hash: str) -> None:
    with _conn() as c:
        c.execute(
            """UPDATE auth_sessions
               SET revoked_at = ?
               WHERE token_hash = ? AND revoked_at IS NULL""",
            (_now(), token_hash),
        )


def _claim_legacy_user_data(
    c: sqlite3.Connection,
    user_id: str,
    *,
    rewrap_credential: (
        Callable[[EncryptedSecret, str, str], EncryptedSecret] | None
    ) = None,
) -> None:
    user_tables = (
        "user_answers",
        "mock_sessions",
        "lab_completions",
        "review_cards",
        "user_reference_answers",
    )
    settings_row = c.execute(
        "SELECT * FROM user_settings WHERE user_id = 'default'"
    ).fetchone()
    if settings_row:
        encrypted: EncryptedSecret | None = None
        if settings_row["llm_api_key_ciphertext"]:
            if rewrap_credential is None:
                raise ValueError("encrypted legacy credential requires rewrapping")
            current = EncryptedSecret(
                ciphertext=settings_row["llm_api_key_ciphertext"],
                nonce=settings_row["llm_api_key_nonce"],
                key_version=settings_row["llm_api_key_version"],
                hint=settings_row["llm_api_key_hint"] or "",
                audience=settings_row["llm_api_key_audience"] or "",
            )
            encrypted = rewrap_credential(current, "default", user_id)
        c.execute(
            """UPDATE user_settings
               SET user_id = ?,
                   llm_api_key_ciphertext = ?,
                   llm_api_key_nonce = ?,
                   llm_api_key_version = ?,
                   llm_api_key_hint = ?,
                   llm_api_key_audience = ?
               WHERE user_id = 'default'""",
            (
                user_id,
                (
                    encrypted.ciphertext
                    if encrypted
                    else settings_row["llm_api_key_ciphertext"]
                ),
                encrypted.nonce if encrypted else settings_row["llm_api_key_nonce"],
                (
                    encrypted.key_version
                    if encrypted
                    else settings_row["llm_api_key_version"]
                ),
                encrypted.hint if encrypted else settings_row["llm_api_key_hint"],
                (
                    encrypted.audience
                    if encrypted
                    else settings_row["llm_api_key_audience"]
                ),
            ),
        )
    for table in user_tables:
        c.execute(
            f"UPDATE {table} SET user_id = ? WHERE user_id = 'default'",
            (user_id,),
        )


# --- Quiz ---


def save_quiz_answer(
    user_id: str,
    question_id: str,
    answer_text: str,
    self_score: int | None,
    ai_score: int | None,
    *,
    reference_answer: str | None = None,
    feedback: str | None = None,
    model_name: str | None = None,
    comparison_detail: dict | None = None,
) -> dict:
    aid = str(uuid.uuid4())
    detail_json = json.dumps(comparison_detail, ensure_ascii=False) if comparison_detail else None
    with _conn() as c:
        c.execute(
            """INSERT INTO user_answers
               (id, user_id, question_id, answer_text, self_score, ai_score, created_at,
                reference_answer, feedback, model_name, comparison_detail)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                aid,
                user_id,
                question_id,
                answer_text,
                self_score,
                ai_score,
                _now(),
                reference_answer,
                feedback,
                model_name,
                detail_json,
            ),
        )
    return {"id": aid, "question_id": question_id}


def list_quiz_history(user_id: str = "default", limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM user_answers WHERE user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("comparison_detail"):
            try:
                d["comparison_detail"] = json.loads(d["comparison_detail"])
            except Exception:
                pass
        out.append(d)
    return out


def get_question_attempt_scores(user_id: str, question_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT id, ai_score, self_score, created_at, feedback
               FROM user_answers WHERE user_id = ? AND question_id = ?
               ORDER BY created_at ASC""",
            (user_id, question_id),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "score": r["ai_score"] if r["ai_score"] is not None else r["self_score"],
            "created_at": r["created_at"],
            "feedback": r["feedback"],
        }
        for r in rows
    ]


# --- User settings ---


def get_user_settings(user_id: str = "default") -> dict:
    with _conn() as c:
        r = c.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    if not r:
        return {"user_id": user_id}
    return dict(r)


def upsert_user_settings(
    user_id: str,
    payload: dict,
    *,
    encrypted_api_key: EncryptedSecret | None = None,
    expected_updated_at: str | None | object = _SETTINGS_REVISION_UNSET,
) -> None:
    if "llm_api_key" in payload:
        raise ValueError("plaintext credentials are not accepted by the store")
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        current = c.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        row = dict(current) if current else {"user_id": user_id}
        current_revision = row.get("updated_at")
        if (
            expected_updated_at is not _SETTINGS_REVISION_UNSET
            and current_revision != expected_updated_at
        ):
            raise SettingsWriteConflict("settings changed during update")
        base_url = (
            payload["llm_base_url"]
            if "llm_base_url" in payload
            else row.get("llm_base_url")
        )
        model = (
            payload["llm_model"] if "llm_model" in payload else row.get("llm_model")
        )
        protocol = (
            payload["llm_protocol"]
            if "llm_protocol" in payload
            else (row.get("llm_protocol") or "openai_chat")
        )
        force_demo = int(
            payload["force_demo"]
            if "force_demo" in payload
            else (row.get("force_demo") or 0)
        )
        ciphertext = row.get("llm_api_key_ciphertext")
        nonce = row.get("llm_api_key_nonce")
        key_version = row.get("llm_api_key_version")
        key_hint = row.get("llm_api_key_hint")
        key_audience = row.get("llm_api_key_audience")
        if encrypted_api_key is not None:
            ciphertext = encrypted_api_key.ciphertext
            nonce = encrypted_api_key.nonce
            key_version = encrypted_api_key.key_version
            key_hint = encrypted_api_key.hint
            key_audience = encrypted_api_key.audience
        c.execute(
            """INSERT INTO user_settings (
                 user_id, llm_base_url, llm_api_key,
                 llm_api_key_ciphertext, llm_api_key_nonce,
                 llm_api_key_version, llm_api_key_hint,
                 llm_api_key_audience, llm_protocol, llm_model, force_demo, updated_at
               )
               VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 llm_base_url = excluded.llm_base_url,
                 llm_api_key = NULL,
                 llm_api_key_ciphertext = excluded.llm_api_key_ciphertext,
                 llm_api_key_nonce = excluded.llm_api_key_nonce,
                 llm_api_key_version = excluded.llm_api_key_version,
                 llm_api_key_hint = excluded.llm_api_key_hint,
                 llm_api_key_audience = excluded.llm_api_key_audience,
                 llm_protocol = excluded.llm_protocol,
                 llm_model = excluded.llm_model,
                 force_demo = excluded.force_demo,
                 updated_at = excluded.updated_at""",
            (
                user_id,
                base_url,
                ciphertext,
                nonce,
                key_version,
                key_hint,
                key_audience,
                protocol,
                model,
                force_demo,
                _now(),
            ),
        )


def list_legacy_llm_keys() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """SELECT user_id, llm_api_key
               FROM user_settings
               WHERE llm_api_key IS NOT NULL
                 AND TRIM(llm_api_key) != ''"""
        ).fetchall()
    return [dict(row) for row in rows]


def migrate_legacy_llm_keys(
    encrypt: Callable[[str, str, str | None], EncryptedSecret],
) -> int:
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        rows = c.execute(
            """SELECT user_id, llm_api_key, llm_base_url
               FROM user_settings
               WHERE llm_api_key IS NOT NULL
                 AND TRIM(llm_api_key) != ''"""
        ).fetchall()
        for row in rows:
            encrypted = encrypt(
                row["llm_api_key"],
                row["user_id"],
                row["llm_base_url"],
            )
            updated = c.execute(
                """UPDATE user_settings
                   SET llm_api_key = NULL,
                       llm_api_key_ciphertext = ?,
                       llm_api_key_nonce = ?,
                       llm_api_key_version = ?,
                       llm_api_key_hint = ?,
                       llm_api_key_audience = ?,
                       updated_at = ?
                   WHERE user_id = ? AND llm_api_key = ?""",
                (
                    encrypted.ciphertext,
                    encrypted.nonce,
                    encrypted.key_version,
                    encrypted.hint,
                    encrypted.audience,
                    _now(),
                    row["user_id"],
                    row["llm_api_key"],
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("legacy credential changed during migration")
        return len(rows)


def migrate_unbound_llm_keys(
    rewrap: Callable[[EncryptedSecret, str, str | None], EncryptedSecret],
) -> int:
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        rows = c.execute(
            """SELECT *
               FROM user_settings
               WHERE llm_api_key_ciphertext IS NOT NULL
                 AND (
                   llm_api_key_audience IS NULL
                   OR TRIM(llm_api_key_audience) = ''
                 )"""
        ).fetchall()
        for row in rows:
            current = EncryptedSecret(
                ciphertext=row["llm_api_key_ciphertext"],
                nonce=row["llm_api_key_nonce"],
                key_version=row["llm_api_key_version"],
                hint=row["llm_api_key_hint"] or "",
                audience="",
            )
            encrypted = rewrap(current, row["user_id"], row["llm_base_url"])
            c.execute(
                """UPDATE user_settings
                   SET llm_api_key_ciphertext = ?,
                       llm_api_key_nonce = ?,
                       llm_api_key_version = ?,
                       llm_api_key_hint = ?,
                       llm_api_key_audience = ?,
                       updated_at = ?
                   WHERE user_id = ?
                     AND llm_api_key_ciphertext = ?
                     AND (
                       llm_api_key_audience IS NULL
                       OR TRIM(llm_api_key_audience) = ''
                     )""",
                (
                    encrypted.ciphertext,
                    encrypted.nonce,
                    encrypted.key_version,
                    encrypted.hint,
                    encrypted.audience,
                    _now(),
                    row["user_id"],
                    row["llm_api_key_ciphertext"],
                ),
            )
        return len(rows)


# --- Reference answers (persistent memory per question) ---


def get_reference_answer(user_id: str, question_id: str) -> dict | None:
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM user_reference_answers WHERE user_id = ? AND question_id = ?",
            (user_id, question_id),
        ).fetchone()
    return dict(r) if r else None


def upsert_reference_answer(user_id: str, question_id: str, reference_text: str) -> dict:
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO user_reference_answers (user_id, question_id, reference_text, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, question_id) DO UPDATE SET
                 reference_text = excluded.reference_text,
                 updated_at = excluded.updated_at""",
            (user_id, question_id, reference_text, now),
        )
    return get_reference_answer(user_id, question_id) or {}


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


def get_mock_session(session_id: str, user_id: str) -> dict:
    with _conn() as c:
        r = c.execute(
            "SELECT * FROM mock_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
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


def update_mock_session(session_id: str, user_id: str, **kwargs: Any) -> dict:
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
    vals.append(user_id)
    with _conn() as c:
        cursor = c.execute(
            f"UPDATE mock_sessions SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
            vals,
        )
        if cursor.rowcount == 0:
            raise KeyError(session_id)
    return get_mock_session(session_id, user_id)


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


# --- LLM-101-CN exercise attempts ---


def create_exercise_attempt(
    user_id: str,
    exercise_id: str,
    answers: dict,
    status: str,
    score: int | None,
    notes: str,
    *,
    feedback: dict | None = None,
    revealed: bool = False,
) -> dict:
    attempt_id = str(uuid.uuid4())
    created_at = _now()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO exercise_attempts
                (id, user_id, exercise_id, answers_json, status, score,
                 feedback_json, revealed_at, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id, user_id, exercise_id,
                json.dumps(answers, ensure_ascii=False), status, score,
                json.dumps(feedback or {}, ensure_ascii=False),
                created_at if revealed else None, notes, created_at,
            ),
        )
    return {
        "id": attempt_id, "user_id": user_id, "exercise_id": exercise_id,
        "status": status, "score": score, "created_at": created_at,
    }


def list_exercise_attempts(user_id: str, limit: int = 100) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, exercise_id, status, score, created_at FROM exercise_attempts "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, max(1, min(limit, 500))),
        ).fetchall()
    return [dict(row) for row in rows]


def get_exercise_progress(user_id: str) -> dict:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT exercise_id, COUNT(*) AS attempts, MAX(score) AS best_score,
                   MAX(created_at) AS last_attempt_at
            FROM exercise_attempts WHERE user_id = ? GROUP BY exercise_id
            ORDER BY last_attempt_at DESC
            """,
            (user_id,),
        ).fetchall()
    items = [dict(row) for row in rows]
    return {
        "total_attempts": sum(item["attempts"] for item in items),
        "completed_items": len(items),
        "items": items,
    }


def exercise_attempt_summary_rows(user_id: str) -> list[dict]:
    """Read all attempts for a user's topic/level aggregation, without a UI page limit."""
    with _conn() as c:
        rows = c.execute(
            "SELECT exercise_id, status, score FROM exercise_attempts WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


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


def create_content_source(
    *,
    source_path: str,
    source_url: str,
    retrieved_at: str,
    source_title: str | None = None,
    publisher: str | None = None,
    rights_note: str | None = None,
    content_item_id: str | None = None,
) -> dict:
    source_id = str(uuid.uuid4())
    now = _now()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO content_sources (
                id, content_item_id, source_path, source_url, source_title,
                publisher, retrieved_at, rights_note, status, created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                source_id,
                content_item_id,
                source_path,
                source_url,
                source_title,
                publisher,
                retrieved_at,
                rights_note,
                now,
                now,
            ),
        )
    return get_content_source(source_id)


def get_content_source(source_id: str) -> dict:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM content_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
    if row is None:
        raise KeyError(source_id)
    return dict(row)


def list_content_sources(status: str | None = None) -> list[dict]:
    with _conn() as c:
        if status:
            rows = c.execute(
                """
                SELECT * FROM content_sources
                WHERE status = ?
                ORDER BY created_at DESC, id DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM content_sources
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def list_content_takedown_events(source_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            """
            SELECT * FROM content_takedown_log
            WHERE source_id = ?
            ORDER BY created_at, id
            """,
            (source_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_content_takedown_event(event_id: str) -> dict:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM content_takedown_log WHERE id = ?",
            (event_id,),
        ).fetchone()
    if row is None:
        raise KeyError(event_id)
    return dict(row)


def record_content_takedown(
    source_id: str,
    actor_user_id: str,
    action: str,
    reason: str,
) -> dict:
    status_by_action = {
        "requested": "takedown_requested",
        "removed": "removed",
        "restored": "active",
    }
    if action not in status_by_action:
        raise ValueError("invalid takedown action")
    event_id = str(uuid.uuid4())
    now = _now()
    with closing(_conn()) as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            existing = c.execute(
                "SELECT 1 FROM content_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
            if existing is None:
                raise KeyError(source_id)
            c.execute(
                """
                UPDATE content_sources
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status_by_action[action], now, source_id),
            )
            c.execute(
                """
                INSERT INTO content_takedown_log (
                    id, source_id, actor_user_id, action, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, source_id, actor_user_id, action, reason, now),
            )
            c.commit()
        except Exception:
            c.rollback()
            raise
    return {
        "source": get_content_source(source_id),
        "event": get_content_takedown_event(event_id),
    }


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
