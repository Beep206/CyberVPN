"""Unit tests for Telegram Mini App initData HMAC-SHA256 validation."""

import hashlib
import hmac
import json
import time
from unittest.mock import patch
from urllib.parse import quote, urlencode

import pytest

from src.infrastructure.oauth.telegram import TelegramOAuthProvider


def _build_init_data(
    bot_token: str,
    user: dict | None = None,
    auth_date: int | None = None,
    extra_params: dict | None = None,
) -> str:
    """Build a valid initData string signed with the given bot_token."""
    if auth_date is None:
        auth_date = int(time.time())
    if user is None:
        user = {"id": 123456789, "first_name": "Test", "username": "testuser"}

    params: dict[str, str] = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
    }
    if extra_params:
        params.update(extra_params)

    # Build data_check_string (sorted, excluding hash)
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    # Secret key: HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # Hash
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value

    return urlencode(params, quote_via=quote)


BOT_TOKEN = "7654321:AAHfVcYK-test-token-for-unit-tests"


class TestValidateInitData:
    """Tests for TelegramOAuthProvider.validate_init_data()."""

    @pytest.fixture(autouse=True)
    def _mock_settings(self):
        with patch("src.infrastructure.oauth.telegram.settings") as mock:
            mock.telegram_bot_token.get_secret_value.return_value = BOT_TOKEN
            mock.telegram_bot_username = "test_bot"
            mock.telegram_auth_max_age_seconds = 86400
            yield mock

    def _provider(self) -> TelegramOAuthProvider:
        return TelegramOAuthProvider()

    @pytest.mark.unit
    def test_valid_init_data_returns_user(self):
        provider = self._provider()
        init_data = _build_init_data(BOT_TOKEN)
        result = provider.validate_init_data(init_data)
        assert result is not None
        assert result["id"] == "123456789"
        assert result["username"] == "testuser"
        assert result["first_name"] == "Test"

    @pytest.mark.unit
    def test_wrong_bot_token_fails(self):
        provider = self._provider()
        init_data = _build_init_data("wrong_bot_token_value_here")
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_tampered_data_fails(self):
        provider = self._provider()
        init_data = _build_init_data(BOT_TOKEN)
        # Tamper with auth_date
        init_data = init_data.replace("auth_date=", "auth_date=0")
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_missing_hash_fails(self):
        provider = self._provider()
        params = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 1})}
        init_data = urlencode(params, quote_via=quote)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_empty_init_data_fails(self):
        provider = self._provider()
        assert provider.validate_init_data("") is None

    @pytest.mark.unit
    def test_missing_user_field_fails(self):
        """initData without user field returns None even if hash is valid."""
        provider = self._provider()
        auth_date = str(int(time.time()))
        params = {"auth_date": auth_date}
        data_check_string = f"auth_date={auth_date}"
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        h = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
        params["hash"] = h
        init_data = urlencode(params, quote_via=quote)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_expired_auth_date_fails(self):
        provider = self._provider()
        old_auth_date = int(time.time()) - 90000  # > 24h
        init_data = _build_init_data(BOT_TOKEN, auth_date=old_auth_date)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_future_auth_date_fails(self):
        provider = self._provider()
        future_auth_date = int(time.time()) + 600  # 10 min in future (> 5 min tolerance)
        init_data = _build_init_data(BOT_TOKEN, auth_date=future_auth_date)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_user_with_all_fields(self):
        provider = self._provider()
        user = {
            "id": 999,
            "first_name": "Alice",
            "last_name": "Smith",
            "username": "alice_s",
            "photo_url": "https://t.me/i/userpic/alice.jpg",
            "language_code": "en",
        }
        init_data = _build_init_data(BOT_TOKEN, user=user)
        result = provider.validate_init_data(init_data)
        assert result is not None
        assert result["id"] == "999"
        assert result["first_name"] == "Alice"
        assert result["last_name"] == "Smith"
        assert result["username"] == "alice_s"
        assert result["language_code"] == "en"

    @pytest.mark.unit
    def test_user_without_username(self):
        provider = self._provider()
        user = {"id": 555, "first_name": "Bob"}
        init_data = _build_init_data(BOT_TOKEN, user=user)
        result = provider.validate_init_data(init_data)
        assert result is not None
        assert result["id"] == "555"
        assert result["username"] is None

    @pytest.mark.unit
    def test_invalid_user_json_fails(self):
        """If user field contains invalid JSON, return None."""
        provider = self._provider()
        auth_date = str(int(time.time()))
        params = {"auth_date": auth_date, "user": "not-valid-json"}
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        h = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
        params["hash"] = h
        init_data = urlencode(params, quote_via=quote)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_no_bot_token_configured_fails(self, _mock_settings):
        _mock_settings.telegram_bot_token.get_secret_value.return_value = ""
        provider = self._provider()
        init_data = _build_init_data(BOT_TOKEN)
        result = provider.validate_init_data(init_data)
        assert result is None

    @pytest.mark.unit
    def test_extra_params_included_in_check(self):
        """Extra params (like query_id) are included in hash calculation."""
        provider = self._provider()
        extra = {"query_id": "AAGmHQAAAAAApmEdSz12345"}
        init_data = _build_init_data(BOT_TOKEN, extra_params=extra)
        result = provider.validate_init_data(init_data)
        assert result is not None
