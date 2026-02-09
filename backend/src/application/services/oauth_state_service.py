"""OAuth state service for CSRF protection with optional PKCE (CRIT-2/HIGH-5).

Manages single-use state tokens for OAuth flows to prevent CSRF attacks.
Supports PKCE (RFC 7636) for providers that require proof-key exchange.
"""

import base64
import hashlib
import json
import logging
import secrets
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class OAuthStateService:
    """Service for managing OAuth state tokens (CSRF protection + optional PKCE).

    State tokens are:
    - Cryptographically random
    - Single-use (deleted on validation)
    - Time-limited (10-minute TTL)
    - Tied to user session or IP

    When PKCE is enabled, a code_verifier/code_challenge pair is generated
    per RFC 7636. The code_verifier is stored alongside the state in Redis
    and returned to the caller upon successful validation so it can be
    exchanged at the token endpoint.
    """

    PREFIX = "oauth_state:"
    TTL_SECONDS = 600  # 10 minutes

    # RFC 7636 Section 4.1: code_verifier is 43-128 characters
    _PKCE_VERIFIER_BYTES = 64  # secrets.token_urlsafe(64) produces ~86 chars

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        """Compute S256 code_challenge from code_verifier (RFC 7636 Section 4.2).

        code_challenge = BASE64URL(SHA256(code_verifier))  -- no padding.
        """
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    async def generate(
        self,
        provider: str,
        user_id: str | None = None,
        ip_address: str | None = None,
        pkce: bool = False,
    ) -> tuple[str, str | None]:
        """Generate a new OAuth state token, optionally with PKCE parameters.

        Args:
            provider: OAuth provider name (e.g., 'telegram', 'github')
            user_id: Optional user ID to bind the state to (for linking flows)
            ip_address: Optional IP address to bind the state to
            pkce: If True, generate PKCE code_verifier and code_challenge

        Returns:
            Tuple of (state_token, code_challenge).
            code_challenge is None when pkce=False.
        """
        state = secrets.token_urlsafe(32)
        key = f"{self.PREFIX}{state}"
        data: dict[str, str | None] = {
            "provider": provider,
            "user_id": user_id,
            "ip_address": ip_address,
            "created_at": datetime.now(UTC).isoformat(),
        }

        code_challenge: str | None = None

        if pkce:
            code_verifier = secrets.token_urlsafe(self._PKCE_VERIFIER_BYTES)
            # RFC 7636 Section 4.1: verifier MUST be 43-128 characters
            assert 43 <= len(code_verifier) <= 128, f"code_verifier length {len(code_verifier)} outside RFC 7636 range"
            code_challenge = self._generate_code_challenge(code_verifier)
            data["code_verifier"] = code_verifier

        await self._redis.setex(key, self.TTL_SECONDS, json.dumps(data))

        logger.debug(
            "OAuth state generated",
            extra={
                "provider": provider,
                "state_prefix": state[:8],
                "pkce_enabled": pkce,
            },
        )

        return state, code_challenge

    async def validate_and_consume(
        self,
        state: str,
        provider: str,
        user_id: str | None = None,
        ip_address: str | None = None,
    ) -> dict | None:
        """Validate and consume an OAuth state token.

        Args:
            state: The state token to validate
            provider: Expected provider name
            user_id: Expected user ID (if applicable)
            ip_address: Expected IP address (if applicable)

        Returns:
            The stored state data dict (including code_verifier when PKCE
            was used) on success, or None on failure.
        """
        key = f"{self.PREFIX}{state}"

        # Get and delete atomically using pipeline
        pipe = self._redis.pipeline()
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()

        data = results[0]
        if not data:
            logger.warning(
                "Invalid or expired OAuth state used",
                extra={"state_prefix": state[:8] if len(state) >= 8 else state},
            )
            return None

        state_data: dict = json.loads(data)

        # Validate provider matches
        if state_data.get("provider") != provider:
            logger.warning(
                "OAuth state provider mismatch",
                extra={
                    "expected": provider,
                    "actual": state_data.get("provider"),
                },
            )
            return None

        # Validate user_id if provided at generation
        if state_data.get("user_id") and user_id and state_data["user_id"] != user_id:
            logger.warning(
                "OAuth state user_id mismatch",
                extra={
                    "expected": state_data.get("user_id"),
                    "actual": user_id,
                },
            )
            return None

        # Note: IP validation is optional - NAT and mobile networks can change IPs
        # Only log warning if different, don't fail
        if state_data.get("ip_address") and ip_address and state_data["ip_address"] != ip_address:
            logger.warning(
                "OAuth state IP address changed during flow",
                extra={
                    "original_ip": state_data.get("ip_address"),
                    "callback_ip": ip_address,
                },
            )

        logger.info(
            "OAuth state validated and consumed",
            extra={
                "provider": provider,
                "state_prefix": state[:8],
                "has_pkce": "code_verifier" in state_data,
            },
        )

        return state_data
