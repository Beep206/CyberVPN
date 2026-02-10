"""Security tests for OAuth validation (CRIT-2).

Tests that:
1. Telegram HMAC validation rejects forged data
2. State parameter protects against CSRF
"""

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, patch

import pytest


class TestTelegramHMACValidation:
    """Test Telegram HMAC-SHA256 signature validation."""

    def test_valid_hmac_signature_passes(self):
        """Valid HMAC signature passes validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            # Create valid auth data
            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
            }

            # Calculate valid hash
            data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(auth_data.items()))
            secret_key = hashlib.sha256(b"test_token").digest()
            valid_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

            auth_data["hash"] = valid_hash

            assert provider._verify_telegram_auth(auth_data) is True

    def test_invalid_hmac_signature_fails(self):
        """Forged HMAC signature fails validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
                "hash": "invalid_forged_hash_that_should_not_work",
            }

            assert provider._verify_telegram_auth(auth_data) is False

    def test_missing_hash_fails(self):
        """Missing hash fails validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
                # No hash field
            }

            assert provider._verify_telegram_auth(auth_data) is False

    def test_old_auth_date_fails(self):
        """Auth date older than max age fails."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400  # 24 hours

            provider = TelegramOAuthProvider()

            # Auth date from 2 days ago
            old_auth_date = str(int(time.time()) - (2 * 86400))

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": old_auth_date,
            }

            assert provider._verify_auth_date(auth_data) is False


class TestOAuthStateService:
    """Test OAuth state service for CSRF protection."""

    @pytest.mark.asyncio
    async def test_generate_creates_state_in_redis(self):
        """State generation stores data in Redis."""
        from src.application.services.oauth_state_service import OAuthStateService

        mock_redis = AsyncMock()
        service = OAuthStateService(mock_redis)

        state, code_challenge = await service.generate(
            provider="github",
            user_id="user-123",
            ip_address="1.2.3.4",
        )

        assert len(state) > 20  # Should be a secure random token
        assert code_challenge is None  # No PKCE by default
        mock_redis.setex.assert_called_once()
