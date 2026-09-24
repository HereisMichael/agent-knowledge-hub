"""Consistent SQLite backup, verification, and guarded restore operations."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db.migrations import (
    current_schema_version,
    expected_schema_version,
    run_migrations,
    validate_current_schema,
    validate_supported_schema,
)
from app.privacy.tombstones import PrivacyLedgerError, apply_deletions


class BackupError(RuntimeError):
    """Raised when a database snapshot cannot be trusted."""


@dataclass(frozen=True)
class BackupResult:
    path: Path
    manifest_path: Path
    sha256: str
    size_bytes: int
    schema_version: str


@dataclass(frozen=True)
class RestoreResult:
    target_path: Path
    safety_backup_path: Path | None
    schema_version: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_signature(payload: dict) -> str | None:
    encoded_key = settings.backup_signing_key.strip()
    if not encoded_key:
        return None
    try:
        key = base64.b64decode(encoded_key, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BackupError("backup signing key is invalid") from exc
    if len(key) != 32:
        raise BackupError("backup signing key is invalid")
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def _read_only_connection(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _verify_database(path: Path, *, allow_legacy: bool = False) -> str:
    try:
        with closing(_read_only_connection(path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                raise BackupError("invalid backup: SQLite integrity check failed")
            if allow_legacy:
                version = validate_supported_schema(connection)
            else:
                validate_current_schema(connection)
                version = current_schema_version(connection)
            return version
    except BackupError:
        raise
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        raise BackupError("invalid backup: unreadable SQLite snapshot") from exc


def _atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _snapshot(
    source_path: Path,
    destination_dir: Path,
    *,
    record_history: bool,
    allow_legacy: bool = False,
) -> BackupResult:
    source = source_path.resolve()
    if not source.is_file():
        raise BackupError("database source does not exist")
    destination = destination_dir.resolve()
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError("database backup destination is unavailable") from exc
    backup_id = uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = destination / f"hub-{timestamp}-{backup_id[:8]}.db"
    temporary = destination / f".{backup_path.name}.tmp"
    created_at = _now()
    try:
        with closing(sqlite3.connect(str(source))) as source_connection:
            with closing(sqlite3.connect(str(temporary))) as backup_connection:
                source_connection.backup(backup_connection)
        schema_version = _verify_database(temporary, allow_legacy=allow_legacy)
        os.replace(temporary, backup_path)
    except BackupError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise BackupError("database backup failed") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

    manifest_path = backup_path.with_suffix(".manifest.json")
    try:
        checksum = _sha256(backup_path)
        size_bytes = backup_path.stat().st_size
        verified_at = _now()
        manifest = {
            "backup_id": backup_id,
            "file_name": backup_path.name,
            "sha256": checksum,
            "size_bytes": size_bytes,
            "schema_version": schema_version,
            "created_at": created_at,
            "verified_at": verified_at,
        }
        signature = _manifest_signature(manifest)
        if signature is not None:
            manifest["signature"] = signature
        _atomic_json(manifest_path, manifest)
    except (BackupError, OSError, TypeError, ValueError) as exc:
        backup_path.unlink(missing_ok=True)
        manifest_path.unlink(missing_ok=True)
        if isinstance(exc, BackupError):
            raise
        raise BackupError("database backup metadata could not be written") from exc
    if record_history:
        try:
            with closing(sqlite3.connect(str(source))) as connection:
                connection.execute(
                    """
                    INSERT INTO backup_history (
                        id, file_name, sha256, size_bytes, schema_version,
                        created_at, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        backup_id,
                        backup_path.name,
                        checksum,
                        size_bytes,
                        schema_version,
                        created_at,
                        verified_at,
                    ),
                )
                connection.commit()
        except (OSError, sqlite3.Error) as exc:
            backup_path.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
            raise BackupError("database backup history could not be recorded") from exc
    return BackupResult(
        path=backup_path,
        manifest_path=manifest_path,
        sha256=checksum,
        size_bytes=size_bytes,
        schema_version=schema_version,
    )


def create_backup(
    destination_dir: Path,
    *,
    source_path: Path | None = None,
) -> BackupResult:
    """Create and verify an online snapshot using SQLite's backup API."""

    source = source_path or Path(settings.sqlite_path)
    return _snapshot(Path(source), Path(destination_dir), record_history=True)


def _verify_manifest(backup_path: Path) -> dict:
    manifest_path = backup_path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise BackupError("invalid backup: manifest is required")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise TypeError("manifest must be an object")
        checksum = _sha256(backup_path)
        size_bytes = backup_path.stat().st_size
    except (OSError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupError("invalid backup: manifest is unreadable") from exc
    if (
        manifest.get("file_name") != backup_path.name
        or manifest.get("sha256") != checksum
        or manifest.get("size_bytes") != size_bytes
    ):
        raise BackupError("invalid backup: manifest verification failed")
    signature = manifest.get("signature")
    unsigned = {key: value for key, value in manifest.items() if key != "signature"}
    expected_signature = _manifest_signature(unsigned)
    signature_required = (
        settings.app_env == "production"
        or signature is not None
        or expected_signature is not None
    )
    if signature_required and (
        not isinstance(signature, str)
        or expected_signature is None
        or not hmac.compare_digest(signature, expected_signature)
    ):
        raise BackupError("invalid backup: manifest signature verification failed")
    return manifest


def _copy_database(source: Path, target: Path) -> None:
    with closing(_read_only_connection(source)) as source_connection:
        with closing(sqlite3.connect(str(target))) as target_connection:
            source_connection.backup(target_connection)


def _remove_database_files(path: Path) -> None:
    for candidate in (
        path,
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
    ):
        candidate.unlink(missing_ok=True)


def restore_backup(
    backup_path: Path,
    *,
    target_path: Path | None = None,
    safety_dir: Path | None = None,
) -> RestoreResult:
    """Validate a snapshot, preserve the current DB, then restore transactionally."""

    backup = Path(backup_path).resolve()
    if not backup.is_file():
        raise BackupError("invalid backup: file does not exist")
    manifest = _verify_manifest(backup)
    schema_version = _verify_database(backup, allow_legacy=True)
    if manifest.get("schema_version") != schema_version:
        raise BackupError("invalid backup: manifest schema version does not match")

    target = Path(target_path or settings.sqlite_path).resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BackupError("database restore target is unavailable") from exc
    target_existed = target.exists()
    safety_backup_path: Path | None = None
    safety: BackupResult | None = None
    if target.exists():
        safety_destination = Path(safety_dir or (target.parent / "pre-restore"))
        safety = _snapshot(
            target,
            safety_destination,
            record_history=False,
            allow_legacy=True,
        )
        safety_backup_path = safety.path

    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.restore")
    target_modified = False
    try:
        _copy_database(backup, temporary)
        restored_version = _verify_database(temporary, allow_legacy=True)
        if restored_version != schema_version:
            raise BackupError("invalid backup: schema changed during restore")
        if restored_version != expected_schema_version():
            with closing(sqlite3.connect(str(temporary))) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                run_migrations(connection)
                validate_current_schema(connection)
        apply_deletions(temporary)
        restored_version = _verify_database(temporary)
        target_modified = True
        _copy_database(temporary, target)
        if _verify_database(target) != restored_version:
            raise BackupError("database restore verification failed")
    except (BackupError, OSError, PrivacyLedgerError, sqlite3.Error) as exc:
        if target_modified:
            try:
                if safety is not None:
                    _copy_database(safety.path, target)
                    _verify_database(target, allow_legacy=True)
                elif not target_existed:
                    _remove_database_files(target)
            except (BackupError, OSError, sqlite3.Error) as rollback_exc:
                raise BackupError(
                    "database restore failed and safety rollback failed"
                ) from rollback_exc
        raise BackupError("database restore failed; original target was recovered") from exc
    finally:
        try:
            _remove_database_files(temporary)
        except OSError:
            pass
    return RestoreResult(
        target_path=target,
        safety_backup_path=safety_backup_path,
        schema_version=restored_version,
    )
