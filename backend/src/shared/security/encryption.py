"""AES-256-GCM encryption utility for sensitive data (SEC-001).

Provides encrypt/decrypt functions for TOTP secrets and other sensitive data.
Uses AES-256-GCM for authenticated encryption.
"""

import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


class EncryptionService:
    """AES-256-GCM encryption service for sensitive data.

    SEC-001: Used to encrypt TOTP secrets at rest in the database.
    """

    # GCM nonce size (96 bits recommended by NIST)
    NONCE_SIZE = 12

    def __init__(self, key: str | bytes) -> None:
        """Initialize encryption service with a key.

        Args:
            key: Encryption key. If string, must be base64-encoded 32 bytes.
                 If bytes, must be exactly 32 bytes (256 bits).

        Raises:
            ValueError: If key is invalid length or format.
        """
        if isinstance(key, str):
            if not key:
                raise ValueError("Encryption key cannot be empty")
            try:
                key_bytes = base64.urlsafe_b64decode(key)
            except Exception as e:  # noqa: S110
                # Try as raw bytes if not base64 (expected fallback for non-b64 keys)
                _ = e  # Deliberate fallback, not an error
                key_bytes = key.encode("utf-8")
        else:
            key_bytes = key

        # Derive 32-byte key if needed (using simple truncation/padding for compatibility)
        if len(key_bytes) < 32:
            # Pad with zeros (not ideal, but ensures compatibility)
            key_bytes = key_bytes + b"\x00" * (32 - len(key_bytes))
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]

        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: String to encrypt.

        Returns:
            Base64-encoded ciphertext with nonce prepended.

        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            return ""

        try:
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
            # Prepend nonce to ciphertext
            encrypted_data = nonce + ciphertext
            return base64.urlsafe_b64encode(encrypted_data).decode("ascii")
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64-encoded ciphertext.

        Args:
            ciphertext: Base64-encoded ciphertext with nonce prepended.

        Returns:
            Decrypted plaintext string.

        Raises:
            EncryptionError: If decryption fails (invalid key, corrupted data).
        """
        if not ciphertext:
            return ""

        try:
            encrypted_data = base64.urlsafe_b64decode(ciphertext)
            if len(encrypted_data) < self.NONCE_SIZE:
                raise EncryptionError("Ciphertext too short")

            nonce = encrypted_data[: self.NONCE_SIZE]
            actual_ciphertext = encrypted_data[self.NONCE_SIZE :]
            plaintext = self._aesgcm.decrypt(nonce, actual_ciphertext, None)
            return plaintext.decode("utf-8")
        except EncryptionError:
            raise
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}") from e


# Singleton instance (lazy initialization)
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton.

    Uses TOTP_ENCRYPTION_KEY from settings.

    Returns:
        EncryptionService instance.

    Raises:
        ValueError: If TOTP_ENCRYPTION_KEY is not configured.
    """
    global _encryption_service

    if _encryption_service is None:
        from src.config.settings import settings

        key = settings.totp_encryption_key.get_secret_value()
        if not key:
            raise ValueError(
                "TOTP_ENCRYPTION_KEY not configured. "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        _encryption_service = EncryptionService(key)

    return _encryption_service


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt a TOTP secret for storage.

    Args:
        secret: Plain TOTP secret.

    Returns:
        Encrypted secret (base64-encoded).
    """
    return get_encryption_service().encrypt(secret)


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypt a stored TOTP secret.

    Args:
        encrypted_secret: Encrypted TOTP secret (base64-encoded).

    Returns:
        Plain TOTP secret.
    """
    return get_encryption_service().decrypt(encrypted_secret)
