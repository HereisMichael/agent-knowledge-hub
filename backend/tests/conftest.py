from __future__ import annotations

import pytest

from app.config import settings
from app.privacy.tombstones import ensure_ledger


@pytest.fixture(autouse=True)
def isolate_privacy_ledger_for_every_test(tmp_path, monkeypatch):
    """Never let tests share durable deletion history across cases."""

    monkeypatch.setattr(
        settings,
        "privacy_ledger_path",
        str(tmp_path / "test-privacy-ledger.db"),
    )
    monkeypatch.setattr(settings, "privacy_ledger_id", "test-ledger-instance")
    ensure_ledger()
