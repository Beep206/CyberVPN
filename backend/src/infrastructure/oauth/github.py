"""GitHub OAuth authentication provider (CRIT-2)."""

import logging
from urllib.parse import urlencode

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

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
    ) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication
            state: CSRF protection state parameter (required for security)

        Returns:
            GitHub auth URL
        """
        params: dict[str, str] = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
        }
        if state:
            params["state"] = state
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> dict | None:
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
                        **({"code_verifier": code_verifier} if code_verifier else {}),
                    },
                    headers={
                        "Accept": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
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
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "GitHub user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()

                email = None
                try:
                    emails_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json",
                            "X-GitHub-Api-Version": "2022-11-28",
                        },
                    )

                    if emails_response.status_code == 200:
                        emails = emails_response.json()
                        verified_primary = next(
                            (
                                item.get("email")
                                for item in emails
                                if item.get("primary") and item.get("verified")
                            ),
                            None,
                        )
                        email = verified_primary or next(
                            (item.get("email") for item in emails if item.get("verified")),
                            None,
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch GitHub emails: {e}")

                return {
                    "id": str(user_data.get("id")),  # Convert to string for consistency
                    "username": user_data.get("login"),
                    "email": email,
                    "name": user_data.get("name"),
                    "avatar_url": user_data.get("avatar_url"),
                    "access_token": access_token,
                    "email_verified": bool(email),
                    "email_trusted": bool(email),
                }

        except httpx.RequestError as e:
            logger.error(f"GitHub OAuth request failed: {e}")
            return None
