"""Container-friendly database backup and restore commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import settings
from app.db.backup import BackupError, create_backup, restore_backup


def _backup(args: argparse.Namespace) -> dict:
    result = create_backup(args.destination)
    return {
        "backup": str(result.path),
        "manifest": str(result.manifest_path),
        "sha256": result.sha256,
        "size_bytes": result.size_bytes,
        "schema_version": result.schema_version,
    }


def _restore(args: argparse.Namespace) -> dict:
    if not args.yes:
        raise BackupError("restore requires --yes after the API has been stopped")
    result = restore_backup(
        args.backup,
        target_path=args.target,
        safety_dir=args.safety_dir,
    )
    return {
        "restored": str(result.target_path),
        "safety_backup": (
            str(result.safety_backup_path)
            if result.safety_backup_path is not None
            else None
        ),
        "schema_version": result.schema_version,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    backup_parser = commands.add_parser("backup", help="Create a verified snapshot.")
    backup_parser.add_argument(
        "--destination",
        type=Path,
        default=Path(settings.backup_path),
    )
    backup_parser.set_defaults(handler=_backup)

    restore_parser = commands.add_parser("restore", help="Restore a verified snapshot.")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument(
        "--target",
        type=Path,
        default=Path(settings.sqlite_path),
    )
    restore_parser.add_argument(
        "--safety-dir",
        type=Path,
        default=Path(settings.backup_path) / "pre-restore",
    )
    restore_parser.add_argument("--yes", action="store_true")
    restore_parser.set_defaults(handler=_restore)
    args = parser.parse_args()
    try:
        payload = args.handler(args)
    except BackupError as exc:
        parser.exit(1, f"{args.command.capitalize()} failed: {exc}\n")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
