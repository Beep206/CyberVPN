"""Discord OAuth authentication provider."""

import logging
from urllib.parse import urlencode

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DiscordOAuthProvider:
    """Discord OAuth authentication provider.

    Implements the OAuth 2.0 authorization code flow:
    1. Redirect user to Discord for authorization
    2. Exchange authorization code for access token
    3. Fetch user info from Discord API
    """

    AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    USER_API_URL = "https://discord.com/api/v10/users/@me"

    def __init__(self) -> None:
        self.client_id = settings.discord_client_id
        self.client_secret = settings.discord_client_secret.get_secret_value()

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate Discord OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication
            state: CSRF protection state parameter (required for security)
            code_challenge: PKCE challenge (required for security)
            code_challenge_method: PKCE challenge method (e.g. S256)

        Returns:
            Discord auth URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify email",
        }
        if state:
            params["state"] = state
        if code_challenge and code_challenge_method:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: str | None = None
    ) -> dict | None:
        """Exchange authorization code for access token and retrieve user info.

        Args:
            code: Authorization code from Discord
            redirect_uri: Original redirect URI used in authorization
            code_verifier: PKCE verifier (required for security matching challenge)

        Returns:
            Normalized user info dict if successful, None otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("Discord OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for access token
                data = {
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                }
                if code_verifier:
                    data["code_verifier"] = code_verifier

                token_response = await client.post(
                    self.TOKEN_URL,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Discord token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()

                # Check for error response
                if "error" in token_data:
                    logger.warning(
                        "Discord token exchange error",
                        extra={
                            "error": token_data.get("error"),
                            "description": token_data.get("error_description"),
                        },
                    )
                    return None

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.warning("Discord response missing access_token")
                    return None

                refresh_token = token_data.get("refresh_token")

                # Get user information
                user_response = await client.get(
                    self.USER_API_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "Discord user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()

                # CRIT: Verify email is verified in Discord to prevent Account Takeover
                if not user_data.get("verified"):
                    logger.warning(
                        "Discord user has unverified email, login rejected.",
                        extra={"user_id": user_data.get("id")},
                    )
                    return None

                # Build avatar URL
                avatar_url = None
                avatar_hash = user_data.get("avatar")
                user_id = user_data.get("id")
                if avatar_hash and user_id:
                    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"

                username = user_data.get("username", "")
                global_name = user_data.get("global_name")

                return {
                    "id": str(user_data.get("id")),
                    "email": user_data.get("email"),
                    "username": f"{username}",
                    "name": global_name or username,
                    "avatar_url": avatar_url,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "email_verified": True,
                    "email_trusted": True,
                }

        except httpx.RequestError as e:
            logger.error(f"Discord OAuth request failed: {e}")
            return None
