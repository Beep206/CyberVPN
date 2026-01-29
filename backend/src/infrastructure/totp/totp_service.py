import pyotp
from typing import Tuple

class TOTPService:
    """Time-based One-Time Password (TOTP) service for 2FA"""

    def __init__(self):
        self.issuer_name = "CyberVPN"

    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret key

        Returns:
            Base32-encoded secret key
        """
        return pyotp.random_base32()

    def generate_qr_uri(self, secret: str, account_name: str) -> str:
        """
        Generate a provisioning URI for QR code generation

        Args:
            secret: TOTP secret key
            account_name: User's account identifier (email or username)

        Returns:
            Provisioning URI for QR code
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=account_name,
            issuer_name=self.issuer_name
        )

    def verify_code(self, secret: str, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code

        Args:
            secret: TOTP secret key
            code: 6-digit TOTP code to verify
            valid_window: Number of time steps to check before/after current (default: 1)

        Returns:
            True if code is valid, False otherwise
        """
        if not code or len(code) != 6 or not code.isdigit():
            return False

        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)

    def get_current_code(self, secret: str) -> str:
        """
        Get the current TOTP code (mainly for testing)

        Args:
            secret: TOTP secret key

        Returns:
            Current 6-digit TOTP code
        """
        totp = pyotp.TOTP(secret)
        return totp.now()
