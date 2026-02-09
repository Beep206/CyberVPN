"""Discord OAuth authentication provider."""

import logging

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
    USER_API_URL = "https://discord.com/api/users/@me"

    def __init__(self) -> None:
        self.client_id = settings.discord_client_id
        self.client_secret = settings.discord_client_secret.get_secret_value()

    def authorize_url(self, redirect_uri: str, state: str | None = None) -> str:
        """Generate Discord OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication
            state: CSRF protection state parameter (required for security)

        Returns:
            Discord auth URL
        """
        params = f"client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email"
        if state:
            params += f"&state={state}"
        return f"{self.AUTHORIZE_URL}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict | None:
        """Exchange authorization code for access token and retrieve user info.

        Args:
            code: Authorization code from Discord
            redirect_uri: Original redirect URI used in authorization

        Returns:
            Normalized user info dict if successful, None otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("Discord OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for access token
                token_response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
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
                }

        except httpx.RequestError as e:
            logger.error(f"Discord OAuth request failed: {e}")
            return None
