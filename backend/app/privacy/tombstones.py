"""Durable, append-only deletion ledger outside restorable app snapshots."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


LEDGER_SCHEMA_VERSION = "20260829_001"
USER_OWNED_TABLES = (
    "auth_sessions",
    "user_answers",
    "exercise_attempts",
    "mock_sessions",
    "lab_completions",
    "review_cards",
    "user_reference_answers",
    "user_settings",
)

METADATA_DDL = """
CREATE TABLE privacy_ledger_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version TEXT NOT NULL,
    ledger_id TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""
DELETIONS_DDL = """
CREATE TABLE account_deletions (
    user_id TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL
)
"""
NO_UPDATE_DDL = """
CREATE TRIGGER account_deletions_no_update
BEFORE UPDATE ON account_deletions
BEGIN
    SELECT RAISE(ABORT, 'account deletion ledger is append-only');
END
"""
NO_DELETE_DDL = """
CREATE TRIGGER account_deletions_no_delete
BEFORE DELETE ON account_deletions
BEGIN
    SELECT RAISE(ABORT, 'account deletion ledger is append-only');
END
"""
METADATA_NO_UPDATE_DDL = """
CREATE TRIGGER privacy_ledger_metadata_no_update
BEFORE UPDATE ON privacy_ledger_metadata
BEGIN
    SELECT RAISE(ABORT, 'privacy ledger metadata is immutable');
END
"""
METADATA_NO_DELETE_DDL = """
CREATE TRIGGER privacy_ledger_metadata_no_delete
BEFORE DELETE ON privacy_ledger_metadata
BEGIN
    SELECT RAISE(ABORT, 'privacy ledger metadata is immutable');
END
"""


class PrivacyLedgerError(RuntimeError):
    """Raised when deletion history is missing or cannot be trusted."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_ddl(value: str) -> str:
    return " ".join(value.split()).lower()


def _path() -> Path:
    return Path(settings.privacy_ledger_path).resolve()


def _read_connection() -> sqlite3.Connection:
    path = _path()
    if not path.is_file():
        raise PrivacyLedgerError("privacy deletion ledger is missing")
    try:
        return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise PrivacyLedgerError("privacy deletion ledger is unreadable") from exc


def _write_connection() -> sqlite3.Connection:
    path = _path()
    if not path.is_file():
        raise PrivacyLedgerError("privacy deletion ledger is missing")
    try:
        connection = sqlite3.connect(str(path))
        connection.execute("PRAGMA secure_delete = ON")
        return connection
    except sqlite3.Error as exc:
        raise PrivacyLedgerError("privacy deletion ledger is unreadable") from exc


def initialize_ledger() -> Path:
    """Explicitly create a new ledger; never repair or replace an existing file."""

    path = _path()
    if path.exists():
        raise PrivacyLedgerError("privacy deletion ledger already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(str(path))) as connection:
            connection.execute("PRAGMA secure_delete = ON")
            connection.execute("BEGIN IMMEDIATE")
            for statement in (
                METADATA_DDL,
                DELETIONS_DDL,
                NO_UPDATE_DDL,
                NO_DELETE_DDL,
                METADATA_NO_UPDATE_DDL,
                METADATA_NO_DELETE_DDL,
            ):
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO privacy_ledger_metadata
                    (singleton, schema_version, ledger_id, created_at)
                VALUES (1, ?, ?, ?)
                """,
                (LEDGER_SCHEMA_VERSION, settings.privacy_ledger_id, _now()),
            )
            connection.commit()
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        validate_ledger()
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def upgrade_legacy_ledger() -> Path:
    """Atomically add identity and append-only guards to the exact legacy schema."""

    path = _path()
    if not path.is_file():
        raise PrivacyLedgerError("legacy privacy deletion ledger is missing")
    try:
        with closing(_write_connection()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """
                    SELECT type, name, sql FROM sqlite_master
                    WHERE name NOT LIKE 'sqlite_%'
                      AND type IN ('table', 'trigger', 'index')
                    """
                ).fetchall()
                actual = {
                    (row[0], row[1]): _normalize_ddl(row[2] or "")
                    for row in rows
                    if row[2] is not None
                }
                expected_legacy = {
                    ("table", "account_deletions"): _normalize_ddl(DELETIONS_DDL)
                }
                if actual != expected_legacy:
                    raise PrivacyLedgerError(
                        "legacy privacy deletion ledger schema is unsupported"
                    )
                original_rows = connection.execute(
                    """
                    SELECT user_id, deleted_at
                    FROM account_deletions ORDER BY user_id
                    """
                ).fetchall()
                for statement in (
                    METADATA_DDL,
                    NO_UPDATE_DDL,
                    NO_DELETE_DDL,
                    METADATA_NO_UPDATE_DDL,
                    METADATA_NO_DELETE_DDL,
                ):
                    connection.execute(statement)
                connection.execute(
                    """
                    INSERT INTO privacy_ledger_metadata
                        (singleton, schema_version, ledger_id, created_at)
                    VALUES (1, ?, ?, ?)
                    """,
                    (LEDGER_SCHEMA_VERSION, settings.privacy_ledger_id, _now()),
                )
                preserved_rows = connection.execute(
                    """
                    SELECT user_id, deleted_at
                    FROM account_deletions ORDER BY user_id
                    """
                ).fetchall()
                if preserved_rows != original_rows:
                    raise PrivacyLedgerError(
                        "legacy privacy deletion ledger rows changed during upgrade"
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    except PrivacyLedgerError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise PrivacyLedgerError(
            "legacy privacy deletion ledger upgrade failed"
        ) from exc
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    validate_ledger()
    return path


def validate_ledger() -> None:
    expected = {
        ("table", "privacy_ledger_metadata"): METADATA_DDL,
        ("table", "account_deletions"): DELETIONS_DDL,
        ("trigger", "account_deletions_no_update"): NO_UPDATE_DDL,
        ("trigger", "account_deletions_no_delete"): NO_DELETE_DDL,
        ("trigger", "privacy_ledger_metadata_no_update"): METADATA_NO_UPDATE_DDL,
        ("trigger", "privacy_ledger_metadata_no_delete"): METADATA_NO_DELETE_DDL,
    }
    try:
        with closing(_read_connection()) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            rows = connection.execute(
                """
                SELECT type, name, sql FROM sqlite_master
                WHERE name NOT LIKE 'sqlite_%' AND type IN ('table', 'trigger', 'index')
                """
            ).fetchall()
            actual = {
                (row[0], row[1]): _normalize_ddl(row[2] or "")
                for row in rows
                if row[2] is not None
            }
            metadata = connection.execute(
                """
                SELECT schema_version, ledger_id
                FROM privacy_ledger_metadata WHERE singleton = 1
                """
            ).fetchall()
    except (OSError, sqlite3.Error, PrivacyLedgerError) as exc:
        if isinstance(exc, PrivacyLedgerError):
            raise
        raise PrivacyLedgerError("privacy deletion ledger is invalid") from exc
    normalized_expected = {
        key: _normalize_ddl(value) for key, value in expected.items()
    }
    if (
        integrity != ("ok",)
        or actual != normalized_expected
        or metadata != [(LEDGER_SCHEMA_VERSION, settings.privacy_ledger_id)]
    ):
        raise PrivacyLedgerError("privacy deletion ledger is invalid")


def ensure_ledger() -> None:
    if not _path().exists() and settings.app_env in {"development", "test"}:
        initialize_ledger()
    validate_ledger()


def record_deletion(user_id: str) -> None:
    validate_ledger()
    try:
        with closing(_write_connection()) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO account_deletions (user_id, deleted_at)
                VALUES (?, ?)
                """,
                (user_id, _now()),
            )
            connection.commit()
    except sqlite3.Error as exc:
        raise PrivacyLedgerError("privacy deletion could not be recorded") from exc


def is_deleted(user_id: str) -> bool:
    """Use a constant-time lookup on the request path after startup validation."""

    try:
        with closing(_read_connection()) as connection:
            metadata = connection.execute(
                """
                SELECT schema_version, ledger_id
                FROM privacy_ledger_metadata WHERE singleton = 1
                """
            ).fetchone()
            if metadata != (LEDGER_SCHEMA_VERSION, settings.privacy_ledger_id):
                raise PrivacyLedgerError("privacy deletion ledger identity is invalid")
            row = connection.execute(
                "SELECT 1 FROM account_deletions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise PrivacyLedgerError("privacy deletion ledger is invalid") from exc
    return row == (1,)


def apply_deletions(database_path: str | Path) -> int:
    validate_ledger()
    target = Path(database_path).resolve()
    if not target.is_file():
        return 0
    with closing(_read_connection()) as ledger:
        user_ids = [
            row[0]
            for row in ledger.execute(
                "SELECT user_id FROM account_deletions ORDER BY deleted_at"
            ).fetchall()
        ]
    if not user_ids:
        return 0
    with closing(sqlite3.connect(str(target))) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("BEGIN IMMEDIATE")
        try:
            for user_id in user_ids:
                for table in USER_OWNED_TABLES:
                    connection.execute(
                        f"DELETE FROM {table} WHERE user_id = ?",
                        (user_id,),
                    )
                connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return len(user_ids)
