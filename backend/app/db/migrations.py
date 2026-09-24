"""Ordered, transactional SQLite schema migrations."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable


MigrationApply = Callable[[sqlite3.Connection], None]

EXPECTED_TABLE_COLUMNS = {
    "auth_sessions": {
        "id", "user_id", "token_hash", "expires_at", "created_at", "revoked_at",
    },
    "backup_history": {
        "id", "file_name", "sha256", "size_bytes", "schema_version",
        "created_at", "verified_at",
    },
    "content_changelog": {"id", "action", "item_id", "title", "published_at"},
    "content_items": {
        "id", "item_type", "source_path", "status", "title", "audit_checks",
        "audit_report", "quality_score", "reviewer_note", "created_at", "updated_at",
    },
    "content_publish_log": {
        "id", "item_id", "dest_paths", "backup_paths", "published_at", "rolled_back",
    },
    "content_sources": {
        "id", "content_item_id", "source_path", "source_url", "source_title",
        "publisher", "retrieved_at", "rights_note", "status", "created_at",
        "updated_at",
    },
    "content_takedown_log": {
        "id", "source_id", "actor_user_id", "action", "reason", "created_at",
    },
    "content_runs": {
        "id", "run_type", "status", "summary", "items_created", "started_at",
        "finished_at",
    },
    "exercise_attempts": {
        "id", "user_id", "exercise_id", "answers_json", "status", "score",
        "feedback_json", "revealed_at", "notes", "created_at",
    },
    "lab_completions": {"id", "user_id", "lab_id", "notes", "completed_at"},
    "mock_sessions": {
        "id", "user_id", "mode", "vendor", "focus", "stage", "transcript",
        "scores", "report", "recommended_lab_ids", "created_at", "updated_at",
        "stage_started_at",
    },
    "review_cards": {
        "user_id", "question_id", "easiness", "repetitions", "interval_days",
        "next_review_at", "last_quality", "updated_at",
    },
    "schema_migrations": {"version", "name", "applied_at"},
    "user_answers": {
        "id", "user_id", "question_id", "answer_text", "self_score", "ai_score",
        "created_at", "reference_answer", "feedback", "model_name",
        "comparison_detail",
    },
    "user_reference_answers": {
        "user_id", "question_id", "reference_text", "updated_at",
    },
    "user_settings": {
        "user_id", "llm_base_url", "llm_api_key", "llm_api_key_ciphertext",
        "llm_api_key_nonce", "llm_api_key_version", "llm_api_key_hint",
        "llm_api_key_audience", "llm_protocol", "llm_model", "force_demo", "updated_at",
    },
    "users": {"id", "email", "password_hash", "role", "created_at", "updated_at"},
}

EXPECTED_PRIMARY_KEYS = {
    "auth_sessions": ("id",),
    "backup_history": ("id",),
    "content_changelog": ("id",),
    "content_items": ("id",),
    "content_publish_log": ("id",),
    "content_sources": ("id",),
    "content_takedown_log": ("id",),
    "content_runs": ("id",),
    "exercise_attempts": ("id",),
    "lab_completions": ("id",),
    "mock_sessions": ("id",),
    "review_cards": ("user_id", "question_id"),
    "schema_migrations": ("version",),
    "user_answers": ("id",),
    "user_reference_answers": ("user_id", "question_id"),
    "user_settings": ("user_id",),
    "users": ("id",),
}


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    apply: MigrationApply


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_existing_schema(connection: sqlite3.Connection) -> None:
    required_columns = {
        "users": {"id", "email", "password_hash", "role"},
        "auth_sessions": {"id", "user_id", "token_hash", "expires_at"},
        "user_answers": {"id", "user_id", "question_id", "answer_text"},
        "mock_sessions": {"id", "user_id", "mode", "stage"},
        "user_settings": {
            "user_id",
            "llm_base_url",
            "llm_api_key_ciphertext",
            "llm_api_key_nonce",
            "llm_api_key_version",
            "llm_api_key_audience",
        },
    }
    for table, expected in required_columns.items():
        columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = expected - columns
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(f"database baseline is missing {table}: {names}")


def _create_backup_history(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_history (
            id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            schema_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            verified_at TEXT NOT NULL
        )
        """
    )


CONTENT_SOURCES_DDL = """
        CREATE TABLE IF NOT EXISTS content_sources (
            id TEXT PRIMARY KEY,
            content_item_id TEXT,
            source_path TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_title TEXT,
            publisher TEXT,
            retrieved_at TEXT NOT NULL,
            rights_note TEXT,
            status TEXT NOT NULL
                CHECK (status IN ('active', 'takedown_requested', 'removed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (content_item_id) REFERENCES content_items(id)
                ON DELETE SET NULL
        )
"""
CONTENT_TAKEDOWN_LOG_DDL = """
        CREATE TABLE IF NOT EXISTS content_takedown_log (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            actor_user_id TEXT,
            action TEXT NOT NULL
                CHECK (action IN ('requested', 'removed', 'restored')),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (source_id) REFERENCES content_sources(id)
                ON DELETE RESTRICT,
            FOREIGN KEY (actor_user_id) REFERENCES users(id)
                ON DELETE SET NULL
        )
"""
CONTENT_SOURCES_INDEX_DDL = """
        CREATE INDEX IF NOT EXISTS idx_content_sources_status
            ON content_sources(status)
"""
CONTENT_TAKEDOWN_INDEX_DDL = """
        CREATE INDEX IF NOT EXISTS idx_content_takedown_log_source
            ON content_takedown_log(source_id, created_at)
"""
CONTENT_TAKEDOWN_NO_UPDATE_DDL = """
        CREATE TRIGGER IF NOT EXISTS content_takedown_log_no_update
        BEFORE UPDATE ON content_takedown_log
        WHEN
            NEW.id IS NOT OLD.id
            OR NEW.source_id IS NOT OLD.source_id
            OR NEW.action IS NOT OLD.action
            OR NEW.reason IS NOT OLD.reason
            OR NEW.created_at IS NOT OLD.created_at
            OR (OLD.actor_user_id IS NULL AND NEW.actor_user_id IS NOT NULL)
            OR (
                OLD.actor_user_id IS NOT NULL
                AND NEW.actor_user_id IS NOT NULL
                AND NEW.actor_user_id IS NOT OLD.actor_user_id
            )
        BEGIN
            SELECT RAISE(ABORT, 'content takedown audit log is append-only');
        END
"""
CONTENT_TAKEDOWN_NO_DELETE_DDL = """
        CREATE TRIGGER IF NOT EXISTS content_takedown_log_no_delete
        BEFORE DELETE ON content_takedown_log
        BEGIN
            SELECT RAISE(ABORT, 'content takedown audit log is append-only');
        END
"""


def _create_content_provenance(connection: sqlite3.Connection) -> None:
    for statement in (
        CONTENT_SOURCES_DDL,
        CONTENT_TAKEDOWN_LOG_DDL,
        CONTENT_SOURCES_INDEX_DDL,
        CONTENT_TAKEDOWN_INDEX_DDL,
        CONTENT_TAKEDOWN_NO_UPDATE_DDL,
        CONTENT_TAKEDOWN_NO_DELETE_DDL,
    ):
        connection.execute(statement)


def _add_llm_protocol(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(user_settings)").fetchall()
    }
    if "llm_protocol" not in columns:
        connection.execute(
            "ALTER TABLE user_settings "
            "ADD COLUMN llm_protocol TEXT NOT NULL DEFAULT 'openai_chat' "
            "CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages'))"
        )


def _create_exercise_attempts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS exercise_attempts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            status TEXT NOT NULL,
            score INTEGER,
            feedback_json TEXT,
            revealed_at TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_exercise_attempts_user "
        "ON exercise_attempts(user_id, created_at)"
    )


MIGRATIONS = (
    Migration("20260829_001", "existing_schema_baseline", _require_existing_schema),
    Migration("20260829_002", "backup_history", _create_backup_history),
    Migration("20260829_003", "content_provenance", _create_content_provenance),
    Migration("20260830_004", "llm_protocol", _add_llm_protocol),
    Migration("20260923_001", "llm101_exercise_attempts", _create_exercise_attempts),
)


def expected_schema_version() -> str:
    return MIGRATIONS[-1].version


def _migration_ledger(connection: sqlite3.Connection) -> list[tuple[str, str]]:
    try:
        return connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError("schema migration ledger is missing") from exc


def _normalize_ddl(value: str) -> str:
    normalized = " ".join(value.split()).lower()
    return normalized.replace(" if not exists ", " ")


def _validate_provenance_guards(connection: sqlite3.Connection) -> None:
    expected_objects = {
        ("table", "content_sources"): CONTENT_SOURCES_DDL,
        ("table", "content_takedown_log"): CONTENT_TAKEDOWN_LOG_DDL,
        ("index", "idx_content_sources_status"): CONTENT_SOURCES_INDEX_DDL,
        ("index", "idx_content_takedown_log_source"): CONTENT_TAKEDOWN_INDEX_DDL,
        ("trigger", "content_takedown_log_no_update"):
            CONTENT_TAKEDOWN_NO_UPDATE_DDL,
        ("trigger", "content_takedown_log_no_delete"):
            CONTENT_TAKEDOWN_NO_DELETE_DDL,
    }
    rows = connection.execute(
        """
        SELECT type, name, sql FROM sqlite_master
        WHERE name IN ('content_sources', 'content_takedown_log')
           OR (
               tbl_name IN ('content_sources', 'content_takedown_log')
               AND type IN ('index', 'trigger')
               AND sql IS NOT NULL
           )
        """
    ).fetchall()
    actual_objects = {
        (row[0], row[1]): _normalize_ddl(row[2] or "")
        for row in rows
    }
    normalized_expected = {
        key: _normalize_ddl(value)
        for key, value in expected_objects.items()
    }
    if actual_objects != normalized_expected:
        raise RuntimeError("database content governance guards are invalid")


_LLM_PROTOCOL_CHECK_TOKENS = (
    "check",
    "(",
    "llm_protocol",
    "in",
    "(",
    "'openai_chat'",
    ",",
    "'anthropic_messages'",
    ")",
    ")",
)


def _sqlite_ddl_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(value):
        if value.startswith("--", index):
            newline = value.find("\n", index + 2)
            index = len(value) if newline == -1 else newline + 1
            continue
        if value.startswith("/*", index):
            closing = value.find("*/", index + 2)
            index = len(value) if closing == -1 else closing + 2
            continue
        char = value[index]
        if char == "'":
            start = index
            index += 1
            while index < len(value):
                if value[index] == "'":
                    index += 2 if index + 1 < len(value) and value[index + 1] == "'" else 1
                    if index == len(value) or value[index - 2:index] != "''":
                        break
                else:
                    index += 1
            tokens.append(value[start:index].lower())
            continue
        if char in {'"', "`", "["}:
            closing = "]" if char == "[" else char
            index += 1
            while index < len(value):
                if value[index] == closing:
                    if index + 1 < len(value) and value[index + 1] == closing:
                        index += 2
                    else:
                        index += 1
                        break
                else:
                    index += 1
            continue
        if char.isalpha() or char == "_":
            start = index
            index += 1
            while index < len(value) and (value[index].isalnum() or value[index] == "_"):
                index += 1
            tokens.append(value[start:index].lower())
            continue
        if char in "(),":
            tokens.append(char)
        index += 1
    return tokens


def _has_llm_protocol_check(value: str) -> bool:
    tokens = _sqlite_ddl_tokens(value)
    expected = list(_LLM_PROTOCOL_CHECK_TOKENS)
    width = len(expected)
    return any(tokens[index:index + width] == expected for index in range(len(tokens)))


def _validate_llm_protocol_constraint(connection: sqlite3.Connection) -> None:
    columns = connection.execute("PRAGMA table_info(user_settings)").fetchall()
    protocol = next((row for row in columns if row[1] == "llm_protocol"), None)
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user_settings'"
    ).fetchone()

    if (
        protocol is None
        or protocol[3] != 1
        or protocol[4] != "'openai_chat'"
        or table is None
        or not _has_llm_protocol_check(table[0] or "")
    ):
        raise RuntimeError("database user settings protocol is invalid")


def _validate_schema_shape(
    connection: sqlite3.Connection,
    *,
    table_columns: dict[str, set[str]],
    primary_keys: dict[str, tuple[str, ...]],
    provenance_required: bool,
) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
    }
    if tables != set(table_columns):
        raise RuntimeError("database table set is invalid")
    for table, expected_columns in table_columns.items():
        info = connection.execute(f"PRAGMA table_info({table})").fetchall()
        columns = {row[1] for row in info}
        primary_key = tuple(
            row[1] for row in sorted(info, key=lambda row: row[5]) if row[5] > 0
        )
        if columns != expected_columns or primary_key != primary_keys[table]:
            raise RuntimeError(f"database table schema is invalid: {table}")
    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(auth_sessions)"
    ).fetchall()
    if not any(
        row[2] == "users" and row[3] == "user_id" and row[4] == "id"
        for row in foreign_keys
    ):
        raise RuntimeError("database session ownership constraint is missing")
    required_foreign_keys = {}
    if provenance_required:
        required_foreign_keys = {
            "content_sources": {
                ("content_items", "content_item_id", "id", "SET NULL"),
            },
            "content_takedown_log": {
                ("content_sources", "source_id", "id", "RESTRICT"),
                ("users", "actor_user_id", "id", "SET NULL"),
            },
        }
    if "exercise_attempts" in table_columns:
        required_foreign_keys["exercise_attempts"] = {
            ("users", "user_id", "id", "CASCADE"),
        }
    for table, expected_keys in required_foreign_keys.items():
        actual_keys = {
            (row[2], row[3], row[4], row[6])
            for row in connection.execute(
                f"PRAGMA foreign_key_list({table})"
            ).fetchall()
        }
        if not expected_keys.issubset(actual_keys):
            raise RuntimeError(
                f"database ownership constraint is missing: {table}"
            )
    for table, required_unique in (
        ("users", ("email",)),
        ("auth_sessions", ("token_hash",)),
    ):
        unique_columns = set()
        for index in connection.execute(f"PRAGMA index_list({table})").fetchall():
            if index[2]:
                columns = tuple(
                    row[2]
                    for row in connection.execute(
                        f"PRAGMA index_info({index[1]})"
                    ).fetchall()
                )
                unique_columns.add(columns)
        if required_unique not in unique_columns:
            raise RuntimeError(f"database unique constraint is missing: {table}")
    if "llm_protocol" in table_columns["user_settings"]:
        _validate_llm_protocol_constraint(connection)
    if provenance_required:
        _validate_provenance_guards(connection)


def validate_supported_schema(connection: sqlite3.Connection) -> str:
    recorded = _migration_ledger(connection)
    expected = [(migration.version, migration.name) for migration in MIGRATIONS]
    previous = expected[:-1]
    before_protocol = expected[:-2]
    legacy = expected[:2]
    if recorded == expected:
        _validate_schema_shape(
            connection,
            table_columns=EXPECTED_TABLE_COLUMNS,
            primary_keys=EXPECTED_PRIMARY_KEYS,
            provenance_required=True,
        )
        return expected[-1][0]
    if recorded == previous:
        previous_columns = {
            table: set(columns)
            for table, columns in EXPECTED_TABLE_COLUMNS.items()
            if table != "exercise_attempts"
        }
        _validate_schema_shape(
            connection,
            table_columns=previous_columns,
            primary_keys={table: key for table, key in EXPECTED_PRIMARY_KEYS.items() if table in previous_columns},
            provenance_required=True,
        )
        return previous[-1][0]
    if recorded == before_protocol:
        earlier_columns = {
            table: set(columns)
            for table, columns in EXPECTED_TABLE_COLUMNS.items()
            if table != "exercise_attempts"
        }
        earlier_columns["user_settings"].remove("llm_protocol")
        _validate_schema_shape(
            connection,
            table_columns=earlier_columns,
            primary_keys={table: key for table, key in EXPECTED_PRIMARY_KEYS.items() if table in earlier_columns},
            provenance_required=True,
        )
        return before_protocol[-1][0]
    if recorded == legacy:
        legacy_columns = {
            table: set(columns)
            for table, columns in EXPECTED_TABLE_COLUMNS.items()
            if table not in {"content_sources", "content_takedown_log", "exercise_attempts"}
        }
        legacy_columns["user_settings"].remove("llm_protocol")
        legacy_primary_keys = {
            table: primary_key
            for table, primary_key in EXPECTED_PRIMARY_KEYS.items()
            if table in legacy_columns
        }
        _validate_schema_shape(
            connection,
            table_columns=legacy_columns,
            primary_keys=legacy_primary_keys,
            provenance_required=False,
        )
        return legacy[-1][0]
    raise RuntimeError("database schema version is unsupported")


def validate_current_schema(connection: sqlite3.Connection) -> None:
    version = validate_supported_schema(connection)
    if version != expected_schema_version():
        raise RuntimeError("database schema version is unsupported")


def _validated(migrations: Iterable[Migration]) -> tuple[Migration, ...]:
    ordered = tuple(migrations)
    versions = [migration.version for migration in ordered]
    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise ValueError("migration versions must be unique and strictly ordered")
    return ordered


def run_migrations(
    connection: sqlite3.Connection,
    *,
    migrations: Iterable[Migration] = MIGRATIONS,
) -> list[str]:
    """Apply each pending migration in its own transaction."""

    ordered = _validated(migrations)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    completed: list[str] = []
    for migration in ordered:
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (migration.version,),
            ).fetchone()
            if existing is not None:
                connection.commit()
                continue
            migration.apply(connection)
            connection.execute(
                """
                INSERT INTO schema_migrations (version, name, applied_at)
                VALUES (?, ?, ?)
                """,
                (migration.version, migration.name, _now()),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        completed.append(migration.version)
    return completed


def current_schema_version(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else ""
