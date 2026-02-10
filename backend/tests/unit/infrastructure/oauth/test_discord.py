"""Unit tests for DiscordOAuthProvider.

Tests authorization URL generation, token exchange success/failure,
user info normalization, and avatar URL construction.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestDiscordOAuthProvider:
    """Tests for Discord OAuth provider."""

    # ------------------------------------------------------------------
    # authorize_url
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_authorize_url_contains_required_params(self):
        """Authorization URL contains client_id, redirect_uri, response_type, scope."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            # Arrange
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            # Act
            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_token_abc",
            )

            # Assert
            assert "client_id=discord_test_id" in url
            assert "state=csrf_token_abc" in url
            assert "redirect_uri=http://localhost/callback" in url
            assert "response_type=code" in url
            assert "identify" in url
            assert "email" in url
            assert url.startswith("https://discord.com/oauth2/authorize")

    @pytest.mark.unit
    def test_authorize_url_without_state(self):
        """Authorization URL omits state parameter when not provided."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "state=" not in url

    # ------------------------------------------------------------------
    # exchange_code - success
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_success_returns_normalized_user(self):
        """Successful code exchange returns normalized user info with avatar URL."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            # Arrange
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "discord_access_token",
                "refresh_token": "discord_refresh_token",
                "token_type": "Bearer",
                "expires_in": 604800,
                "scope": "identify email",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "12345",
                "username": "testuser",
                "global_name": "Test User Display",
                "email": "test@discord.com",
                "avatar": "abc123hash",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Act
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code_from_discord",
                    redirect_uri="http://localhost/callback",
                )

            # Assert
            assert result is not None
            assert result["id"] == "12345"
            assert result["email"] == "test@discord.com"
            assert result["username"] == "testuser"
            assert result["name"] == "Test User Display"
            assert result["avatar_url"] == "https://cdn.discordapp.com/avatars/12345/abc123hash.png"
            assert result["access_token"] == "discord_access_token"
            assert result["refresh_token"] == "discord_refresh_token"

    @pytest.mark.unit
    async def test_exchange_code_no_avatar_returns_none_avatar_url(self):
        """User without avatar hash gets None avatar_url."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "99",
                "username": "noavatar",
                "email": "no@avatar.com",
                "avatar": None,
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is not None
            assert result["avatar_url"] is None

    @pytest.mark.unit
    async def test_exchange_code_no_global_name_falls_back_to_username(self):
        """Name falls back to username when global_name is absent."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "77",
                "username": "fallbackuser",
                "email": "fb@discord.com",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is not None
            assert result["name"] == "fallbackuser"

    # ------------------------------------------------------------------
    # exchange_code - failure paths
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_token_failure_returns_none(self):
        """Token exchange returning non-200 status returns None."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 400

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="invalid_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_error_in_token_data_returns_none(self):
        """Token response containing 'error' key returns None."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Invalid code",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_missing_access_token_returns_none(self):
        """Token response without access_token key returns None."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "token_type": "Bearer",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_user_info_failure_returns_none(self):
        """User info fetch returning non-200 status returns None."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "valid_token",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 401

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_missing_credentials_returns_none(self):
        """Missing client credentials returns None without HTTP calls."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = ""
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = ""

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            result = await provider.exchange_code(
                code="code",
                redirect_uri="http://localhost/callback",
            )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_network_error_returns_none(self):
        """Network error during exchange returns None."""
        with patch("src.infrastructure.oauth.discord.settings") as mock_settings:
            mock_settings.discord_client_id = "discord_test_id"
            mock_settings.discord_client_secret = MagicMock()
            mock_settings.discord_client_secret.get_secret_value.return_value = "discord_secret"

            from src.infrastructure.oauth.discord import DiscordOAuthProvider

            provider = DiscordOAuthProvider()

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectTimeout("Timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None
