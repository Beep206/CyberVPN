"""GitHub OAuth authentication provider (CRIT-2)."""

import logging

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class GitHubOAuthProvider:
    """GitHub OAuth authentication provider.

    Implements the OAuth 2.0 authorization code flow:
    1. Redirect user to GitHub for authorization
    2. Exchange authorization code for access token
    3. Fetch user info from GitHub API
    """

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"

    def __init__(self) -> None:
        self.client_id = settings.github_client_id
        self.client_secret = settings.github_client_secret.get_secret_value()

    def authorize_url(self, redirect_uri: str, state: str | None = None) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication
            state: CSRF protection state parameter (required for security)

        Returns:
            GitHub auth URL
        """
        params = f"client_id={self.client_id}&redirect_uri={redirect_uri}&scope=read:user user:email"
        if state:
            params += f"&state={state}"
        return f"{self.AUTHORIZE_URL}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict | None:
        """Exchange authorization code for access token and retrieve user info.

        Args:
            code: Authorization code from GitHub
            redirect_uri: Original redirect URI used in authorization

        Returns:
            User info dict if successful, None otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("GitHub OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for access token
                token_response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "GitHub token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()

                # Check for error response
                if "error" in token_data:
                    logger.warning(
                        "GitHub token exchange error",
                        extra={
                            "error": token_data.get("error"),
                            "description": token_data.get("error_description"),
                        },
                    )
                    return None

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.warning("GitHub response missing access_token")
                    return None

                # Get user information
                user_response = await client.get(
                    self.USER_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "GitHub user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()

                return {
                    "id": str(user_data.get("id")),  # Convert to string for consistency
                    "username": user_data.get("login"),
                    "email": user_data.get("email"),
                    "name": user_data.get("name"),
                    "avatar_url": user_data.get("avatar_url"),
                    "access_token": access_token,
                }

        except httpx.RequestError as e:
            logger.error(f"GitHub OAuth request failed: {e}")
            return None
