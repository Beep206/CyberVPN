"""Unit tests for FacebookOAuthProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestFacebookOAuthProvider:
    """Tests for Facebook OAuth provider."""

    @pytest.mark.unit
    def test_authorize_url_contains_required_params(self):
        """Authorization URL contains client_id, redirect_uri, state, and scope."""
        with patch("src.infrastructure.oauth.facebook.settings") as mock_settings:
            mock_settings.facebook_client_id = "facebook_test_id"
            mock_settings.facebook_client_secret = MagicMock()
            mock_settings.facebook_client_secret.get_secret_value.return_value = "facebook_secret"

            from src.infrastructure.oauth.facebook import FacebookOAuthProvider

            provider = FacebookOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_token_abc",
            )

            assert url.startswith("https://www.facebook.com/dialog/oauth")
            assert "client_id=facebook_test_id" in url
            assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
            assert "state=csrf_token_abc" in url
            assert "response_type=code" in url
            assert "email%2Cpublic_profile" in url

    @pytest.mark.unit
    async def test_exchange_code_success_returns_normalized_user(self):
        """Successful code exchange returns normalized Facebook user info."""
        with patch("src.infrastructure.oauth.facebook.settings") as mock_settings:
            mock_settings.facebook_client_id = "facebook_test_id"
            mock_settings.facebook_client_secret = MagicMock()
            mock_settings.facebook_client_secret.get_secret_value.return_value = "facebook_secret"

            from src.infrastructure.oauth.facebook import FacebookOAuthProvider

            provider = FacebookOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "facebook_access_token",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "12345",
                "name": "Test User",
                "short_name": "testuser",
                "email": "test@facebook.com",
                "picture": {
                    "data": {
                        "url": "https://graph.facebook.com/12345/picture?type=large",
                    }
                },
            }

            mock_client = AsyncMock()
            mock_client.get.side_effect = [mock_token_response, mock_user_response]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="facebook_auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is not None
            assert result["id"] == "12345"
            assert result["email"] == "test@facebook.com"
            assert result["username"] == "testuser"
            assert result["name"] == "Test User"
            assert result["avatar_url"] == "https://graph.facebook.com/12345/picture?type=large"
            assert result["access_token"] == "facebook_access_token"
            assert result["refresh_token"] is None

    @pytest.mark.unit
    async def test_exchange_code_missing_access_token_returns_none(self):
        """Missing access token fails the exchange."""
        with patch("src.infrastructure.oauth.facebook.settings") as mock_settings:
            mock_settings.facebook_client_id = "facebook_test_id"
            mock_settings.facebook_client_secret = MagicMock()
            mock_settings.facebook_client_secret.get_secret_value.return_value = "facebook_secret"

            from src.infrastructure.oauth.facebook import FacebookOAuthProvider

            provider = FacebookOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"token_type": "bearer"}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="facebook_auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_httpx_error_returns_none(self):
        """Network failures return None instead of raising."""
        with patch("src.infrastructure.oauth.facebook.settings") as mock_settings:
            mock_settings.facebook_client_id = "facebook_test_id"
            mock_settings.facebook_client_secret = MagicMock()
            mock_settings.facebook_client_secret.get_secret_value.return_value = "facebook_secret"

            from src.infrastructure.oauth.facebook import FacebookOAuthProvider

            provider = FacebookOAuthProvider()

            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("network error")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="facebook_auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None
