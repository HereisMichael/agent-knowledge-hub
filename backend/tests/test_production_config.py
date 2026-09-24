from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


VALID_ENCRYPTION_KEY = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
VALID_BACKUP_SIGNING_KEY = "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8="


@pytest.mark.parametrize(
    "invite_code",
    ["", "short-code", "change-me-invite-code"],
)
def test_production_rejects_missing_or_placeholder_invite_code(invite_code):
    with pytest.raises(ValidationError, match="AUTH_INVITE_CODE"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_invite_code=invite_code,
            credential_encryption_key=VALID_ENCRYPTION_KEY,
        )


def test_production_accepts_a_strong_invite_code():
    configured = Settings(
        _env_file=None,
        app_env="production",
        auth_invite_code="invite-2026-7e6d9a1c4b8f",
        credential_encryption_key=VALID_ENCRYPTION_KEY,
        backup_signing_key=VALID_BACKUP_SIGNING_KEY,
        privacy_ledger_id="deployment-ledger-2026",
    )

    assert configured.app_env == "production"


def test_production_requires_a_unique_privacy_ledger_id():
    with pytest.raises(ValidationError, match="PRIVACY_LEDGER_ID"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_invite_code="invite-2026-7e6d9a1c4b8f",
            credential_encryption_key=VALID_ENCRYPTION_KEY,
            backup_signing_key=VALID_BACKUP_SIGNING_KEY,
        )


@pytest.mark.parametrize("protocol", ["openai_chat", "anthropic_messages"])
def test_production_accepts_supported_llm_protocol(protocol):
    configured = Settings(
        _env_file=None,
        app_env="production",
        auth_invite_code="invite-2026-7e6d9a1c4b8f",
        credential_encryption_key=VALID_ENCRYPTION_KEY,
        backup_signing_key=VALID_BACKUP_SIGNING_KEY,
        privacy_ledger_id="deployment-ledger-2026",
        llm_protocol=protocol,
    )

    assert configured.llm_protocol == protocol


def test_production_rejects_unsupported_llm_protocol():
    with pytest.raises(ValidationError, match="unsupported_llm_protocol"):
        Settings(
            _env_file=None,
            llm_protocol="unsupported",
        )


def test_session_lifetime_must_be_bounded():
    with pytest.raises(ValidationError, match="SESSION_TTL_HOURS"):
        Settings(_env_file=None, session_ttl_hours=0)


def test_privacy_ledger_cannot_share_the_primary_database_path(tmp_path):
    same_path = str(tmp_path / "hub.db")

    with pytest.raises(ValidationError, match="PRIVACY_LEDGER_PATH"):
        Settings(
            _env_file=None,
            sqlite_path=same_path,
            privacy_ledger_path=same_path,
        )


@pytest.mark.parametrize("encryption_key", ["", "not-base64", "c2hvcnQ="])
def test_production_requires_a_32_byte_encryption_key(encryption_key):
    with pytest.raises(ValidationError, match="CREDENTIAL_ENCRYPTION_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_invite_code="invite-2026-7e6d9a1c4b8f",
            credential_encryption_key=encryption_key,
            backup_signing_key=VALID_BACKUP_SIGNING_KEY,
        )


def test_cors_origins_are_trimmed_and_configurable():
    configured = Settings(
        _env_file=None,
        cors_allowed_origins="https://app.example.com, https://admin.example.com ",
    )

    assert configured.cors_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


@pytest.mark.parametrize(
    "origins",
    ["*", "http://app.example.com", "https://app.example.com,http://localhost:5174"],
)
def test_production_rejects_unsafe_cors_origins(origins):
    with pytest.raises(ValidationError, match="CORS_ALLOWED_ORIGINS"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_invite_code="invite-2026-7e6d9a1c4b8f",
            credential_encryption_key=VALID_ENCRYPTION_KEY,
            backup_signing_key=VALID_BACKUP_SIGNING_KEY,
            cors_allowed_origins=origins,
        )


@pytest.mark.parametrize("signing_key", ["", "not-base64", "c2hvcnQ="])
def test_production_requires_a_32_byte_backup_signing_key(signing_key):
    with pytest.raises(ValidationError, match="BACKUP_SIGNING_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            auth_invite_code="invite-2026-7e6d9a1c4b8f",
            credential_encryption_key=VALID_ENCRYPTION_KEY,
            backup_signing_key=signing_key,
        )
