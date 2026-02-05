import logging

import pyotp

from src.config.settings import settings
from src.shared.security.encryption import EncryptionError, EncryptionService

logger = logging.getLogger(__name__)


class TOTPService:
    """Time-based One-Time Password (TOTP) service for 2FA.

    SEC-001: Supports encryption of TOTP secrets at rest.
    """

    def __init__(self):
        self.issuer_name = "CyberVPN"
        self._encryption_service: EncryptionService | None = None

    @property
    def encryption_service(self) -> EncryptionService | None:
        """Lazy-load encryption service if key is configured."""
        if self._encryption_service is None:
            key = settings.totp_encryption_key.get_secret_value()
            if key:
                self._encryption_service = EncryptionService(key)
        return self._encryption_service

    def encrypt_secret(self, secret: str) -> str:
        """SEC-001: Encrypt TOTP secret for storage.

        Args:
            secret: Plain TOTP secret.

        Returns:
            Encrypted secret if encryption is configured, otherwise plain secret.
        """
        if self.encryption_service:
            try:
                return self.encryption_service.encrypt(secret)
            except EncryptionError as e:
                logger.error("Failed to encrypt TOTP secret: %s", e)
                raise
        return secret

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """SEC-001: Decrypt stored TOTP secret.

        Args:
            encrypted_secret: Encrypted or plain TOTP secret.

        Returns:
            Plain TOTP secret.
        """
        if not self.encryption_service:
            return encrypted_secret

        try:
            return self.encryption_service.decrypt(encrypted_secret)
        except EncryptionError:
            # Might be a plain secret from before encryption was enabled
            logger.warning("Failed to decrypt TOTP secret, assuming plain text")
            return encrypted_secret

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret key.

        SEC-001: Returns encrypted secret if encryption is configured.

        Returns:
            Base32-encoded secret key (encrypted if configured).
        """
        plain_secret = pyotp.random_base32()
        return self.encrypt_secret(plain_secret)

    def generate_qr_uri(self, secret: str, account_name: str) -> str:
        """
        Generate a provisioning URI for QR code generation.

        SEC-001: Decrypts secret if encrypted.

        Args:
            secret: TOTP secret key (may be encrypted).
            account_name: User's account identifier (email or username).

        Returns:
            Provisioning URI for QR code.
        """
        plain_secret = self.decrypt_secret(secret)
        totp = pyotp.TOTP(plain_secret)
        return totp.provisioning_uri(name=account_name, issuer_name=self.issuer_name)

    def verify_code(self, secret: str, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code.

        SEC-001: Decrypts secret if encrypted before verification.

        Args:
            secret: TOTP secret key (may be encrypted).
            code: 6-digit TOTP code to verify.
            valid_window: Number of time steps to check before/after current (default: 1).

        Returns:
            True if code is valid, False otherwise.
        """
        if not code or len(code) != 6 or not code.isdigit():
            return False

        plain_secret = self.decrypt_secret(secret)
        totp = pyotp.TOTP(plain_secret)
        return totp.verify(code, valid_window=valid_window)

    def get_current_code(self, secret: str) -> str:
        """
        Get the current TOTP code (mainly for testing).

        SEC-001: Decrypts secret if encrypted.

        Args:
            secret: TOTP secret key (may be encrypted).

        Returns:
            Current 6-digit TOTP code.
        """
        plain_secret = self.decrypt_secret(secret)
        totp = pyotp.TOTP(plain_secret)
        return totp.now()
