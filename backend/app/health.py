"""Small, public health checks for orchestrators and load balancers."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import settings
from app.db.migrations import current_schema_version, validate_current_schema
from app.interview.questions import load_questions
from app.privacy.tombstones import PrivacyLedgerError, validate_ledger


class NotReady(RuntimeError):
    """Raised when the API must not receive production traffic."""


def readiness() -> dict:
    database = Path(settings.sqlite_path).resolve()
    if not database.is_file():
        raise NotReady("database unavailable")
    try:
        with closing(
            sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        ) as connection:
            if connection.execute("SELECT 1").fetchone() != (1,):
                raise NotReady("database unavailable")
            validate_current_schema(connection)
            schema_version = current_schema_version(connection)
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        raise NotReady("database unavailable") from exc
    if not schema_version:
        raise NotReady("database unavailable")
    try:
        validate_ledger()
    except PrivacyLedgerError as exc:
        raise NotReady("privacy ledger unavailable") from exc
    try:
        question_count = len(load_questions())
    except Exception as exc:
        raise NotReady("question bank unavailable") from exc
    if question_count == 0:
        raise NotReady("question bank unavailable")
    return {
        "status": "ready",
        "database": "ok",
        "schema_version": schema_version,
        "questions": question_count,
    }
