"""Invite registration and opaque server-side sessions."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt

from app.config import settings
from app.db import store
from app.privacy.tombstones import is_deleted


@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str
    role: str


@dataclass(frozen=True)
class SessionGrant:
    identity: Identity
    token: str
    expires_at: str


class AuthError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"agent-knowledge-hub-invalid-password",
    bcrypt.gensalt(rounds=12),
)


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    local, separator, domain = normalized.partition("@")
    if (
        not separator
        or not local
        or not domain
        or "." not in domain
        or len(normalized) > 254
    ):
        raise AuthError("invalid_email")
    return normalized


def _validate_password(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(password) < 12 or len(encoded) > 72:
        raise AuthError("weak_password")
    return encoded


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _identity(row: dict) -> Identity:
    return Identity(
        user_id=row["user_id"] if "user_id" in row else row["id"],
        email=row["email"],
        role=row["role"],
    )


def _issue_session(user: dict) -> SessionGrant:
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    ).isoformat()
    store.create_auth_session(user["id"], _hash_token(token), expires_at)
    return SessionGrant(identity=_identity(user), token=token, expires_at=expires_at)


def register(email: str, password: str, invite_code: str) -> SessionGrant:
    expected_invite = settings.auth_invite_code.strip()
    supplied_invite = invite_code.strip()
    if expected_invite and not hmac.compare_digest(supplied_invite, expected_invite):
        raise AuthError("invalid_invite")

    normalized_email = _normalize_email(email)
    encoded_password = _validate_password(password)
    password_hash = bcrypt.hashpw(encoded_password, bcrypt.gensalt(rounds=12)).decode(
        "ascii"
    )
    from app.settings.service import rewrap_credential

    try:
        user = store.create_user(
            normalized_email,
            password_hash,
            rewrap_credential=rewrap_credential,
        )
    except ValueError as exc:
        if str(exc) == "email_exists":
            raise AuthError("email_exists") from exc
        raise
    return _issue_session(user)


def login(email: str, password: str) -> SessionGrant:
    normalized_email = _normalize_email(email)
    encoded_password = _validate_password(password)
    user = store.get_user_by_email(normalized_email)
    candidate_hash = (
        user["password_hash"].encode("ascii") if user else _DUMMY_PASSWORD_HASH
    )
    if (
        not bcrypt.checkpw(encoded_password, candidate_hash)
        or not user
        or is_deleted(user["id"])
    ):
        raise AuthError("invalid_credentials")
    return _issue_session(user)


def authenticate(token: str) -> Identity:
    if not token:
        raise AuthError("invalid_session")
    row = store.get_identity_by_token_hash(
        _hash_token(token),
        datetime.now(timezone.utc).isoformat(),
    )
    if not row:
        raise AuthError("invalid_session")
    if is_deleted(row["user_id"]):
        raise AuthError("invalid_session")
    return _identity(row)


def logout(token: str) -> None:
    if token:
        store.revoke_auth_session(_hash_token(token))


def confirm_password(user_id: str, password: str) -> None:
    try:
        encoded_password = _validate_password(password)
    except AuthError as exc:
        raise AuthError("invalid_credentials") from exc
    user = store.get_user_by_id(user_id)
    candidate_hash = (
        user["password_hash"].encode("ascii") if user else _DUMMY_PASSWORD_HASH
    )
    if not user or not bcrypt.checkpw(encoded_password, candidate_hash):
        raise AuthError("invalid_credentials")
