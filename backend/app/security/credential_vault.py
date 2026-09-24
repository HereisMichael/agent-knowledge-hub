"""Authenticated encryption for user-supplied credentials."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


LEGACY_KEY_VERSION = "v1"
KEY_VERSION = "v2"
NONCE_BYTES = 12


class CredentialVaultUnavailable(RuntimeError):
    """Raised when credential encryption is not safely configured."""


class CredentialDecryptionError(RuntimeError):
    """Raised without leaking why a credential envelope was rejected."""


@dataclass(frozen=True)
class EncryptedSecret:
    ciphertext: str
    nonce: str
    key_version: str
    hint: str
    audience: str = ""


def mask_secret(secret: str) -> str:
    value = (secret or "").strip()
    if len(value) < 8:
        return ""
    return f"{value[:3]}…{value[-4:]}"


class CredentialVault:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise CredentialVaultUnavailable(
                "CREDENTIAL_ENCRYPTION_KEY must decode to exactly 32 bytes"
            )
        self._cipher = AESGCM(key)

    @classmethod
    def from_base64(cls, encoded_key: str) -> "CredentialVault":
        value = (encoded_key or "").strip()
        if not value:
            raise CredentialVaultUnavailable(
                "CREDENTIAL_ENCRYPTION_KEY is required to store credentials"
            )
        try:
            key = base64.b64decode(value, altchars=b"-_", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise CredentialVaultUnavailable(
                "CREDENTIAL_ENCRYPTION_KEY must be valid base64"
            ) from exc
        return cls(key)

    @staticmethod
    def _associated_data(user_id: str, key_version: str, audience: str = "") -> bytes:
        suffix = f":{audience}" if key_version == KEY_VERSION else ""
        return (
            f"agent-knowledge-hub:credential:{user_id}:{key_version}{suffix}"
        ).encode("utf-8")

    def encrypt(self, plaintext: str, user_id: str, audience: str) -> EncryptedSecret:
        value = (plaintext or "").strip()
        normalized_audience = (audience or "").strip()
        if not value or not normalized_audience:
            raise ValueError("credential must not be empty")
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = self._cipher.encrypt(
            nonce,
            value.encode("utf-8"),
            self._associated_data(user_id, KEY_VERSION, normalized_audience),
        )
        return EncryptedSecret(
            ciphertext=base64.urlsafe_b64encode(ciphertext).decode("ascii"),
            nonce=base64.urlsafe_b64encode(nonce).decode("ascii"),
            key_version=KEY_VERSION,
            hint=mask_secret(value),
            audience=normalized_audience,
        )

    def decrypt(
        self,
        secret: EncryptedSecret,
        user_id: str,
        audience: str,
    ) -> str:
        expected_audience = (audience or "").strip()
        if (
            not isinstance(secret.key_version, str)
            or secret.key_version not in {LEGACY_KEY_VERSION, KEY_VERSION}
            or not isinstance(secret.nonce, str)
            or not isinstance(secret.ciphertext, str)
            or not isinstance(user_id, str)
            or (
                secret.key_version == KEY_VERSION
                and (
                    not isinstance(secret.audience, str)
                    or not expected_audience
                    or secret.audience != expected_audience
                )
            )
        ):
            raise CredentialDecryptionError("credential cannot be decrypted")
        try:
            nonce = base64.b64decode(
                secret.nonce,
                altchars=b"-_",
                validate=True,
            )
            ciphertext = base64.b64decode(
                secret.ciphertext,
                altchars=b"-_",
                validate=True,
            )
            if len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
                raise ValueError("malformed credential envelope")
            plaintext = self._cipher.decrypt(
                nonce,
                ciphertext,
                self._associated_data(
                    user_id,
                    secret.key_version,
                    secret.audience if secret.key_version == KEY_VERSION else "",
                ),
            )
            return plaintext.decode("utf-8")
        except (
            InvalidTag,
            ValueError,
            UnicodeDecodeError,
            UnicodeEncodeError,
            binascii.Error,
            TypeError,
            AttributeError,
        ) as exc:
            raise CredentialDecryptionError("credential cannot be decrypted") from exc
