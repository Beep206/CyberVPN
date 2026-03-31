"""Unit tests for GitHubOAuthProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestGitHubOAuthProvider:
    """Tests for GitHub OAuth provider."""

    @pytest.mark.unit
    def test_authorize_url_includes_pkce_when_requested(self):
        """GitHub authorize URL carries PKCE challenge fields for web login."""
        with patch("src.infrastructure.oauth.github.settings") as mock_settings:
            mock_settings.github_client_id = "github_test_id"
            mock_settings.github_client_secret = MagicMock()
            mock_settings.github_client_secret.get_secret_value.return_value = "github_secret"

            from src.infrastructure.oauth.github import GitHubOAuthProvider

            provider = GitHubOAuthProvider()

            url = provider.authorize_url(
                redirect_uri="http://localhost/callback",
                state="csrf_token_abc",
                code_challenge="challenge_123",
            )

            assert url.startswith("https://github.com/login/oauth/authorize")
            assert "client_id=github_test_id" in url
            assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
            assert "state=csrf_token_abc" in url
            assert "code_challenge=challenge_123" in url
            assert "code_challenge_method=S256" in url

    @pytest.mark.unit
    async def test_exchange_code_sends_code_verifier(self):
        """Token exchange forwards the PKCE code_verifier when present."""
        with patch("src.infrastructure.oauth.github.settings") as mock_settings:
            mock_settings.github_client_id = "github_test_id"
            mock_settings.github_client_secret = MagicMock()
            mock_settings.github_client_secret.get_secret_value.return_value = "github_secret"

            from src.infrastructure.oauth.github import GitHubOAuthProvider

            provider = GitHubOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "github_access_token"}

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": 12345,
                "login": "octocat",
                "name": "The Octocat",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345?v=4",
            }

            mock_emails_response = MagicMock()
            mock_emails_response.status_code = 200
            mock_emails_response.json.return_value = [
                {"email": "verified@example.com", "verified": True, "primary": True},
            ]

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.side_effect = [mock_user_response, mock_emails_response]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code",
                    redirect_uri="http://localhost/callback",
                    code_verifier="verifier_123",
                )

            assert result is not None
            assert result["email"] == "verified@example.com"
            assert result["email_verified"] is True
            assert result["email_trusted"] is True
            assert mock_client.post.call_args.kwargs["data"]["code_verifier"] == "verifier_123"

    @pytest.mark.unit
    async def test_exchange_code_prefers_primary_verified_email(self):
        """Primary verified email wins over secondary verified entries."""
        with patch("src.infrastructure.oauth.github.settings") as mock_settings:
            mock_settings.github_client_id = "github_test_id"
            mock_settings.github_client_secret = MagicMock()
            mock_settings.github_client_secret.get_secret_value.return_value = "github_secret"

            from src.infrastructure.oauth.github import GitHubOAuthProvider

            provider = GitHubOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "github_access_token"}

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": 1,
                "login": "octocat",
                "name": "The Octocat",
                "avatar_url": None,
            }

            mock_emails_response = MagicMock()
            mock_emails_response.status_code = 200
            mock_emails_response.json.return_value = [
                {"email": "secondary@example.com", "verified": True, "primary": False},
                {"email": "primary@example.com", "verified": True, "primary": True},
            ]

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.side_effect = [mock_user_response, mock_emails_response]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is not None
            assert result["email"] == "primary@example.com"

    @pytest.mark.unit
    async def test_exchange_code_returns_untrusted_when_verified_email_is_absent(self):
        """GitHub login must not auto-link from an unverified or missing email set."""
        with patch("src.infrastructure.oauth.github.settings") as mock_settings:
            mock_settings.github_client_id = "github_test_id"
            mock_settings.github_client_secret = MagicMock()
            mock_settings.github_client_secret.get_secret_value.return_value = "github_secret"

            from src.infrastructure.oauth.github import GitHubOAuthProvider

            provider = GitHubOAuthProvider()

            mock_token_response = MagicMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "github_access_token"}

            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = {
                "id": 1,
                "login": "octocat",
                "name": "The Octocat",
                "avatar_url": None,
            }

            mock_emails_response = MagicMock()
            mock_emails_response.status_code = 200
            mock_emails_response.json.return_value = [
                {"email": "unverified@example.com", "verified": False, "primary": True},
            ]

            mock_client = AsyncMock()
            mock_client.post.return_value = mock_token_response
            mock_client.get.side_effect = [mock_user_response, mock_emails_response]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is not None
            assert result["email"] is None
            assert result["email_verified"] is False
            assert result["email_trusted"] is False

    @pytest.mark.unit
    async def test_exchange_code_httpx_error_returns_none(self):
        """Network errors fail closed."""
        with patch("src.infrastructure.oauth.github.settings") as mock_settings:
            mock_settings.github_client_id = "github_test_id"
            mock_settings.github_client_secret = MagicMock()
            mock_settings.github_client_secret.get_secret_value.return_value = "github_secret"

            from src.infrastructure.oauth.github import GitHubOAuthProvider

            provider = GitHubOAuthProvider()

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("network error")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await provider.exchange_code(
                    code="auth_code",
                    redirect_uri="http://localhost/callback",
                )

            assert result is None
