"""Unit tests for MicrosoftOAuthProvider.

Tests authorization URL generation (with PKCE and tenant), token exchange
success/failure, and user info normalization from Microsoft Graph API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


class TestMicrosoftOAuthProvider:
    """Tests for Microsoft OAuth provider."""

    # ------------------------------------------------------------------
    # authorize_url
    # ------------------------------------------------------------------

    @pytest.mark.unit
    def test_authorize_url_contains_required_params(self):
        """Authorization URL contains client_id, redirect_uri, response_type, scope."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            # Arrange
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            # Act
            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_state_ms",
            )

            # Assert
            assert "client_id=ms_client_id" in url
            assert "state=csrf_state_ms" in url
            assert "redirect_uri=http://localhost/callback" in url
            assert "response_type=code" in url
            assert "scope=" in url
            assert "openid" in url
            assert "response_mode=query" in url
            assert "login.microsoftonline.com/common" in url

    @pytest.mark.unit
    def test_authorize_url_uses_custom_tenant(self):
        """Authorization URL uses the configured tenant ID."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "my-org-tenant-id"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "login.microsoftonline.com/my-org-tenant-id" in url

    @pytest.mark.unit
    def test_authorize_url_defaults_to_common_tenant(self):
        """Authorization URL defaults to 'common' tenant when tenant_id is None."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = None

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "login.microsoftonline.com/common" in url

    @pytest.mark.unit
    def test_authorize_url_without_state(self):
        """Authorization URL omits state parameter when not provided."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            url = provider.authorize_url(redirect_uri="http://localhost/callback")

            assert "state=" not in url

    @pytest.mark.unit
    def test_authorize_url_with_pkce(self):
        """Authorization URL includes PKCE parameters when provided."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="state_val",
                code_challenge="pkce_challenge_value",
                code_challenge_method="S256",
            )

            assert "code_challenge=pkce_challenge_value" in url
            assert "code_challenge_method=S256" in url

    # ------------------------------------------------------------------
    # exchange_code - success
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_success_returns_normalized_user(self):
        """Successful code exchange returns normalized user info from Graph API."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            # Arrange
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "ms_access_token",
                "refresh_token": "ms_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "ms_user_12345",
                "displayName": "Test User MS",
                "mail": "test@outlook.com",
                "userPrincipalName": "test@outlook.com",
            }

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.return_value = mock_user_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            # Act
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code_from_ms",
                    redirect_uri="http://localhost/callback",
                )

            # Assert
            assert result is not None
            assert result["id"] == "ms_user_12345"
            assert result["email"] == "test@outlook.com"
            assert result["username"] == "test@outlook.com"
            assert result["name"] == "Test User MS"
            assert result["avatar_url"] is None  # Microsoft Graph doesn't return avatar in /me
            assert result["access_token"] == "ms_access_token"
            assert result["refresh_token"] == "ms_refresh_token"

    @pytest.mark.unit
    async def test_exchange_code_falls_back_to_user_principal_name(self):
        """Email falls back to userPrincipalName when mail is null (personal accounts)."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "personal_user",
                "displayName": "Personal User",
                "mail": None,
                "userPrincipalName": "personal@live.com",
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
            assert result["email"] == "personal@live.com"
            assert result["username"] == "personal@live.com"

    @pytest.mark.unit
    async def test_exchange_code_with_pkce_sends_code_verifier(self):
        """Code exchange includes code_verifier in token payload when provided."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": "1",
                "displayName": "U",
                "mail": "u@ms.com",
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
                    code_verifier="ms_verifier_value",
                )

            call_kwargs = mock_client.post.call_args
            posted_data = call_kwargs.kwargs.get("data", {})
            assert posted_data.get("code_verifier") == "ms_verifier_value"

    # ------------------------------------------------------------------
    # exchange_code - failure paths
    # ------------------------------------------------------------------

    @pytest.mark.unit
    async def test_exchange_code_token_failure_returns_none(self):
        """Token exchange returning non-200 status returns None."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 400

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
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "error": "invalid_client",
                "error_description": "Client authentication failed",
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
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

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
        """User info fetch from Graph API returning non-200 returns None."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "tok",
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
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = ""
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = ""
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            result = await provider.exchange_code(
                code="code",
                redirect_uri="http://localhost/callback",
            )

            assert result is None

    @pytest.mark.unit
    async def test_exchange_code_network_error_returns_none(self):
        """Network error during exchange returns None."""
        with patch("src.infrastructure.oauth.microsoft.settings") as mock_settings:
            mock_settings.microsoft_client_id = "ms_client_id"
            mock_settings.microsoft_client_secret = MagicMock()
            mock_settings.microsoft_client_secret.get_secret_value.return_value = "ms_secret"
            mock_settings.microsoft_tenant_id = "common"

            from src.infrastructure.oauth.microsoft import MicrosoftOAuthProvider

            provider = MicrosoftOAuthProvider()

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("DNS resolution failed")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None
