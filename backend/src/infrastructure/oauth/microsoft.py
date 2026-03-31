"""Microsoft OAuth authentication provider."""

import logging
from urllib.parse import urlencode

import httpx

from src.config.settings import settings
from src.infrastructure.oauth.oidc import AsyncOIDCTokenVerifier

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
        self.discovery_url = f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
        self.user_api_url = "https://graph.microsoft.com/v1.0/me"

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
        nonce: str | None = None,
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
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "response_mode": "query",
        }
        if state:
            params["state"] = state
        if code_challenge:
            params["code_challenge"] = code_challenge
        if code_challenge_method:
            params["code_challenge_method"] = code_challenge_method
        if nonce:
            params["nonce"] = nonce
        return f"{self.authorize_url_base}?{urlencode(params)}"

    async def _verify_id_token(self, id_token: str, nonce: str | None = None) -> dict | None:
        def _issuer_validator(claims: dict, discovery: dict) -> bool:
            issuer = claims.get("iss")
            discovery_issuer = discovery.get("issuer")
            if not isinstance(issuer, str) or not isinstance(discovery_issuer, str):
                return False

            tenant_id = claims.get("tid")
            if "{tenantid}" in discovery_issuer and isinstance(tenant_id, str):
                return issuer == discovery_issuer.replace("{tenantid}", tenant_id)

            return issuer == discovery_issuer

        return await AsyncOIDCTokenVerifier.verify_id_token(
            id_token=id_token,
            audience=self.client_id,
            discovery_url=self.discovery_url,
            nonce=nonce,
            issuer_validator=_issuer_validator,
        )

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
                id_token = token_data.get("id_token")
                if not access_token or not id_token:
                    logger.warning("Microsoft response missing access_token or id_token")
                    return None

                claims = await self._verify_id_token(id_token)
                if not claims:
                    logger.warning("Microsoft ID token validation failed")
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
                email_candidates = (
                    claims.get("email"),
                    claims.get("preferred_username"),
                    user_data.get("mail"),
                    user_data.get("userPrincipalName"),
                )
                email = next(
                    (
                        candidate
                        for candidate in email_candidates
                        if isinstance(candidate, str) and "@" in candidate
                    ),
                    None,
                )

                return {
                    "id": str(user_data.get("id") or claims.get("sub") or claims.get("oid")),
                    "email": email,
                    "username": claims.get("preferred_username") or email,
                    "name": user_data.get("displayName") or claims.get("name"),
                    "avatar_url": None,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "email_verified": bool(email),
                    "email_trusted": bool(email),
                }

        except httpx.RequestError as e:
            logger.error(
                "Microsoft OAuth request failed",
                extra={"error": str(e)},
            )
            return None
