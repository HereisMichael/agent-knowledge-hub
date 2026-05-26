#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.content.daily_update import run_daily_update  # noqa: E402
from app.db.store import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print(run_daily_update())
