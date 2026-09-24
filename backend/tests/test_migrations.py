from __future__ import annotations

import sqlite3
import threading
import time

import pytest

from app.config import settings
from app.db import store
from app.db import migrations as migration_module
from app.db.migrations import (
    Migration,
    current_schema_version,
    run_migrations,
    validate_current_schema,
)


def test_llm101_attempt_migration_is_current_and_validated(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    store.init_db()
    with sqlite3.connect(database) as connection:
        assert current_schema_version(connection) == "20260923_001"
        assert {row[1] for row in connection.execute("PRAGMA table_info(exercise_attempts)")} >= {
            "id", "user_id", "exercise_id", "answers_json", "status", "score", "created_at"
        }
        validate_current_schema(connection)


def _database(tmp_path, monkeypatch):
    database = tmp_path / "migrations.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    return database


def _previous_schema_database(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    store.init_db()
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE user_settings RENAME TO user_settings_current")
        connection.execute(
            """
            CREATE TABLE user_settings (
                user_id TEXT PRIMARY KEY,
                llm_base_url TEXT,
                llm_api_key TEXT,
                llm_api_key_ciphertext TEXT,
                llm_api_key_nonce TEXT,
                llm_api_key_version TEXT,
                llm_api_key_hint TEXT,
                llm_api_key_audience TEXT,
                llm_model TEXT,
                force_demo INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("DROP TABLE user_settings_current")
        connection.execute("DROP TABLE exercise_attempts")
        connection.execute("DELETE FROM schema_migrations WHERE version > '20260829_003'")
    return database


def test_protocol_migration_defaults_existing_rows_to_openai(tmp_path, monkeypatch):
    database = _previous_schema_database(tmp_path, monkeypatch)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO user_settings (user_id, force_demo, updated_at) VALUES (?, 0, ?)",
            ("existing-user", "2026-08-30T00:00:00+00:00"),
        )
        run_migrations(connection, migrations=migration_module.MIGRATIONS[:-1])
        row = connection.execute(
            "SELECT llm_protocol FROM user_settings WHERE user_id = ?",
            ("existing-user",),
        ).fetchone()
        assert row[0] == "openai_chat"
        assert current_schema_version(connection) == "20260830_004"


@pytest.mark.parametrize(
    "protocol_definition",
    [
        "TEXT DEFAULT 'openai_chat' CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages'))",
        "TEXT NOT NULL DEFAULT 'anthropic_messages' CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages'))",
        "TEXT NOT NULL DEFAULT 'openai_chat' CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages', 'forged'))",
        "TEXT NOT NULL DEFAULT 'openai_chat' CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages', 'forged')) /* CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages')) */",
        "TEXT NOT NULL DEFAULT 'openai_chat' CHECK (llm_protocol IN ('openai_chat', 'anthropic_messages', 'forged')) CONSTRAINT \"check (llm_protocol in ('openai_chat', 'anthropic_messages'))\" CHECK (1)",
    ],
)
def test_current_schema_rejects_forged_v004_protocol_constraints(
    tmp_path,
    monkeypatch,
    protocol_definition,
):
    database = _database(tmp_path, monkeypatch)
    store.init_db()
    with sqlite3.connect(database) as connection:
        connection.execute("ALTER TABLE user_settings RENAME TO user_settings_valid")
        connection.execute(
            f"""
            CREATE TABLE user_settings (
                user_id TEXT PRIMARY KEY,
                llm_base_url TEXT,
                llm_api_key TEXT,
                llm_api_key_ciphertext TEXT,
                llm_api_key_nonce TEXT,
                llm_api_key_version TEXT,
                llm_api_key_hint TEXT,
                llm_api_key_audience TEXT,
                llm_protocol {protocol_definition},
                llm_model TEXT,
                force_demo INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("DROP TABLE user_settings_valid")

        with pytest.raises(RuntimeError, match="database user settings protocol is invalid"):
            validate_current_schema(connection)


def test_store_records_ordered_schema_migrations_once(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)

    store.init_db()
    store.init_db()

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        backup_table = connection.execute(
            """SELECT name FROM sqlite_master
               WHERE type = 'table' AND name = 'backup_history'"""
        ).fetchone()
        version = current_schema_version(connection)
    assert rows == [
        ("20260829_001", "existing_schema_baseline"),
        ("20260829_002", "backup_history"),
        ("20260829_003", "content_provenance"),
        ("20260830_004", "llm_protocol"),
        ("20260923_001", "llm101_exercise_attempts"),
    ]
    assert backup_table == ("backup_history",)
    assert version == "20260923_001"


def test_reinitializing_preserves_existing_user_data(tmp_path, monkeypatch):
    _database(tmp_path, monkeypatch)
    store.init_db()
    answer = store.save_quiz_answer(
        "user-a",
        "question-a",
        "preserved answer",
        4,
        80,
    )

    store.init_db()

    history = store.list_quiz_history("user-a")
    assert history[0]["id"] == answer["id"]
    assert history[0]["answer_text"] == "preserved answer"


def test_failed_migration_rolls_back_schema_and_ledger(tmp_path):
    database = tmp_path / "failed-migration.db"

    def fail_after_ddl(connection):
        connection.execute("CREATE TABLE should_rollback (id TEXT)")
        raise RuntimeError("migration failed")

    migration = Migration("20990101_001", "failing", fail_after_ddl)
    with sqlite3.connect(database) as connection:
        with pytest.raises(RuntimeError, match="migration failed"):
            run_migrations(connection, migrations=(migration,))

    with sqlite3.connect(database) as connection:
        table = connection.execute(
            """SELECT name FROM sqlite_master
               WHERE type = 'table' AND name = 'should_rollback'"""
        ).fetchone()
        recorded = connection.execute(
            """SELECT version FROM schema_migrations
               WHERE version = '20990101_001'"""
        ).fetchone()
    assert table is None
    assert recorded is None


def test_content_provenance_ddl_stays_inside_migration_transaction(tmp_path):
    database = tmp_path / "failed-provenance.db"

    class FailingConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if "CREATE TABLE IF NOT EXISTS content_takedown_log" in sql:
                raise RuntimeError("injected provenance DDL failure")
            return super().execute(sql, parameters)

    with sqlite3.connect(database, factory=FailingConnection) as connection:
        connection.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE content_items (id TEXT PRIMARY KEY)")
        connection.commit()
        migration = Migration(
            "20260829_003",
            "content_provenance",
            migration_module._create_content_provenance,
        )
        with pytest.raises(RuntimeError, match="injected provenance DDL failure"):
            run_migrations(connection, migrations=(migration,))

    with sqlite3.connect(database) as connection:
        source_table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'content_sources'
            """
        ).fetchone()
        recorded = connection.execute(
            """
            SELECT version FROM schema_migrations
            WHERE version = '20260829_003'
            """
        ).fetchone()
    assert source_table is None
    assert recorded is None


def test_migration_versions_must_be_unique_and_ordered(tmp_path):
    database = tmp_path / "invalid-migrations.db"
    no_op = lambda connection: None
    migrations = (
        Migration("2", "later", no_op),
        Migration("1", "earlier", no_op),
    )

    with sqlite3.connect(database) as connection:
        with pytest.raises(ValueError, match="strictly ordered"):
            run_migrations(connection, migrations=migrations)


def test_concurrent_migration_runners_apply_each_version_once(tmp_path):
    database = tmp_path / "concurrent.db"
    started = threading.Barrier(2)
    initial_reads = threading.Barrier(2)
    errors: list[Exception] = []

    class SynchronizedConnection(sqlite3.Connection):
        synchronized = False

        def execute(self, sql, parameters=()):
            if (
                not self.synchronized
                and sql.strip() == "SELECT version FROM schema_migrations"
            ):
                self.synchronized = True
                initial_reads.wait(timeout=5)
            return super().execute(sql, parameters)

    def slow_migration(connection):
        connection.execute("CREATE TABLE IF NOT EXISTS concurrent_table (id TEXT)")
        time.sleep(0.2)

    migrations = (Migration("20990101_001", "concurrent", slow_migration),)

    def migrate():
        try:
            with sqlite3.connect(
                database,
                timeout=5,
                factory=SynchronizedConnection,
            ) as connection:
                started.wait()
                run_migrations(connection, migrations=migrations)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=migrate) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    with sqlite3.connect(database) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
    assert count == 1


def test_concurrent_store_initialization_is_idempotent(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    errors: list[Exception] = []
    started = threading.Barrier(2)

    def initialize():
        try:
            started.wait()
            store.init_db()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=initialize) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    with sqlite3.connect(database) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert versions == [
        ("20260829_001",),
        ("20260829_002",),
        ("20260829_003",),
        ("20260830_004",),
        ("20260923_001",),
    ]
