"""Telegram OAuth authentication provider with HMAC-SHA256 validation (CRIT-2)."""

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qs, unquote

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

    def validate_init_data(self, init_data: str) -> dict | None:
        """Validate Telegram Mini App initData using HMAC-SHA256.

        Following Telegram's verification protocol:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Steps:
        1. Parse init_data as URL-encoded string.
        2. Build data_check_string from sorted key=value pairs (excluding hash).
        3. Compute secret_key = HMAC-SHA256("WebAppData", bot_token).
        4. Compute expected_hash = HMAC-SHA256(secret_key, data_check_string).
        5. Compare with constant-time hmac.compare_digest.
        6. Validate auth_date freshness.

        Args:
            init_data: Raw URL-encoded initData string from Telegram.WebApp.initData

        Returns:
            Parsed user dict if valid, None otherwise.
        """
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return None

        if not init_data:
            logger.debug("Empty initData")
            return None

        # Parse URL-encoded initData
        parsed = parse_qs(init_data, keep_blank_values=True)
        # parse_qs returns lists; flatten to single values
        params: dict[str, str] = {k: v[0] for k, v in parsed.items()}

        check_hash = params.get("hash")
        if not check_hash:
            logger.debug("initData missing hash")
            return None

        # Build data_check_string: sorted key=value pairs excluding "hash"
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items()) if k != "hash"
        )

        # Secret key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            self.bot_token.encode(),
            hashlib.sha256,
        ).digest()

        # Expected hash: HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, check_hash):
            logger.warning("initData HMAC validation failed")
            return None

        # Validate auth_date freshness
        auth_date_str = params.get("auth_date")
        if not auth_date_str:
            logger.debug("initData missing auth_date")
            return None

        if not self._verify_auth_date({"auth_date": auth_date_str}):
            return None

        # Extract user from the "user" JSON field
        user_json = params.get("user")
        if not user_json:
            logger.debug("initData missing user field")
            return None

        try:
            user_data = json.loads(unquote(user_json))
        except (json.JSONDecodeError, ValueError):
            logger.warning("initData user field is not valid JSON")
            return None

        return {
            "id": str(user_data.get("id", "")),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "username": user_data.get("username"),
            "photo_url": user_data.get("photo_url"),
            "language_code": user_data.get("language_code"),
        }
