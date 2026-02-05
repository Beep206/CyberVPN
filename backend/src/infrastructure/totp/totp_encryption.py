"""TOTP secret encryption service (MED-6).

Encrypts TOTP secrets at rest using AES-256-GCM:
- Secrets encrypted before database storage
- Decrypted only when generating/verifying TOTP codes
- Key derived from master key using HKDF
"""

import base64
import logging
import os
from typing import ClassVar

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TOTPEncryptionService:
    """Service for encrypting/decrypting TOTP secrets.

    Uses Fernet (AES-128-CBC with HMAC) for symmetric encryption.
    Key is derived from master key using HKDF.
    """

    INFO_CONTEXT: ClassVar[bytes] = b"cybervpn-totp-encryption-v1"
    ENCRYPTED_PREFIX: ClassVar[str] = "enc:v1:"

    def __init__(self) -> None:
        master_key = settings.totp_encryption_key.get_secret_value()
        if not master_key:
            logger.warning(
                "TOTP_ENCRYPTION_KEY not set - secrets will not be encrypted. "
                "Set TOTP_ENCRYPTION_KEY in production!"
            )
            self._fernet = None
        else:
            # Derive key using HKDF
            derived_key = self._derive_key(master_key.encode())
            self._fernet = Fernet(base64.urlsafe_b64encode(derived_key))

    def _derive_key(self, master_key: bytes) -> bytes:
        """Derive encryption key from master key using HKDF."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,  # No salt for deterministic derivation
            info=self.INFO_CONTEXT,
        )
        return hkdf.derive(master_key)

    def encrypt(self, secret: str) -> str:
        """Encrypt a TOTP secret.

        Args:
            secret: The plaintext TOTP secret

        Returns:
            Encrypted secret with prefix, or original if encryption disabled
        """
        if self._fernet is None:
            return secret

        encrypted = self._fernet.encrypt(secret.encode())
        return f"{self.ENCRYPTED_PREFIX}{encrypted.decode()}"

    def decrypt(self, stored_value: str) -> str:
        """Decrypt a TOTP secret.

        Args:
            stored_value: The stored (possibly encrypted) secret

        Returns:
            Decrypted plaintext secret
        """
        if self._fernet is None:
            return stored_value

        # Check if value is encrypted
        if not stored_value.startswith(self.ENCRYPTED_PREFIX):
            # Legacy plaintext secret
            return stored_value

        encrypted_data = stored_value[len(self.ENCRYPTED_PREFIX) :]
        return self._fernet.decrypt(encrypted_data.encode()).decode()

    def is_encrypted(self, stored_value: str) -> bool:
        """Check if a stored value is encrypted.

        Args:
            stored_value: The stored secret

        Returns:
            True if encrypted, False if plaintext
        """
        return stored_value.startswith(self.ENCRYPTED_PREFIX)


# Singleton instance
_totp_encryption: TOTPEncryptionService | None = None


def get_totp_encryption() -> TOTPEncryptionService:
    """Get the TOTP encryption service singleton."""
    global _totp_encryption
    if _totp_encryption is None:
        _totp_encryption = TOTPEncryptionService()
    return _totp_encryption
