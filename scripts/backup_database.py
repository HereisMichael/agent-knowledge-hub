"""Create a verified SQLite snapshot without stopping the API."""

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
from app.db.backup import BackupError, create_backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(settings.backup_path),
        help="Directory for the database snapshot and metadata manifest.",
    )
    args = parser.parse_args()
    try:
        result = create_backup(args.destination)
    except BackupError as exc:
        parser.exit(1, f"Backup failed: {exc}\n")
    print(
        json.dumps(
            {
                "backup": str(result.path),
                "manifest": str(result.manifest_path),
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "schema_version": result.schema_version,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
