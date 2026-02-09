"""Apple Sign In OAuth authentication provider."""

import logging
import time

import httpx
import jwt

from src.config.settings import settings

logger = logging.getLogger(__name__)


class AppleOAuthProvider:
    """Apple Sign In authentication provider.

    Implements the OAuth 2.0 authorization code flow for Apple:
    1. Redirect user to Apple for authorization
    2. Exchange authorization code for tokens (form_post callback)
    3. Decode id_token JWT to extract user identity

    Apple specifics:
    - Uses a JWT client secret signed with ES256 (team private key)
    - User name is only sent on the first authorization (via `user` POST field)
    - id_token is an RS256 JWT validated against Apple JWKS
    """

    AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"
    JWKS_URL = "https://appleid.apple.com/auth/keys"

    def __init__(self) -> None:
        self.client_id = settings.apple_client_id
        self.team_id = settings.apple_team_id
        self.key_id = settings.apple_key_id
        self.private_key = settings.apple_private_key.get_secret_value()

    def _generate_client_secret(self) -> str:
        """Generate a JWT client secret signed with the Apple private key.

        Apple requires the client_secret to be a JWT signed with ES256
        using the team's private key. Maximum validity is 6 months.

        Returns:
            Encoded JWT string to use as client_secret.
        """
        now = int(time.time())
        payload = {
            "iss": self.team_id,
            "iat": now,
            "exp": now + 86400 * 180,  # 6 months max
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }
        return jwt.encode(
            payload,
            self.private_key,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )

    def authorize_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate Apple Sign In authorization URL.

        Args:
            redirect_uri: URL to redirect after authentication.
            state: CSRF protection state parameter (required for security).
            code_challenge: PKCE code challenge value.
            code_challenge_method: PKCE method, typically 'S256'.

        Returns:
            Apple auth URL.
        """
        params = (
            f"client_id={self.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=name email"
            f"&response_mode=form_post"
        )
        if state:
            params += f"&state={state}"
        if code_challenge:
            params += f"&code_challenge={code_challenge}"
        if code_challenge_method:
            params += f"&code_challenge_method={code_challenge_method}"
        return f"{self.AUTHORIZE_URL}?{params}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
        user_name: str | None = None,
    ) -> dict | None:
        """Exchange authorization code for tokens and extract user identity.

        Apple returns an id_token JWT containing the user's sub (unique ID)
        and email. The user's name is only provided on the first
        authorization via a separate `user` JSON field in the POST callback
        body -- pass it here as ``user_name``.

        Args:
            code: Authorization code from Apple callback.
            redirect_uri: Original redirect URI used in authorization.
            code_verifier: PKCE code verifier (if PKCE was used).
            user_name: Full name from Apple's initial callback (first auth only).

        Returns:
            User info dict if successful, None otherwise.
        """
        if not self.private_key:
            logger.error("Apple Sign In private key not configured")
            return None

        if not self.client_id or not self.team_id or not self.key_id:
            logger.error("Apple Sign In credentials not fully configured")
            return None

        try:
            client_secret = self._generate_client_secret()

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Exchange code for tokens
                token_payload: dict[str, str] = {
                    "client_id": self.client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                }
                if code_verifier:
                    token_payload["code_verifier"] = code_verifier

                token_response = await client.post(
                    self.TOKEN_URL,
                    data=token_payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if token_response.status_code != 200:
                    logger.warning(
                        "Apple token exchange failed",
                        extra={"status": token_response.status_code},
                    )
                    return None

                token_data = token_response.json()

                if "error" in token_data:
                    logger.warning(
                        "Apple token exchange error",
                        extra={
                            "error": token_data.get("error"),
                            "description": token_data.get("error_description"),
                        },
                    )
                    return None

                id_token = token_data.get("id_token")
                if not id_token:
                    logger.warning("Apple response missing id_token")
                    return None

                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")

                # Fetch Apple JWKS for id_token validation
                jwks_response = await client.get(self.JWKS_URL)
                if jwks_response.status_code != 200:
                    logger.warning(
                        "Apple JWKS fetch failed",
                        extra={"status": jwks_response.status_code},
                    )
                    return None

                jwks = jwks_response.json()

                # Decode and validate the id_token
                # Build a PyJWKSet from the fetched keys
                jwk_set = jwt.PyJWKSet.from_dict(jwks)

                # Get the unverified header to find the correct key
                unverified_header = jwt.get_unverified_header(id_token)
                kid = unverified_header.get("kid")

                signing_key_obj = None
                for key in jwk_set.keys:
                    if key.key_id == kid:
                        signing_key_obj = key
                        break

                if signing_key_obj is None:
                    logger.warning(
                        "Apple id_token signing key not found in JWKS",
                        extra={"kid": kid},
                    )
                    return None

                claims = jwt.decode(
                    id_token,
                    signing_key_obj.key,
                    algorithms=["RS256"],
                    audience=self.client_id,
                )

                sub = claims.get("sub")
                email = claims.get("email")

                if not sub:
                    logger.warning("Apple id_token missing 'sub' claim")
                    return None

                name = user_name or email or sub

                return {
                    "id": sub,
                    "email": email,
                    "username": email,
                    "name": name,
                    "avatar_url": None,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }

        except jwt.PyJWTError as e:
            logger.error(
                "Apple id_token validation failed",
                extra={"error": str(e)},
            )
            return None
        except httpx.RequestError as e:
            logger.error(
                "Apple OAuth request failed",
                extra={"error": str(e)},
            )
            return None
