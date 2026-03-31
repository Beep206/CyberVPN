"""Transparent encrypted text column type for sensitive OAuth provider tokens."""

from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from src.config.settings import settings
from src.shared.security.encryption import (
    EncryptionError,
    decrypt_oauth_token,
    encrypt_oauth_token,
)

ENCRYPTED_VALUE_PREFIX = "enc::v1::"


class EncryptedText(TypeDecorator[str]):
    """Encrypt values on write and decrypt them on read.

    Rollout behavior:
    - New writes are encrypted when an encryption key is configured.
    - Legacy plaintext rows remain readable while fallback is enabled.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, _dialect) -> str | None:
        if value is None or value == "":
            return value

        encrypted = encrypt_oauth_token(value)
        if encrypted == value:
            return value

        return f"{ENCRYPTED_VALUE_PREFIX}{encrypted}"

    def process_result_value(self, value: str | None, _dialect) -> str | None:
        if value is None or value == "":
            return value

        if value.startswith(ENCRYPTED_VALUE_PREFIX):
            encrypted_value = value.removeprefix(ENCRYPTED_VALUE_PREFIX)
            try:
                return decrypt_oauth_token(encrypted_value)
            except EncryptionError:
                if not settings.oauth_token_plaintext_fallback_enabled:
                    raise
                return value

        if settings.oauth_token_plaintext_fallback_enabled:
            return value

        raise EncryptionError("OAuth token column contains legacy plaintext while plaintext fallback is disabled.")
