"""Unit tests for TwitterOAuthProvider.

Tests authorization URL generation (with PKCE required), HTTP Basic Auth
token exchange, and user info normalization from Twitter API v2.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestTwitterOAuthProvider:
    """Tests for X (Twitter) OAuth 2.0 provider."""

    # ------------------------------------------------------------------
    # authorize_url
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_authorize_url_contains_required_params(self):
        """Authorization URL contains client_id, redirect_uri, response_type, scope."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            # Arrange
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            # Act
            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_tw",
            )

            # Assert
            assert "client_id=tw_client_id" in url
            assert "state=csrf_tw" in url
            assert "redirect_uri=http://localhost/callback" in url
            assert "response_type=code" in url
            assert "users.read" in url
            assert "tweet.read" in url
            assert url.startswith("https://twitter.com/i/oauth2/authorize")

    @pytest.mark.unit
    def test_authorize_url_without_state(self):
        """Authorization URL omits state parameter when not provided."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "state=" not in url

    @pytest.mark.unit
    def test_authorize_url_with_pkce(self):
        """Authorization URL includes PKCE code_challenge and method."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="state",
                code_challenge="tw_pkce_challenge",
                code_challenge_method="S256",
            )

            assert "code_challenge=tw_pkce_challenge" in url
            assert "code_challenge_method=S256" in url

    @pytest.mark.unit
    def test_authorize_url_pkce_defaults_to_s256(self):
        """PKCE code_challenge_method defaults to S256 when method is None."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                code_challenge="challenge_val",
                code_challenge_method=None,
            )

            assert "code_challenge_method=S256" in url

    # ------------------------------------------------------------------
    # exchange_code - success
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_success_returns_normalized_user(self):
        """Successful code exchange returns normalized user info from Twitter v2."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            # Arrange
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tw_access_token",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "data": {
                    "id": "tw_12345",
                    "username": "testuser",
                    "name": "Test Twitter User",
                    "profile_image_url": "https://pbs.twimg.com/profile_images/photo.jpg",
                },
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Act
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code_from_twitter",
                    redirect_uri="http://localhost/callback",
                    code_verifier="tw_verifier",
                )

            # Assert
            assert result is not None
            assert result["id"] == "tw_12345"
            assert result["email"] is None  # Twitter basic scope doesn't provide email
            assert result["username"] == "testuser"
            assert result["name"] == "Test Twitter User"
            assert result["avatar_url"] == "https://pbs.twimg.com/profile_images/photo.jpg"
            assert result["access_token"] == "tw_access_token"
            assert result["refresh_token"] is None

    @pytest.mark.unit
    async def test_exchange_code_uses_http_basic_auth(self):
        """Token exchange uses HTTP Basic Auth header with client_id:client_secret."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "data": {"id": "1", "username": "u", "name": "N"},
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            # Verify HTTP Basic Auth header
            call_kwargs = mock_client.post.call_args
            headers = call_kwargs.kwargs.get("headers", {})
            expected_credentials = base64.b64encode(b"tw_client_id:tw_secret").decode()
            assert headers.get("Authorization") == f"Basic {expected_credentials}"
            assert headers.get("Content-Type") == "application/x-www-form-urlencoded"

    @pytest.mark.unit
    async def test_exchange_code_sends_code_verifier(self):
        """Token exchange includes code_verifier in form data."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "data": {"id": "1", "username": "u", "name": "N"},
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                    code_verifier="tw_pkce_verifier",
                )

            call_kwargs = mock_client.post.call_args
            posted_data = call_kwargs.kwargs.get("data", {})
            assert posted_data.get("code_verifier") == "tw_pkce_verifier"

    @pytest.mark.unit
    async def test_exchange_code_empty_data_returns_empty_fields(self):
        """User response with empty data dict returns None-ish fields gracefully."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {"data": {}}

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
            assert result["id"] == "None"
            assert result["email"] is None
            assert result["username"] is None
            assert result["refresh_token"] is None

    # ------------------------------------------------------------------
    # exchange_code - failure paths
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_token_failure_returns_none(self):
        """Token exchange returning non-200 status returns None."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 403

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="bad_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_error_in_token_data_returns_none(self):
        """Token response containing 'error' key returns None."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "error": "invalid_request",
                "error_description": "Value passed for code was invalid",
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
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "token_type": "bearer",
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
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 429  # Rate limited

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
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = ""
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = ""

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            result = await provider.exchange_code(
                code="code",
                redirect_uri="http://localhost/callback",
            )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_network_error_returns_none(self):
        """Network error during exchange returns None."""
        with patch("src.infrastructure.oauth.twitter.settings") as mock_settings:
            mock_settings.twitter_client_id = "tw_client_id"
            mock_settings.twitter_client_secret = MagicMock()
            mock_settings.twitter_client_secret.get_secret_value.return_value = "tw_secret"

            from src.infrastructure.oauth.twitter import TwitterOAuthProvider

            provider = TwitterOAuthProvider()

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ReadTimeout("Read timed out")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None
