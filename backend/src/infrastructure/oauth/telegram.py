"""Telegram OAuth authentication provider with HMAC-SHA256 validation (CRIT-2)."""

import hashlib
import hmac
import logging
import time

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TelegramOAuthProvider:
    """Telegram OAuth authentication provider with proper security validation.

    Security features:
    - HMAC-SHA256 signature validation using bot token
    - auth_date validation to prevent replay attacks
    - Constant-time comparison for hash validation
    """

    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token.get_secret_value()
        self.bot_username = settings.telegram_bot_username
        self.max_auth_age_seconds = settings.telegram_auth_max_age_seconds

    def authorize_url(self, redirect_uri: str) -> str:
        """Generate Telegram OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication

        Returns:
            Telegram auth URL
        """
        base_url = "https://oauth.telegram.org/auth"
        params = f"bot_id={self.bot_username}&origin={redirect_uri}&request_access=write"
        return f"{base_url}?{params}"

    async def exchange_code(self, auth_data: dict[str, str]) -> dict | None:
        """Verify Telegram auth data and extract user information.

        Validates:
        1. HMAC-SHA256 signature
        2. auth_date is within acceptable range

        Args:
            auth_data: Dictionary containing Telegram auth data (id, first_name, hash, etc.)

        Returns:
            User info dict if valid, None otherwise
        """
        if not self._verify_telegram_auth(auth_data):
            logger.warning("Telegram auth validation failed - invalid signature")
            return None

        if not self._verify_auth_date(auth_data):
            logger.warning("Telegram auth validation failed - auth_date too old")
            return None

        return {
            "id": auth_data.get("id"),
            "username": auth_data.get("username"),
            "first_name": auth_data.get("first_name"),
            "last_name": auth_data.get("last_name"),
            "photo_url": auth_data.get("photo_url"),
        }

    def _verify_telegram_auth(self, auth_data: dict[str, str]) -> bool:
        """Verify Telegram authentication data using HMAC-SHA256.

        Following Telegram's verification protocol:
        https://core.telegram.org/widgets/login#checking-authorization

        Args:
            auth_data: Dictionary containing Telegram auth data

        Returns:
            True if data is valid, False otherwise
        """
        check_hash = auth_data.get("hash")
        if not check_hash:
            logger.debug("Telegram auth missing hash")
            return False

        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False

        # Create a copy without the hash
        data_check = {k: v for k, v in auth_data.items() if k != "hash"}

        # Create data check string (key=value pairs sorted alphabetically, joined by newlines)
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_check.items()))

        # Calculate secret key: SHA256 of bot token
        secret_key = hashlib.sha256(self.bot_token.encode()).digest()

        # Calculate expected hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(calculated_hash, check_hash)

    def _verify_auth_date(self, auth_data: dict[str, str]) -> bool:
        """Verify auth_date is within acceptable range.

        Prevents replay attacks by ensuring auth data isn't too old.

        Args:
            auth_data: Dictionary containing Telegram auth data

        Returns:
            True if auth_date is valid, False otherwise
        """
        auth_date_str = auth_data.get("auth_date")
        if not auth_date_str:
            logger.debug("Telegram auth missing auth_date")
            return False

        try:
            auth_date = int(auth_date_str)
        except ValueError:
            logger.debug("Telegram auth_date is not a valid integer")
            return False

        current_time = int(time.time())
        age = current_time - auth_date

        if age > self.max_auth_age_seconds:
            logger.warning(
                "Telegram auth_date too old",
                extra={"auth_age_seconds": age, "max_age": self.max_auth_age_seconds},
            )
            return False

        # Also check for future dates (clock skew tolerance: 5 minutes)
        if age < -300:
            logger.warning(
                "Telegram auth_date is in the future",
                extra={"auth_date": auth_date, "current_time": current_time},
            )
            return False

        return True
