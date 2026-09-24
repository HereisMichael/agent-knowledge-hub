from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path

import pytest

from app.config import settings
from app.db import store
from app.db import backup as backup_module
from app.db.backup import BackupError, create_backup, restore_backup


def _database(tmp_path, monkeypatch) -> Path:
    database = tmp_path / "hub.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    store.init_db()
    return database


def test_backup_and_restore_preserve_data_without_leaking_manifest_content(
    tmp_path, monkeypatch
):
    database = _database(tmp_path, monkeypatch)
    answer_text = "private interview answer"
    store.save_quiz_answer("user-a", "question-a", answer_text, 4, 88)

    backup = create_backup(tmp_path / "backups")

    assert backup.path.exists()
    assert backup.manifest_path.exists()
    manifest_text = backup.manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["sha256"] == backup.sha256
    assert manifest["schema_version"] == "20260923_001"
    assert answer_text not in manifest_text
    assert str(database.parent) not in manifest_text

    store.save_quiz_answer("user-a", "question-b", "new answer", 3, 70)
    restored = restore_backup(
        backup.path,
        target_path=database,
        safety_dir=tmp_path / "pre-restore",
    )

    assert restored.safety_backup_path is not None
    assert restored.safety_backup_path.exists()
    history = store.list_quiz_history("user-a")
    assert [item["question_id"] for item in history] == ["question-a"]
    assert history[0]["answer_text"] == answer_text


def test_restore_rejects_corrupt_backup_without_changing_target(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "question-a", "must survive", 4, 90)
    backup = create_backup(tmp_path / "backups")
    original_target = database.read_bytes()
    backup.path.write_bytes(b"not a sqlite database")

    with pytest.raises(BackupError, match="invalid backup"):
        restore_backup(
            backup.path,
            target_path=database,
            safety_dir=tmp_path / "pre-restore",
        )

    assert database.read_bytes() == original_target
    assert store.list_quiz_history("user-a")[0]["answer_text"] == "must survive"


def test_backup_history_records_verified_snapshot(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)

    backup = create_backup(tmp_path / "backups")

    import sqlite3

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT file_name, sha256, size_bytes, schema_version, verified_at
            FROM backup_history
            """
        ).fetchone()
    assert row is not None
    assert row[0] == backup.path.name
    assert row[1] == backup.sha256
    assert row[2] == backup.size_bytes
    assert row[3] == "20260923_001"
    assert row[4]


def test_restore_requires_a_manifest(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "question-a", "preserved", 4, 90)
    backup = create_backup(tmp_path / "backups")
    backup.manifest_path.unlink()

    with pytest.raises(BackupError, match="manifest"):
        restore_backup(backup.path, target_path=database)

    assert store.list_quiz_history("user-a")[0]["answer_text"] == "preserved"


def test_restore_rejects_forged_schema_even_with_matching_manifest(
    tmp_path, monkeypatch
):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "question-a", "preserved", 4, 90)
    forged = tmp_path / "forged.db"
    with sqlite3.connect(forged) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            INSERT INTO schema_migrations VALUES (
                '20260829_002', 'backup_history', '2026-08-29T00:00:00Z'
            );
            INSERT INTO schema_migrations (version, name, applied_at)
            VALUES (
                '20260829_003', 'content_provenance', '2026-08-29T00:00:00Z'
            );
            CREATE TABLE unrelated (id TEXT);
            """
        )
    digest = hashlib.sha256(forged.read_bytes()).hexdigest()
    forged.with_suffix(".manifest.json").write_text(
        json.dumps(
            {
                "backup_id": "forged",
                "file_name": forged.name,
                "sha256": digest,
                "size_bytes": forged.stat().st_size,
                "schema_version": "20260830_004",
                "created_at": "2026-08-29T00:00:00Z",
                "verified_at": "2026-08-29T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BackupError, match="invalid backup"):
        restore_backup(forged, target_path=database)

    assert store.list_quiz_history("user-a")[0]["answer_text"] == "preserved"


def test_restore_rejects_non_object_manifest(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    backup = create_backup(tmp_path / "backups")
    backup.manifest_path.write_text("[]", encoding="utf-8")

    with pytest.raises(BackupError, match="manifest"):
        restore_backup(backup.path, target_path=database)


def test_restore_rejects_a_tampered_signed_manifest(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    monkeypatch.setattr(
        settings,
        "backup_signing_key",
        "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8=",
    )
    backup = create_backup(tmp_path / "backups")
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    assert manifest["signature"]
    manifest["verified_at"] = "2099-01-01T00:00:00Z"
    backup.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BackupError, match="signature"):
        restore_backup(backup.path, target_path=database)


def test_restore_never_ignores_an_existing_signature_when_key_is_missing(
    tmp_path, monkeypatch
):
    database = _database(tmp_path, monkeypatch)
    signing_key = "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8="
    monkeypatch.setattr(settings, "backup_signing_key", signing_key)
    backup = create_backup(tmp_path / "backups")
    with sqlite3.connect(backup.path) as connection:
        connection.execute(
            """
            INSERT INTO user_answers (
                id, user_id, question_id, answer_text, created_at
            ) VALUES ('tampered', 'attacker', 'q', 'tampered', '2099-01-01')
            """
        )
    manifest = json.loads(backup.manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = hashlib.sha256(backup.path.read_bytes()).hexdigest()
    manifest["size_bytes"] = backup.path.stat().st_size
    backup.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(settings, "backup_signing_key", "")

    with pytest.raises(BackupError, match="signature"):
        restore_backup(backup.path, target_path=database)


def test_restore_normalizes_invalid_utf8_manifest(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    backup = create_backup(tmp_path / "backups")
    backup.manifest_path.write_bytes(b"\xff\xfe\xfd")

    with pytest.raises(BackupError, match="manifest"):
        restore_backup(backup.path, target_path=database)


def test_final_verification_failure_restores_safety_snapshot(
    tmp_path, monkeypatch
):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "question-before", "backup state", 4, 90)
    backup = create_backup(tmp_path / "backups")
    store.save_quiz_answer("user-a", "question-current", "current state", 5, 95)
    real_verify = backup_module._verify_database
    failed_once = False

    def fail_final_target(path, **kwargs):
        nonlocal failed_once
        if Path(path).resolve() == database.resolve() and not failed_once:
            failed_once = True
            raise BackupError("injected final verification failure")
        return real_verify(path, **kwargs)

    monkeypatch.setattr(backup_module, "_verify_database", fail_final_target)

    with pytest.raises(BackupError, match="restore failed"):
        restore_backup(
            backup.path,
            target_path=database,
            safety_dir=tmp_path / "pre-restore",
        )

    question_ids = {
        item["question_id"] for item in store.list_quiz_history("user-a")
    }
    assert question_ids == {"question-before", "question-current"}


def _rewrite_unsigned_manifest(backup_path: Path, schema_version: str) -> None:
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("signature", None)
    manifest["sha256"] = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    manifest["size_bytes"] = backup_path.stat().st_size
    manifest["schema_version"] = schema_version
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_restore_upgrades_a_valid_previous_schema_backup(tmp_path, monkeypatch):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "legacy-question", "legacy answer", 4, 88)
    backup = create_backup(tmp_path / "backups")
    with sqlite3.connect(backup.path) as connection:
        connection.executescript(
            """
            DROP TABLE content_takedown_log;
            DROP TABLE content_sources;
            DROP TABLE exercise_attempts;
            ALTER TABLE user_settings DROP COLUMN llm_protocol;
            DELETE FROM schema_migrations WHERE version IN ('20260829_003', '20260830_004', '20260923_001');
            """
        )
    _rewrite_unsigned_manifest(backup.path, "20260829_002")

    result = restore_backup(backup.path, target_path=database)

    assert result.schema_version == "20260923_001"
    assert store.list_quiz_history("user-a")[0]["answer_text"] == "legacy answer"
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone() == ("20260923_001",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'content_sources'"
        ).fetchone() == ("content_sources",)


def test_restore_accepts_supported_previous_schema_as_current_target(
    tmp_path, monkeypatch
):
    database = _database(tmp_path, monkeypatch)
    store.save_quiz_answer("user-a", "legacy-question", "legacy answer", 4, 88)
    backup = create_backup(tmp_path / "backups")
    for path in (backup.path, database):
        with sqlite3.connect(path) as connection:
            connection.executescript(
                """
                DROP TABLE content_takedown_log;
                DROP TABLE content_sources;
                DROP TABLE exercise_attempts;
                ALTER TABLE user_settings DROP COLUMN llm_protocol;
                DELETE FROM schema_migrations WHERE version IN ('20260829_003', '20260830_004', '20260923_001');
                """
            )
    _rewrite_unsigned_manifest(backup.path, "20260829_002")

    result = restore_backup(backup.path, target_path=database)

    assert result.schema_version == "20260923_001"
    assert store.list_quiz_history("user-a")[0]["answer_text"] == "legacy answer"


def test_restore_rejects_snapshot_missing_append_only_trigger(
    tmp_path,
    monkeypatch,
):
    database = _database(tmp_path, monkeypatch)
    backup = create_backup(tmp_path / "backups")
    with sqlite3.connect(backup.path) as connection:
        connection.execute("DROP TRIGGER content_takedown_log_no_delete")
    _rewrite_unsigned_manifest(backup.path, "20260923_001")

    with pytest.raises(BackupError, match="invalid backup"):
        restore_backup(backup.path, target_path=database)
