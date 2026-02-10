"""Telegram Login Widget authentication service.

Validates Telegram authentication data using HMAC-SHA256 signature
as per https://core.telegram.org/widgets/login#checking-authorization
"""

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

from src.config.settings import settings


class TelegramUserData(TypedDict, total=False):
    """Telegram user data from auth callback."""

    id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    auth_date: int
    hash: str


class InvalidTelegramAuthError(Exception):
    """Raised when Telegram authentication data is invalid."""

    def __init__(self, message: str = "Invalid Telegram authentication data"):
        self.message = message
        super().__init__(self.message)


class TelegramAuthExpiredError(Exception):
    """Raised when Telegram auth_date is too old."""

    def __init__(self, message: str = "Telegram authentication has expired"):
        self.message = message
        super().__init__(self.message)


@dataclass
class TelegramAuthResult:
    """Result of successful Telegram authentication validation."""

    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    auth_date: datetime


class TelegramAuthService:
    """Service for validating Telegram Login Widget authentication.

    Validates HMAC-SHA256 signatures using the bot token and checks
    that auth_date is within the allowed time window.
    """

    def __init__(self) -> None:
        self._bot_token = settings.telegram_bot_token.get_secret_value()
        self._max_age_seconds = settings.telegram_auth_max_age_seconds

    def validate_auth_data(self, auth_data_b64: str) -> TelegramAuthResult:
        """Validate Telegram auth data and return user information.

        Args:
            auth_data_b64: Base64-encoded JSON string containing Telegram auth data.

        Returns:
            TelegramAuthResult with validated user data.

        Raises:
            InvalidTelegramAuthError: If signature is invalid or data malformed.
            TelegramAuthExpiredError: If auth_date is older than max_age_seconds.
        """
        if not self._bot_token:
            raise InvalidTelegramAuthError("Telegram bot token not configured")

        # Decode base64 auth data
        try:
            auth_data_json = base64.b64decode(auth_data_b64).decode("utf-8")
            auth_data: TelegramUserData = json.loads(auth_data_json)
        except (ValueError, json.JSONDecodeError) as e:
            raise InvalidTelegramAuthError(f"Invalid auth data format: {e}") from e

        # Validate required fields
        if "id" not in auth_data or "auth_date" not in auth_data or "hash" not in auth_data:
            raise InvalidTelegramAuthError("Missing required fields in auth data")

        # Check auth_date freshness
        auth_timestamp = auth_data["auth_date"]
        auth_datetime = datetime.fromtimestamp(auth_timestamp, tz=UTC)
        now = datetime.now(UTC)
        age_seconds = (now - auth_datetime).total_seconds()

        if age_seconds > self._max_age_seconds:
            raise TelegramAuthExpiredError(
                f"Auth data is {int(age_seconds)} seconds old, max allowed: {self._max_age_seconds}"
            )

        # Validate HMAC-SHA256 signature
        provided_hash = auth_data.pop("hash")
        if not self._verify_signature(dict(auth_data), provided_hash):
            raise InvalidTelegramAuthError("Invalid signature")

        return TelegramAuthResult(
            telegram_id=auth_data["id"],
            first_name=auth_data.get("first_name", ""),
            last_name=auth_data.get("last_name"),
            username=auth_data.get("username"),
            photo_url=auth_data.get("photo_url"),
            auth_date=auth_datetime,
        )

    def _verify_signature(self, data: dict, provided_hash: str) -> bool:
        """Verify HMAC-SHA256 signature of Telegram auth data.

        According to Telegram docs:
        1. Create data_check_string by sorting keys alphabetically and
           joining as "key=value" with newlines
        2. Compute SHA256 hash of bot token (this is the secret key)
        3. Compute HMAC-SHA256(data_check_string, secret_key)
        4. Compare with provided hash
        """
        # Create data_check_string
        sorted_items = sorted(data.items())
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

        # Secret key = SHA256(bot_token)
        secret_key = hashlib.sha256(self._bot_token.encode()).digest()

        # Compute HMAC
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_hash, provided_hash)
