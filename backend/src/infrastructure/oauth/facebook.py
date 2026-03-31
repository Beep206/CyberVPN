"""Facebook OAuth authentication provider."""

import logging
from urllib.parse import urlencode

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class FacebookOAuthProvider:
    """Facebook OAuth 2.0 authentication provider."""

    AUTHORIZE_URL = "https://www.facebook.com/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/oauth/access_token"
    USER_API_URL = "https://graph.facebook.com/me"

    def __init__(self) -> None:
        self.client_id = settings.facebook_client_id
        self.client_secret = settings.facebook_client_secret.get_secret_value()

    def authorize_url(self, redirect_uri: str, state: str | None = None) -> str:
        """Generate Facebook OAuth authorization URL."""
        params: dict[str, str] = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email,public_profile",
        }
        if state:
            params["state"] = state

        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> dict | None:
        """Exchange authorization code for tokens and retrieve user info."""
        if not self.client_id or not self.client_secret:
            logger.error("Facebook OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_response = await client.get(
                    self.TOKEN_URL,
                    params={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Facebook token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()
                if "error" in token_data:
                    logger.warning(
                        "Facebook token exchange error",
                        extra={"error": token_data.get("error")},
                    )
                    return None

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.warning("Facebook response missing access_token")
                    return None

                user_response = await client.get(
                    self.USER_API_URL,
                    params={
                        "fields": "id,name,email,short_name,picture.type(large)",
                        "access_token": access_token,
                    },
                    headers={"Accept": "application/json"},
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "Facebook user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()
                picture = user_data.get("picture")
                picture_data = picture.get("data", {}) if isinstance(picture, dict) else {}
                avatar_url = picture_data.get("url")

                email = user_data.get("email")
                short_name = user_data.get("short_name")
                name = user_data.get("name") or short_name or email or user_data.get("id")

                return {
                    "id": str(user_data.get("id")),
                    "email": email,
                    "username": short_name or email,
                    "name": name,
                    "avatar_url": avatar_url,
                    "access_token": access_token,
                    "refresh_token": None,
                    "email_verified": False,
                    "email_trusted": False,
                }

        except httpx.RequestError as e:
            logger.error("Facebook OAuth request failed: %s", e)
            return None
