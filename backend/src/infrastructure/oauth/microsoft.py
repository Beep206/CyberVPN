"""Microsoft OAuth authentication provider."""

import logging

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = "openid email profile User.Read"


class MicrosoftOAuthProvider:
    """Microsoft OAuth authentication provider.

    Implements the OAuth 2.0 authorization code flow with PKCE support:
    1. Redirect user to Microsoft for authorization
    2. Exchange authorization code for access token
    3. Fetch user info from Microsoft Graph API
    """

    def __init__(self) -> None:
        self.client_id = settings.microsoft_client_id
        self.client_secret = settings.microsoft_client_secret.get_secret_value()
        tenant = settings.microsoft_tenant_id or "common"
        self.authorize_url_base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        self.user_api_url = "https://graph.microsoft.com/v1.0/me"

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate Microsoft OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication.
            state: CSRF protection state parameter.
            code_challenge: PKCE code challenge value.
            code_challenge_method: PKCE challenge method (e.g. S256).

        Returns:
            Microsoft auth URL.
        """
        params = (
            f"client_id={self.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={SCOPES}"
            f"&response_mode=query"
        )
        if state:
            params += f"&state={state}"
        if code_challenge:
            params += f"&code_challenge={code_challenge}"
        if code_challenge_method:
            params += f"&code_challenge_method={code_challenge_method}"
        return f"{self.authorize_url_base}?{params}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ) -> dict | None:
        """Exchange authorization code for access token and retrieve user info.

        Args:
            code: Authorization code from Microsoft.
            redirect_uri: Original redirect URI used in authorization.
            code_verifier: PKCE code verifier value.

        Returns:
            User info dict if successful, None otherwise.
        """
        if not self.client_id or not self.client_secret:
            logger.error("Microsoft OAuth client credentials not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for access token
                token_payload: dict[str, str] = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "scope": SCOPES,
                }
                if code_verifier:
                    token_payload["code_verifier"] = code_verifier

                token_response = await client.post(
                    self.token_url,
                    data=token_payload,
                    headers={"Accept": "application/json"},
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Microsoft token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()

                # Check for error response
                if "error" in token_data:
                    logger.warning(
                        "Microsoft token exchange error",
                        extra={
                            "error": token_data.get("error"),
                            "description": token_data.get("error_description"),
                        },
                    )
                    return None

                access_token = token_data.get("access_token")
                if not access_token:
                    logger.warning("Microsoft response missing access_token")
                    return None

                refresh_token = token_data.get("refresh_token")

                # Get user information from Microsoft Graph
                user_response = await client.get(
                    self.user_api_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )

                if user_response.status_code != 200:
                    logger.warning(
                        "Microsoft user info fetch failed",
                        extra={"status": user_response.status_code},
                    )
                    return None

                user_data = user_response.json()

                # MS Graph returns mail for work accounts and
                # userPrincipalName as fallback for personal accounts
                email = user_data.get("mail") or user_data.get("userPrincipalName")

                return {
                    "id": str(user_data.get("id")),
                    "email": email,
                    "username": email,
                    "name": user_data.get("displayName"),
                    "avatar_url": None,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }

        except httpx.RequestError as e:
            logger.error(
                "Microsoft OAuth request failed",
                extra={"error": str(e)},
            )
            return None
