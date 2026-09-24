"""Per-user LLM settings overlay."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import normalize_llm_protocol, settings
from app.db import store
from app.security.credential_vault import CredentialVault, EncryptedSecret
from app.security.outbound_url import outbound_origin, validate_outbound_url


@dataclass
class LlmRuntime:
    base_url: str
    api_key: str
    model: str
    demo: bool
    protocol: str = "openai_chat"


class CredentialEndpointMismatch(ValueError):
    """Raised when an endpoint is not covered by the selected credential."""


def mask_api_key(key: str) -> str:
    k = (key or "").strip()
    if not k or len(k) < 8:
        return ""
    return f"{k[:3]}…{k[-4:]}"


def _vault() -> CredentialVault:
    return CredentialVault.from_base64(settings.credential_encryption_key)


def _encrypted_secret(row: dict) -> EncryptedSecret | None:
    if not row.get("llm_api_key_ciphertext"):
        return None
    return EncryptedSecret(
        ciphertext=row["llm_api_key_ciphertext"],
        nonce=row["llm_api_key_nonce"],
        key_version=row["llm_api_key_version"],
        hint=row.get("llm_api_key_hint") or "",
        audience=row.get("llm_api_key_audience") or "",
    )


def resolve_llm(user_id: str = "default") -> LlmRuntime:
    row = store.get_user_settings(user_id)
    protocol = normalize_llm_protocol(row.get("llm_protocol") or settings.llm_protocol)
    server_protocol = normalize_llm_protocol(settings.llm_protocol)
    base_url = (row.get("llm_base_url") or "").strip() or settings.llm_base_url
    target_origin = outbound_origin(base_url)
    server_origin = outbound_origin(settings.llm_base_url)
    encrypted = _encrypted_secret(row)
    force_demo = bool(row.get("force_demo"))
    if force_demo:
        api_key = ""
    elif encrypted:
        if encrypted.audience != target_origin:
            raise CredentialEndpointMismatch("credential is not valid for endpoint")
        api_key = _vault().decrypt(encrypted, user_id, target_origin)
    else:
        if target_origin != server_origin or protocol != server_protocol:
            raise CredentialEndpointMismatch(
                "custom endpoint or protocol requires a custom key"
            )
        api_key = settings.llm_api_key
    api_key = (api_key or "").strip()
    model = (row.get("llm_model") or "").strip() or settings.llm_model

    if force_demo:
        demo = True
    elif encrypted:
        demo = False
    else:
        demo = settings.use_demo_llm

    return LlmRuntime(
        base_url=base_url,
        api_key=api_key or "not-set",
        model=model,
        protocol=protocol,
        demo=demo,
    )

def get_settings_public(user_id: str = "default") -> dict:
    row = store.get_user_settings(user_id)
    protocol = normalize_llm_protocol(
        row.get("llm_protocol") or settings.llm_protocol
    )
    has_custom_key = bool(row.get("llm_api_key_ciphertext"))
    force_demo = bool(row.get("force_demo"))
    demo_mode_active = (
        True
        if force_demo
        else (False if has_custom_key else settings.use_demo_llm)
    )
    return {
        "llm_base_url": row.get("llm_base_url") or settings.llm_base_url,
        "llm_protocol": protocol,
        "llm_model": row.get("llm_model") or settings.llm_model,
        "llm_api_key_masked": (
            row.get("llm_api_key_hint") or mask_api_key(settings.llm_api_key)
        ),
        "has_custom_key": has_custom_key,
        "force_demo": force_demo,
        "demo_mode_active": demo_mode_active,
        "using_server_env_fallback": not has_custom_key,
    }


def update_settings(user_id: str, payload: dict) -> dict:
    current = store.get_user_settings(user_id)
    safe_payload = dict(payload)
    plaintext_key = (safe_payload.pop("llm_api_key", "") or "").strip()
    current_protocol = normalize_llm_protocol(
        current.get("llm_protocol") or settings.llm_protocol
    )
    target_protocol = current_protocol
    if "llm_protocol" in safe_payload:
        target_protocol = normalize_llm_protocol(safe_payload["llm_protocol"])
    safe_payload["llm_protocol"] = target_protocol
    if "llm_base_url" in safe_payload:
        requested_url = (safe_payload["llm_base_url"] or "").strip()
        safe_payload["llm_base_url"] = (
            validate_outbound_url(requested_url) if requested_url else ""
        )
    effective_url = (
        safe_payload.get("llm_base_url")
        if "llm_base_url" in safe_payload
        else current.get("llm_base_url")
    ) or settings.llm_base_url
    target_origin = outbound_origin(effective_url)
    server_origin = outbound_origin(settings.llm_base_url)
    server_protocol = normalize_llm_protocol(settings.llm_protocol)
    target_force_demo = bool(
        safe_payload.get("force_demo", current.get("force_demo"))
    )
    current_secret = _encrypted_secret(current)
    if plaintext_key:
        encrypted = _vault().encrypt(plaintext_key, user_id, target_origin)
    else:
        encrypted = None
        if current_secret:
            if (
                current_secret.audience != target_origin
                or target_protocol != current_protocol
            ):
                raise CredentialEndpointMismatch(
                    "changing endpoint origin or protocol requires a new key"
                )
        elif not target_force_demo and (
            target_origin != server_origin or target_protocol != server_protocol
        ):
            raise CredentialEndpointMismatch(
                "custom endpoint or protocol requires a custom key"
            )
    store.upsert_user_settings(
        user_id,
        safe_payload,
        encrypted_api_key=encrypted,
        expected_updated_at=current.get("updated_at"),
    )
    return get_settings_public(user_id)

def migrate_legacy_llm_keys() -> int:
    vault: CredentialVault | None = None

    def encrypt(
        plaintext: str,
        user_id: str,
        base_url: str | None,
    ) -> EncryptedSecret:
        nonlocal vault
        vault = vault or _vault()
        audience = outbound_origin(base_url or settings.llm_base_url)
        return vault.encrypt(plaintext, user_id, audience)

    return store.migrate_legacy_llm_keys(encrypt)


def migrate_unbound_llm_keys() -> int:
    vault: CredentialVault | None = None

    def rewrap(
        encrypted: EncryptedSecret,
        user_id: str,
        base_url: str | None,
    ) -> EncryptedSecret:
        nonlocal vault
        vault = vault or _vault()
        audience = outbound_origin(base_url or settings.llm_base_url)
        plaintext = vault.decrypt(encrypted, user_id, audience)
        return vault.encrypt(plaintext, user_id, audience)

    return store.migrate_unbound_llm_keys(rewrap)


def rewrap_credential(
    encrypted: EncryptedSecret,
    previous_user_id: str,
    next_user_id: str,
) -> EncryptedSecret:
    vault = _vault()
    audience = encrypted.audience or outbound_origin(settings.llm_base_url)
    plaintext = vault.decrypt(encrypted, previous_user_id, audience)
    return vault.encrypt(plaintext, next_user_id, audience)
