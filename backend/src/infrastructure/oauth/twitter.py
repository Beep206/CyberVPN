"""X (Twitter) OAuth 2.0 authentication provider (CRIT-2)."""

import base64
import logging

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TwitterOAuthProvider:
    """X (Twitter) OAuth 2.0 authentication provider.

    Implements the OAuth 2.0 authorization code flow with PKCE:
    1. Redirect user to Twitter for authorization (with PKCE challenge)
    2. Exchange authorization code for access token (with PKCE verifier)
    3. Fetch user info from Twitter API v2
    """

    AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    USER_API_URL = "https://api.twitter.com/2/users/me"

    def __init__(self) -> None:
        self.client_id = settings.twitter_client_id
        self.client_secret = settings.twitter_client_secret.get_secret_value()

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate Twitter OAuth 2.0 authorization URL.

        PKCE is required for Twitter OAuth 2.0. The caller must generate
        a code_verifier, derive the code_challenge (S256), and pass both
        the challenge here and the verifier to exchange_code later.

        Args:
            redirect_uri: URL to redirect after authentication
            state: CSRF protection state parameter (required for security)
            code_challenge: PKCE code challenge derived from code_verifier
            code_challenge_method: PKCE method, must be "S256" for Twitter

        Returns:
            Twitter auth URL
        """
        params = (
            f"client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code&scope=users.read tweet.read"
        )
        if state:
            params += f"&state={state}"
        if code_challenge:
            params += f"&code_challenge={code_challenge}"
            params += f"&code_challenge_method={code_challenge_method or 'S256'}"
        return f"{self.AUTHORIZE_URL}?{params}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict | None:
        """Exchange authorization code for access token and retrieve user info.

        Twitter requires HTTP Basic Auth (client_id:client_secret) for the
        token exchange and PKCE code_verifier for proof of possession.

        Args:
            code: Authorization code from Twitter
            redirect_uri: Original redirect URI used in authorization
            code_verifier: PKCE code verifier (required for Twitter)

        Returns:
            User info dict if successful, None otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("Twitter OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Twitter requires HTTP Basic Auth for token exchange
                credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

                # Build form data for token exchange
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                }
                if code_verifier:
                    token_data["code_verifier"] = code_verifier

                token_response = await client.post(
                    self.TOKEN_URL,
                    data=token_data,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Twitter token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_result = token_response.json()

                # Check for error response
                if "error" in token_result:
                    logger.warning(
                        "Twitter token exchange error",
                        extra={
                            "error": token_result.get("error"),
                            "description": token_result.get("error_description"),
                        },
                    )
                    return None

                access_token = token_result.get("access_token")
                if not access_token:
                    logger.warning("Twitter response missing access_token")
                    return None

                # Fetch user information from Twitter API v2
                user_response = await client.get(
                    f"{self.USER_API_URL}?user.fields=profile_image_url,name,username",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "Twitter user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_result = user_response.json()
                data = user_result.get("data", {})

                return {
                    "id": str(data.get("id")),
                    "email": None,  # Not available in basic scope
                    "username": data.get("username"),
                    "name": data.get("name"),
                    "avatar_url": data.get("profile_image_url"),
                    "access_token": access_token,
                    "refresh_token": None,
                }

        except httpx.RequestError as e:
            logger.error(f"Twitter OAuth request failed: {e}")
            return None
