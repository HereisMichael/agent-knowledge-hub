from __future__ import annotations

import base64
import socket
import sqlite3

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.auth import service as auth_service
from app.config import settings
from app.db import store
from app.security.credential_vault import (
    CredentialDecryptionError,
    EncryptedSecret,
    CredentialVault,
    CredentialVaultUnavailable,
)
from app.settings import service as settings_service


MASTER_KEY = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")


def _configure(tmp_path, monkeypatch, *, encryption_key: str = MASTER_KEY):
    database = tmp_path / "credentials.db"
    monkeypatch.setattr(settings, "sqlite_path", str(database))
    monkeypatch.setattr(settings, "credential_encryption_key", encryption_key)
    store.init_db()
    return database


def test_vault_randomizes_ciphertext_and_binds_it_to_the_owner():
    vault = CredentialVault.from_base64(MASTER_KEY)

    audience = "https://api.example.com"
    first = vault.encrypt("sk-private-example", "user-a", audience)
    second = vault.encrypt("sk-private-example", "user-a", audience)

    assert first.ciphertext != second.ciphertext
    assert first.nonce != second.nonce
    assert vault.decrypt(first, "user-a", audience) == "sk-private-example"
    with pytest.raises(CredentialDecryptionError):
        vault.decrypt(first, "user-b", audience)
    with pytest.raises(CredentialDecryptionError):
        vault.decrypt(first, "user-a", "https://attacker.example")


def test_user_key_is_never_persisted_or_returned_as_plaintext(tmp_path, monkeypatch):
    database = _configure(tmp_path, monkeypatch)
    secret = "sk-secret-must-never-appear-in-sqlite"
    from app.security import outbound_url

    monkeypatch.setattr(
        outbound_url.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ],
    )

    public = settings_service.update_settings(
        "user-a",
        {
            "llm_api_key": secret,
            "llm_model": "private-model",
            "llm_base_url": "HTTPS://API.Example.COM:443/v1",
        },
    )

    assert secret.encode("utf-8") not in database.read_bytes()
    assert secret not in repr(public)
    assert public["has_custom_key"] is True
    assert public["llm_api_key_masked"] == "sk-…lite"
    assert public["llm_base_url"] == "https://api.example.com/v1"
    assert public["llm_protocol"] == "openai_chat"
    assert settings_service.resolve_llm("user-a").api_key == secret


def test_runtime_resolves_anthropic_protocol(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    store.upsert_user_settings(
        "user-a",
        {
            "llm_protocol": "anthropic_messages",
            "llm_base_url": "https://api.anthropic.com",
            "llm_model": "claude-3-5-haiku-latest",
            "force_demo": 1,
        },
    )

    assert settings_service.resolve_llm("user-a").protocol == "anthropic_messages"


def test_unsafe_model_url_is_not_persisted(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.security.outbound_url import UnsafeOutboundUrl

    with pytest.raises(UnsafeOutboundUrl):
        settings_service.update_settings(
            "user-a",
            {"llm_base_url": "http://127.0.0.1:8000/v1"},
        )

    assert store.get_user_settings("user-a") == {"user_id": "user-a"}


def test_legacy_plaintext_key_is_migrated_and_cleared_atomically(tmp_path, monkeypatch):
    database = _configure(tmp_path, monkeypatch)
    legacy_secret = "sk-legacy-plaintext-key"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO user_settings
               (user_id, llm_api_key, force_demo, updated_at)
               VALUES (?, ?, 0, ?)""",
            ("legacy-user", legacy_secret, "2026-08-29T00:00:00+00:00"),
        )

    migrated = settings_service.migrate_legacy_llm_keys()

    row = store.get_user_settings("legacy-user")
    assert migrated == 1
    assert row["llm_api_key"] is None
    assert row["llm_api_key_ciphertext"]
    assert legacy_secret.encode("utf-8") not in database.read_bytes()
    assert settings_service.resolve_llm("legacy-user").api_key == legacy_secret


def test_saving_a_key_fails_closed_when_vault_is_unavailable(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch, encryption_key="")

    with pytest.raises(CredentialVaultUnavailable):
        settings_service.update_settings("user-a", {"llm_api_key": "sk-private"})


def test_store_rejects_plaintext_credentials_at_its_boundary(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="plaintext credentials"):
        store.upsert_user_settings("user-a", {"llm_api_key": "sk-bypass-attempt"})


def test_first_admin_can_decrypt_a_migrated_legacy_default_key(tmp_path, monkeypatch):
    database = _configure(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT INTO user_settings
               (user_id, llm_api_key, force_demo, updated_at)
               VALUES ('default', ?, 0, ?)""",
            ("sk-legacy-admin-key", "2026-08-29T00:00:00+00:00"),
        )
    assert settings_service.migrate_legacy_llm_keys() == 1

    grant = auth_service.register(
        "owner@example.com",
        "correct horse battery staple",
        "invite-2026-safe",
    )

    assert grant.identity.role == "admin"
    assert settings_service.resolve_llm(grant.identity.user_id).api_key == (
        "sk-legacy-admin-key"
    )


def test_failed_legacy_rewrap_rolls_back_first_admin_creation(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "auth_invite_code", "invite-2026-safe")
    other_key = base64.urlsafe_b64encode(bytes(reversed(range(32)))).decode("ascii")
    unreadable = CredentialVault.from_base64(other_key).encrypt(
        "sk-unreadable",
        "default",
        "https://api.example.com",
    )
    store.upsert_user_settings(
        "default",
        {},
        encrypted_api_key=unreadable,
    )

    with pytest.raises(CredentialDecryptionError):
        auth_service.register(
            "owner@example.com",
            "correct horse battery staple",
            "invite-2026-safe",
        )

    assert store.get_user_by_email("owner@example.com") is None


def test_non_key_settings_update_uses_one_atomic_store_connection(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    settings_service.update_settings("user-a", {"llm_api_key": "sk-current-key"})
    real_connect = store._conn
    connection_count = 0

    def tracked_connect():
        nonlocal connection_count
        connection_count += 1
        return real_connect()

    monkeypatch.setattr(store, "_conn", tracked_connect)
    store.upsert_user_settings("user-a", {"llm_model": "new-model"})

    assert connection_count == 1
    assert settings_service.resolve_llm("user-a").api_key == "sk-current-key"


def test_stale_settings_write_cannot_split_endpoint_from_newer_key(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    from app.db.store import SettingsWriteConflict

    settings_service.update_settings("user-a", {"llm_api_key": "sk-first-key"})
    stale_revision = store.get_user_settings("user-a")["updated_at"]
    settings_service.update_settings("user-a", {"llm_api_key": "sk-newer-key"})

    with pytest.raises(SettingsWriteConflict):
        store.upsert_user_settings(
            "user-a",
            {"llm_model": "stale-write"},
            expected_updated_at=stale_revision,
        )

    assert settings_service.resolve_llm("user-a").api_key == "sk-newer-key"


def test_legacy_migration_rolls_back_all_rows_if_encryption_fails(
    tmp_path,
    monkeypatch,
):
    database = _configure(tmp_path, monkeypatch)
    with sqlite3.connect(database) as connection:
        connection.executemany(
            """INSERT INTO user_settings
               (user_id, llm_api_key, force_demo, updated_at)
               VALUES (?, ?, 0, ?)""",
            [
                ("legacy-a", "sk-legacy-a", "2026-08-29T00:00:00+00:00"),
                ("legacy-b", "sk-legacy-b", "2026-08-29T00:00:00+00:00"),
            ],
        )
    real_encrypt = CredentialVault.encrypt
    attempts = 0

    def fail_second(self, plaintext, user_id, audience):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            raise RuntimeError("simulated encryption failure")
        return real_encrypt(self, plaintext, user_id, audience)

    monkeypatch.setattr(CredentialVault, "encrypt", fail_second)
    with pytest.raises(RuntimeError, match="simulated encryption failure"):
        settings_service.migrate_legacy_llm_keys()

    assert {row["user_id"] for row in store.list_legacy_llm_keys()} == {
        "legacy-a",
        "legacy-b",
    }


@pytest.mark.parametrize(
    "ciphertext,nonce",
    [
        ("not-base64!", "also-invalid!"),
        ("YWJj", "c2hvcnQ="),
        (None, None),
    ],
)
def test_malformed_envelopes_raise_only_the_domain_error(ciphertext, nonce):
    vault = CredentialVault.from_base64(MASTER_KEY)
    malformed = type(
        "MalformedEnvelope",
        (),
        {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "key_version": "v1",
            "hint": "",
        },
    )()

    with pytest.raises(CredentialDecryptionError):
        vault.decrypt(malformed, "user-a", "https://api.example.com")


def test_custom_endpoint_requires_a_key_in_the_same_profile(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.security import outbound_url
    from app.settings.service import CredentialEndpointMismatch

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
    ])

    with pytest.raises(CredentialEndpointMismatch):
        settings_service.update_settings(
            "user-a",
            {"llm_base_url": "https://custom.example/v1"},
        )


def test_changing_endpoint_origin_requires_a_new_key(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.security import outbound_url
    from app.settings.service import CredentialEndpointMismatch

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
    ])
    settings_service.update_settings(
        "user-a",
        {
            "llm_base_url": "https://first.example/v1",
            "llm_api_key": "sk-first-host-key",
        },
    )

    with pytest.raises(CredentialEndpointMismatch):
        settings_service.update_settings(
            "user-a",
            {"llm_base_url": "https://second.example/v1"},
        )

    runtime = settings_service.resolve_llm("user-a")
    assert runtime.base_url == "https://first.example/v1"
    assert runtime.api_key == "sk-first-host-key"


def test_server_fallback_key_cannot_be_paired_with_a_custom_origin(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    from app.settings.service import CredentialEndpointMismatch

    monkeypatch.setattr(settings, "llm_api_key", "sk-operator-secret")
    store.upsert_user_settings(
        "user-a",
        {"llm_base_url": "https://attacker.example/v1"},
    )

    with pytest.raises(CredentialEndpointMismatch):
        settings_service.resolve_llm("user-a")


def test_unbound_v1_ciphertext_is_rewrapped_for_its_existing_origin(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)
    raw_key = base64.urlsafe_b64decode(MASTER_KEY)
    nonce = bytes(range(12))
    plaintext = "sk-existing-v1-key"
    aad = b"agent-knowledge-hub:credential:user-a:v1"
    legacy = EncryptedSecret(
        ciphertext=base64.urlsafe_b64encode(
            AESGCM(raw_key).encrypt(nonce, plaintext.encode(), aad)
        ).decode("ascii"),
        nonce=base64.urlsafe_b64encode(nonce).decode("ascii"),
        key_version="v1",
        hint="sk-…-key",
    )
    store.upsert_user_settings(
        "user-a",
        {"llm_base_url": "https://existing.example/v1"},
        encrypted_api_key=legacy,
    )

    assert settings_service.migrate_unbound_llm_keys() == 1

    row = store.get_user_settings("user-a")
    assert row["llm_api_key_version"] == "v2"
    assert row["llm_api_key_audience"] == "https://existing.example"
    assert settings_service.resolve_llm("user-a").api_key == plaintext


def test_protocol_change_requires_a_new_key_and_is_atomic(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.settings.service import CredentialEndpointMismatch

    settings_service.update_settings(
        "user-a",
        {
            "llm_protocol": "openai_chat",
            "llm_api_key": "sk-old-protocol-key",
        },
    )

    with pytest.raises(CredentialEndpointMismatch):
        settings_service.update_settings(
            "user-a",
            {"llm_protocol": "anthropic_messages"},
        )

    runtime = settings_service.resolve_llm("user-a")
    assert runtime.protocol == "openai_chat"
    assert runtime.api_key == "sk-old-protocol-key"


def test_protocol_change_with_replacement_key_updates_atomically(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    settings_service.update_settings(
        "user-a",
        {"llm_api_key": "sk-old-protocol-key"},
    )

    public = settings_service.update_settings(
        "user-a",
        {
            "llm_protocol": "anthropic_messages",
            "llm_api_key": "sk-new-protocol-key",
        },
    )

    runtime = settings_service.resolve_llm("user-a")
    assert runtime.protocol == "anthropic_messages"
    assert runtime.api_key == "sk-new-protocol-key"
    assert public["llm_protocol"] == "anthropic_messages"
    assert "sk-new-protocol-key" not in repr(public)


def test_server_fallback_requires_matching_origin_and_protocol(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.settings.service import CredentialEndpointMismatch

    monkeypatch.setattr(settings, "llm_api_key", "sk-server-fallback")
    with pytest.raises(CredentialEndpointMismatch):
        settings_service.update_settings(
            "user-a",
            {"llm_protocol": "anthropic_messages", "force_demo": 0},
        )

    assert store.get_user_settings("user-a") == {"user_id": "user-a"}
    public = settings_service.update_settings(
        "user-a",
        {"llm_protocol": "openai_chat", "force_demo": 0},
    )
    assert public["using_server_env_fallback"] is True
    assert settings_service.resolve_llm("user-a").api_key == "sk-server-fallback"


def test_force_demo_can_stage_custom_protocol_without_a_key(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    from app.security import outbound_url

    monkeypatch.setattr(outbound_url.socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
    ])
    public = settings_service.update_settings(
        "user-a",
        {
            "llm_base_url": "https://staging.example/v1",
            "llm_protocol": "anthropic_messages",
            "force_demo": 1,
        },
    )

    assert public["has_custom_key"] is False
    assert public["llm_protocol"] == "anthropic_messages"
    assert settings_service.resolve_llm("user-a").demo is True


@pytest.mark.parametrize("server_protocol", ["openai_chat", "anthropic_messages"])
def test_first_partial_update_persists_effective_server_protocol(
    tmp_path,
    monkeypatch,
    server_protocol,
):
    _configure(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "llm_protocol", server_protocol)

    public = settings_service.update_settings(
        "user-a",
        {"llm_model": "partial-update-model"},
    )

    stored = store.get_user_settings("user-a")
    assert stored["llm_protocol"] == server_protocol
    assert public["llm_protocol"] == server_protocol


@pytest.mark.parametrize("invalid_master_key", ["", "not-valid-base64"])
def test_public_settings_never_resolve_or_decrypt_custom_credentials(
    tmp_path,
    monkeypatch,
    invalid_master_key,
):
    _configure(tmp_path, monkeypatch)
    store.upsert_user_settings(
        "user-a",
        {
            "llm_protocol": "anthropic_messages",
            "llm_base_url": "https://api.anthropic.com",
            "llm_model": "claude-test",
            "force_demo": 0,
        },
        encrypted_api_key=EncryptedSecret(
            ciphertext="opaque-ciphertext",
            nonce="opaque-nonce",
            key_version="v2",
            hint="sk-…test",
            audience="https://api.anthropic.com",
        ),
    )
    monkeypatch.setattr(settings, "credential_encryption_key", invalid_master_key)

    def forbidden(*args, **kwargs):
        raise AssertionError("public settings must not access plaintext credentials")

    monkeypatch.setattr(settings_service, "resolve_llm", forbidden)
    monkeypatch.setattr(CredentialVault, "decrypt", forbidden)

    public = settings_service.get_settings_public("user-a")

    assert public == {
        "llm_base_url": "https://api.anthropic.com",
        "llm_protocol": "anthropic_messages",
        "llm_model": "claude-test",
        "llm_api_key_masked": "sk-…test",
        "has_custom_key": True,
        "force_demo": False,
        "demo_mode_active": False,
        "using_server_env_fallback": False,
    }


@pytest.mark.parametrize(
    "placeholder_key",
    ["not-set", "sk-xxx", "your_api_key_here"],
)
def test_encrypted_custom_placeholder_key_is_not_demo(
    tmp_path,
    monkeypatch,
    placeholder_key,
):
    _configure(tmp_path, monkeypatch)

    public = settings_service.update_settings(
        "user-a",
        {"llm_api_key": placeholder_key, "force_demo": 0},
    )
    runtime = settings_service.resolve_llm("user-a")

    assert public["has_custom_key"] is True
    assert public["demo_mode_active"] is False
    assert runtime.demo is False
    assert runtime.api_key == placeholder_key


def test_force_demo_overrides_an_encrypted_custom_placeholder_key(
    tmp_path,
    monkeypatch,
):
    _configure(tmp_path, monkeypatch)

    public = settings_service.update_settings(
        "user-a",
        {"llm_api_key": "not-set", "force_demo": 1},
    )
    runtime = settings_service.resolve_llm("user-a")

    assert public["has_custom_key"] is True
    assert public["demo_mode_active"] is True
    assert runtime.demo is True


@pytest.mark.parametrize(
    "placeholder_key",
    ["not-set", "sk-xxx", "your_api_key_here"],
)
def test_server_fallback_placeholder_key_remains_demo(
    tmp_path,
    monkeypatch,
    placeholder_key,
):
    _configure(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "llm_api_key", placeholder_key)

    public = settings_service.get_settings_public("user-a")
    runtime = settings_service.resolve_llm("user-a")

    assert public["has_custom_key"] is False
    assert public["using_server_env_fallback"] is True
    assert public["demo_mode_active"] is True
    assert runtime.demo is True
