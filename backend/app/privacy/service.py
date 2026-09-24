"""Export and delete authenticated user data behind a small interface."""

from __future__ import annotations

from datetime import datetime, timezone

from app.auth import service as auth_service
from app.auth.service import Identity
from app.db import store
from app.db.migrations import expected_schema_version
from app.privacy.tombstones import record_deletion


class PrivacyError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def export_account(identity: Identity) -> dict:
    try:
        data = store.export_user_data(identity.user_id)
    except ValueError as exc:
        raise PrivacyError(str(exc)) from exc
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": expected_schema_version(),
        **data,
    }


def delete_account(identity: Identity, password: str) -> None:
    try:
        auth_service.confirm_password(identity.user_id, password)
    except auth_service.AuthError as exc:
        raise PrivacyError("invalid_password") from exc
    try:
        store.delete_user_account(
            identity.user_id,
            before_delete=record_deletion,
        )
    except ValueError as exc:
        raise PrivacyError(str(exc)) from exc
