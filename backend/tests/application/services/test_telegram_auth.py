"""Tests for Telegram OAuth authentication service."""

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

from src.application.services.telegram_auth import (
    InvalidTelegramAuthError,
    TelegramAuthExpiredError,
    TelegramAuthService,
)


@pytest.fixture
def bot_token() -> str:
    """Test bot token."""
    return "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"


@pytest.fixture
def telegram_service(bot_token: str) -> TelegramAuthService:
    """Create TelegramAuthService with test bot token."""
    with patch("src.application.services.telegram_auth.settings") as mock_settings:
        mock_settings.telegram_bot_token.get_secret_value.return_value = bot_token
        mock_settings.telegram_auth_max_age_seconds = 86400
        yield TelegramAuthService()


def create_telegram_auth_data(
    telegram_id: int,
    first_name: str,
    auth_date: int,
    bot_token: str,
    username: str | None = None,
    photo_url: str | None = None,
) -> str:
    """Create valid Telegram auth data with correct HMAC signature."""
    data = {
        "id": telegram_id,
        "first_name": first_name,
        "auth_date": auth_date,
    }
    if username:
        data["username"] = username
    if photo_url:
        data["photo_url"] = photo_url

    # Create data_check_string
    sorted_items = sorted(data.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)

    # Secret key = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Compute HMAC
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    data["hash"] = computed_hash

    # Encode as base64
    return base64.b64encode(json.dumps(data).encode()).decode()


class TestTelegramAuthService:
    """Tests for TelegramAuthService."""

    def test_validate_auth_data_success(
        self, telegram_service: TelegramAuthService, bot_token: str
    ) -> None:
        """Test successful validation of Telegram auth data."""
        auth_date = int(time.time())
        auth_data = create_telegram_auth_data(
            telegram_id=123456789,
            first_name="John",
            username="johndoe",
            auth_date=auth_date,
            bot_token=bot_token,
        )

        result = telegram_service.validate_auth_data(auth_data)

        assert result.telegram_id == 123456789
        assert result.first_name == "John"
        assert result.username == "johndoe"
        assert not result.isExpired if hasattr(result, "isExpired") else True

    def test_validate_auth_data_invalid_signature(
        self, telegram_service: TelegramAuthService, bot_token: str
    ) -> None:
        """Test rejection of auth data with invalid signature."""
        data = {
            "id": 123456789,
            "first_name": "John",
            "auth_date": int(time.time()),
            "hash": "invalid_hash_that_will_not_match",
        }
        auth_data = base64.b64encode(json.dumps(data).encode()).decode()

        with pytest.raises(InvalidTelegramAuthError, match="Invalid signature"):
            telegram_service.validate_auth_data(auth_data)

    def test_validate_auth_data_expired(
        self, telegram_service: TelegramAuthService, bot_token: str
    ) -> None:
        """Test rejection of auth data with expired auth_date."""
        # Create auth data from 25 hours ago (max is 24 hours)
        old_auth_date = int(time.time()) - (25 * 60 * 60)
        auth_data = create_telegram_auth_data(
            telegram_id=123456789,
            first_name="John",
            auth_date=old_auth_date,
            bot_token=bot_token,
        )

        with pytest.raises(TelegramAuthExpiredError):
            telegram_service.validate_auth_data(auth_data)

    def test_validate_auth_data_missing_fields(
        self, telegram_service: TelegramAuthService
    ) -> None:
        """Test rejection of auth data with missing required fields."""
        data = {"id": 123456789}  # Missing auth_date and hash
        auth_data = base64.b64encode(json.dumps(data).encode()).decode()

        with pytest.raises(InvalidTelegramAuthError, match="Missing required fields"):
            telegram_service.validate_auth_data(auth_data)

    def test_validate_auth_data_invalid_base64(
        self, telegram_service: TelegramAuthService
    ) -> None:
        """Test rejection of invalid base64 encoded data."""
        with pytest.raises(InvalidTelegramAuthError, match="Invalid auth data format"):
            telegram_service.validate_auth_data("not_valid_base64!!!")

    def test_validate_auth_data_invalid_json(
        self, telegram_service: TelegramAuthService
    ) -> None:
        """Test rejection of invalid JSON in auth data."""
        invalid_json = base64.b64encode(b"not json at all").decode()

        with pytest.raises(InvalidTelegramAuthError, match="Invalid auth data format"):
            telegram_service.validate_auth_data(invalid_json)

    def test_validate_auth_data_no_bot_token_configured(self) -> None:
        """Test error when bot token is not configured."""
        with patch("src.application.services.telegram_auth.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = ""
            mock_settings.telegram_auth_max_age_seconds = 86400
            service = TelegramAuthService()

            with pytest.raises(InvalidTelegramAuthError, match="not configured"):
                service.validate_auth_data("some_data")
