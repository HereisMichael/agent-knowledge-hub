"""Run the content scheduler as a single dedicated process."""

from __future__ import annotations

import signal
from threading import Event

from app.db import store
from app.scheduler.jobs import start_scheduler, stop_scheduler


def run(*, stop_event: Event | None = None) -> None:
    stopped = stop_event or Event()
    store.init_db()
    start_scheduler()
    try:
        stopped.wait()
    finally:
        stop_scheduler()


def main() -> int:
    stopped = Event()

    def request_stop(*_args) -> None:
        stopped.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    run(stop_event=stopped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
