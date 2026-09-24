"""Restore a verified SQLite snapshot after creating a safety copy."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.chdir(PROJECT_ROOT / "backend")

from app.config import settings
from app.db.backup import BackupError, restore_backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path, help="Snapshot database to restore.")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(settings.sqlite_path),
        help="Database to replace.",
    )
    parser.add_argument(
        "--safety-dir",
        type=Path,
        default=Path(settings.backup_path) / "pre-restore",
        help="Directory that receives the current database before restore.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm the destructive replacement of the target database.",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("restore requires --yes after the API has been stopped")
    try:
        result = restore_backup(
            args.backup,
            target_path=args.target,
            safety_dir=args.safety_dir,
        )
    except BackupError as exc:
        parser.exit(1, f"Restore failed: {exc}\n")
    print(
        json.dumps(
            {
                "restored": str(result.target_path),
                "safety_backup": (
                    str(result.safety_backup_path)
                    if result.safety_backup_path is not None
                    else None
                ),
                "schema_version": result.schema_version,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
