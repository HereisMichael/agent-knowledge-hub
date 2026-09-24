from __future__ import annotations

from threading import Event

from app.scheduler import worker


def test_worker_initializes_database_and_stops_scheduler(monkeypatch):
    calls: list[str] = []
    stopped = Event()
    stopped.set()
    monkeypatch.setattr(worker.store, "init_db", lambda: calls.append("init"))
    monkeypatch.setattr(worker, "start_scheduler", lambda: calls.append("start"))
    monkeypatch.setattr(worker, "stop_scheduler", lambda: calls.append("stop"))

    worker.run(stop_event=stopped)

    assert calls == ["init", "start", "stop"]
