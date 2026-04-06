"""Google OAuth authentication provider (CRIT-2)."""

import asyncio
import logging
from urllib.parse import urlencode

import httpx

from src.config.settings import settings
from src.infrastructure.oauth.errors import OAuthProviderUnavailableError
from src.infrastructure.oauth.oidc import AsyncOIDCTokenVerifier

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
    DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    ALLOWED_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
    REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
    MAX_REQUEST_ATTEMPTS = 2
    RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
    RETRYABLE_TOKEN_ERRORS = frozenset({"temporarily_unavailable", "server_error"})

    def __init__(self) -> None:
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret.get_secret_value()

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str = "S256",
        nonce: str | None = None,
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
        if nonce:
            params["nonce"] = nonce

        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def _verify_id_token(self, id_token: str, nonce: str | None = None) -> dict | None:
        return await AsyncOIDCTokenVerifier.verify_id_token(
            id_token=id_token,
            audience=self.client_id,
            discovery_url=self.DISCOVERY_URL,
            nonce=nonce,
            issuer_validator=lambda claims, _discovery: claims.get("iss") in self.ALLOWED_ISSUERS,
        )

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

        last_error: httpx.RequestError | None = None

        def _raise_google_unavailable(reason: str, *, extra: dict | None = None) -> None:
            logger.warning("Google OAuth provider temporarily unavailable", extra=extra or {"reason": reason})
            raise OAuthProviderUnavailableError("Google OAuth provider is temporarily unavailable")

        for attempt in range(1, self.MAX_REQUEST_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
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
                        if token_response.status_code in self.RETRYABLE_HTTP_STATUSES:
                            _raise_google_unavailable(
                                "retryable_token_http_status",
                                extra={"status": token_response.status_code, "attempt": attempt},
                            )

                        error_payload = None
                        try:
                            error_payload = token_response.json()
                        except ValueError:
                            error_payload = None

                        logger.warning(
                            "Google token exchange failed",
                            extra={
                                "status": token_response.status_code,
                                "error": error_payload.get("error") if isinstance(error_payload, dict) else None,
                                "description": (
                                    error_payload.get("error_description")
                                    if isinstance(error_payload, dict)
                                    else None
                                ),
                                "attempt": attempt,
                            },
                        )
                        return None

                    token_data = token_response.json()

                    # Check for error response
                    if "error" in token_data:
                        if token_data.get("error") in self.RETRYABLE_TOKEN_ERRORS:
                            _raise_google_unavailable(
                                "retryable_token_error",
                                extra={
                                    "error": token_data.get("error"),
                                    "description": token_data.get("error_description"),
                                    "attempt": attempt,
                                },
                            )

                        logger.warning(
                            "Google token exchange error",
                            extra={
                                "error": token_data.get("error"),
                                "description": token_data.get("error_description"),
                            },
                        )
                        return None

                    access_token = token_data.get("access_token")
                    id_token = token_data.get("id_token")
                    if not access_token or not id_token:
                        logger.warning("Google response missing access_token or id_token")
                        return None

                    claims = await self._verify_id_token(id_token)
                    if not claims:
                        logger.warning("Google ID token validation failed")
                        return None

                    refresh_token = token_data.get("refresh_token")
                    email = claims.get("email")
                    email_verified = bool(claims.get("email_verified"))

                    return {
                        "id": str(claims.get("sub")),
                        "email": email,
                        "username": email,
                        "name": claims.get("name"),
                        "avatar_url": claims.get("picture"),
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "email_verified": email_verified,
                        "email_trusted": bool(email and email_verified),
                    }

            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    "Google OAuth request attempt failed",
                    extra={
                        "attempt": attempt,
                        "max_attempts": self.MAX_REQUEST_ATTEMPTS,
                        "error_type": type(e).__name__,
                        "error": repr(str(e)),
                    },
                )
                if attempt < self.MAX_REQUEST_ATTEMPTS:
                    await asyncio.sleep(0.4)
            except OAuthProviderUnavailableError:
                raise

        raise OAuthProviderUnavailableError("Google OAuth provider is temporarily unavailable") from last_error
