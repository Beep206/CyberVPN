"""Unit tests for GoogleOAuthProvider.

Tests authorization URL generation (with and without PKCE),
token exchange success/failure, and user info normalization.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestGoogleOAuthProvider:
    """Tests for Google OAuth 2.0 provider."""

    # ------------------------------------------------------------------
    # authorize_url
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_authorize_url_contains_required_params(self):
        """Authorization URL contains client_id, redirect_uri, response_type, scope."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            # Arrange
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            # Act
            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_state_123",
            )

            # Assert
            assert "client_id=test_client_id" in url
            assert "state=csrf_state_123" in url
            assert "redirect_uri=" in url
            assert "response_type=code" in url
            assert "scope=" in url
            assert "openid" in url
            assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")

    @pytest.mark.unit
    def test_authorize_url_without_state(self):
        """Authorization URL omits state parameter when not provided."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "state=" not in url

    @pytest.mark.unit
    def test_authorize_url_with_pkce(self):
        """Authorization URL includes PKCE code_challenge and method when provided."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_state",
                code_challenge="dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
                code_challenge_method="S256",
            )

            assert "code_challenge=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" in url
            assert "code_challenge_method=S256" in url

    @pytest.mark.unit
    def test_authorize_url_pkce_defaults_to_s256(self):
        """PKCE code_challenge_method defaults to S256 when code_challenge provided."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                code_challenge="some_challenge",
            )

            assert "code_challenge_method=S256" in url

    # ------------------------------------------------------------------
    # exchange_code - success
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_success_returns_normalized_user(self):
        """Successful code exchange returns normalized user info dict."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            # Arrange
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "google_access_token",
                "refresh_token": "google_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "sub": "12345",
                "email": "test@gmail.com",
                "name": "Test User",
                "picture": "https://lh3.googleusercontent.com/photo.jpg",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Act
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code_from_google",
                    redirect_uri="http://localhost/callback",
                )

            # Assert
            assert result is not None
            assert result["id"] == "12345"
            assert result["email"] == "test@gmail.com"
            assert result["username"] == "test@gmail.com"
            assert result["name"] == "Test User"
            assert result["avatar_url"] == "https://lh3.googleusercontent.com/photo.jpg"
            assert result["access_token"] == "google_access_token"
            assert result["refresh_token"] == "google_refresh_token"

    @pytest.mark.unit
    async def test_exchange_code_with_pkce_sends_code_verifier(self):
        """Code exchange includes code_verifier in token payload when provided."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "sub": "1",
                "email": "u@g.com",
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
                    code_verifier="test_verifier_value",
                )

            # Verify code_verifier was included in the POST data
            call_kwargs = mock_client.post.call_args
            posted_data = call_kwargs.kwargs.get("data", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
            assert posted_data.get("code_verifier") == "test_verifier_value"

    # ------------------------------------------------------------------
    # exchange_code - failure paths
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_token_failure_returns_none(self):
        """Token exchange returning non-200 status returns None."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 401

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
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "error": "invalid_grant",
                "error_description": "Code has expired",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="expired_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_missing_access_token_returns_none(self):
        """Token response without access_token key returns None."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

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
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "valid_token",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 403

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
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = ""
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = ""

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            result = await provider.exchange_code(
                code="code",
                redirect_uri="http://localhost/callback",
            )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_network_error_returns_none(self):
        """Network error (httpx.RequestError) during exchange returns None."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_no_refresh_token(self):
        """User info is returned even when refresh_token is absent from token response."""
        with patch("src.infrastructure.oauth.google.settings") as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_client_secret = MagicMock()
            mock_settings.google_client_secret.get_secret_value.return_value = "test_secret"

            from src.infrastructure.oauth.google import GoogleOAuthProvider

            provider = GoogleOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "access_only",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "sub": "99",
                "email": "norefresh@gmail.com",
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
            assert result["refresh_token"] is None
