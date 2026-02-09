"""Google OAuth authentication provider (CRIT-2)."""

import logging
from urllib.parse import urlencode

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class GoogleOAuthProvider:
    """Google OAuth 2.0 authentication provider.

    Implements the OAuth 2.0 authorization code flow with optional PKCE:
    1. Redirect user to Google for authorization
    2. Exchange authorization code for access/refresh tokens
    3. Fetch user info from Google userinfo API
    """

    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_API_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def __init__(self) -> None:
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret.get_secret_value()

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
    ) -> str:
        """Generate Google OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication.
            state: CSRF protection state parameter (required for security).
            code_challenge: PKCE code challenge for public clients.
            code_challenge_method: PKCE method, defaults to S256.

        Returns:
            Google authorization URL.
        """
        params: dict[str, str] = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method

        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict | None:
        """Exchange authorization code for tokens and retrieve user info.

        Args:
            code: Authorization code from Google.
            redirect_uri: Original redirect URI used in authorization.
            code_verifier: PKCE code verifier matching the code_challenge.

        Returns:
            Normalized user info dict if successful, None otherwise.
        """
        if not self.client_id or not self.client_secret:
            logger.error("Google OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for tokens
                token_payload: dict[str, str] = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
                if code_verifier:
                    token_payload["code_verifier"] = code_verifier

                token_response = await client.post(
                    self.TOKEN_URL,
                    data=token_payload,
                    headers={"Accept": "application/json"},
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Google token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()

                # Check for error response
                if "error" in token_data:
                    logger.warning(
                        "Google token exchange error",
                        extra={
                            "error": token_data.get("error"),
                            "description": token_data.get("error_description"),
                        },
                    )
                    return None

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.warning("Google response missing access_token")
                    return None

                refresh_token = token_data.get("refresh_token")

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
                        "Google user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()

                return {
                    "id": str(user_data.get("sub")),
                    "email": user_data.get("email"),
                    "username": user_data.get("email"),
                    "name": user_data.get("name"),
                    "avatar_url": user_data.get("picture"),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }

        except httpx.RequestError as e:
            logger.error(f"Google OAuth request failed: {e}")
            return None
