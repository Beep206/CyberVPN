"""Authentication service with JWT token management (HIGH-6).

Security improvements:
- All tokens include jti (JWT ID) claim for unique identification
- Tokens can be individually revoked via revocation list
- Supports logout (single token) and logout-all (all user tokens)
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt

from src.config.settings import settings

_hasher = PasswordHasher(
    memory_cost=19456,  # 19 MiB (OWASP 2025)
    time_cost=2,
    parallelism=1,
    hash_len=32,
)


class AuthService:
    # MED-5: JWT algorithm allowlist - only these algorithms are permitted
    ALLOWED_ALGORITHMS = frozenset({"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256"})

    def __init__(self) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._access_expire = settings.access_token_expire_minutes
        self._refresh_expire = settings.refresh_token_expire_days
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience

        # MED-5: Validate configured algorithm is in allowlist
        if self._algorithm not in self.ALLOWED_ALGORITHMS:
            raise ValueError(
                f"JWT algorithm '{self._algorithm}' not in allowlist: {self.ALLOWED_ALGORITHMS}"
            )

    def create_access_token(
        self,
        subject: str,
        role: str,
        extra: dict | None = None,
        jti: str | None = None,
    ) -> tuple[str, str, datetime]:
        """Create access token with JTI claim.

        Args:
            subject: User ID
            role: User role
            extra: Additional claims
            jti: JWT ID (generated if not provided)

        Returns:
            Tuple of (token, jti, expires_at)
        """
        if jti is None:
            jti = str(uuid.uuid4())

        expire = datetime.now(UTC) + timedelta(minutes=self._access_expire)
        issued_at = datetime.now(UTC)
        payload = {
            "sub": subject,
            "role": role,
            "exp": expire,
            "iat": issued_at,
            "jti": jti,  # HIGH-6: JWT ID for revocation
            "type": "access",
        }
        if self._issuer:
            payload["iss"] = self._issuer
        if self._audience:
            payload["aud"] = self._audience
        if extra:
            payload.update(extra)

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, jti, expire

    def create_access_token_simple(
        self,
        subject: str,
        role: str,
        extra: dict | None = None,
    ) -> str:
        """Create access token (legacy compatibility - returns token string only).

        Note: Prefer create_access_token() for new code to get JTI for revocation.
        """
        token, _, _ = self.create_access_token(subject, role, extra)
        return token

    def create_refresh_token(
        self,
        subject: str,
        remember_me: bool = False,
        jti: str | None = None,
        fingerprint: str | None = None,
    ) -> tuple[str, str, datetime]:
        """Create refresh token with JTI claim and optional device fingerprint.

        Args:
            subject: User ID string.
            remember_me: If True, use 30-day TTL; otherwise, use standard 7-day TTL.
            jti: JWT ID (generated if not provided)
            fingerprint: Client device fingerprint for token binding (MED-002)

        Returns:
            Tuple of (token, jti, expires_at)
        """
        if jti is None:
            jti = str(uuid.uuid4())

        # Extended TTL for remember_me (30 days vs standard 7 days)
        expire_days = 30 if remember_me else self._refresh_expire
        expire = datetime.now(UTC) + timedelta(days=expire_days)
        issued_at = datetime.now(UTC)
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": issued_at,
            "jti": jti,  # HIGH-6: JWT ID for revocation
            "type": "refresh",
            "remember_me": remember_me,
        }
        # MED-002: Add device fingerprint for token binding
        if fingerprint:
            payload["fgp"] = fingerprint
        if self._issuer:
            payload["iss"] = self._issuer
        if self._audience:
            payload["aud"] = self._audience

        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, jti, expire

    def create_refresh_token_simple(
        self,
        subject: str,
        remember_me: bool = False,
        fingerprint: str | None = None,
    ) -> str:
        """Create refresh token (legacy compatibility - returns token string only).

        Note: Prefer create_refresh_token() for new code to get JTI for revocation.
        """
        token, _, _ = self.create_refresh_token(subject, remember_me, fingerprint=fingerprint)
        return token

    def decode_token(self, token: str) -> dict:
        """Decode and validate a JWT token.

        Note: This does NOT check the revocation list. Use validate_token()
        from the dependency layer for full validation including revocation check.
        """
        options = {"require": ["exp", "sub"]}
        if not self._audience:
            options["verify_aud"] = False

        decode_kwargs: dict[str, object] = {
            "algorithms": [self._algorithm],
            "options": options,
        }
        if self._audience:
            decode_kwargs["audience"] = self._audience
        if self._issuer:
            decode_kwargs["issuer"] = self._issuer

        return jwt.decode(token, self._secret, **decode_kwargs)

    def get_token_jti(self, token: str) -> str | None:
        """Extract JTI from a token without full validation.

        Args:
            token: The JWT token

        Returns:
            JTI string or None if not present
        """
        try:
            # Decode without verification to get claims
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            return payload.get("jti")
        except jwt.PyJWTError:
            return None

    def get_token_expiry(self, token: str) -> datetime | None:
        """Extract expiry from a token without full validation.

        Args:
            token: The JWT token

        Returns:
            Expiry datetime or None if not present
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            exp = payload.get("exp")
            if exp:
                return datetime.fromtimestamp(exp, tz=UTC)
            return None
        except jwt.PyJWTError:
            return None

    def get_token_fingerprint(self, token: str) -> str | None:
        """Extract device fingerprint from a token without full validation (MED-002).

        Args:
            token: The JWT token

        Returns:
            Fingerprint string or None if not present
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
            return payload.get("fgp")
        except jwt.PyJWTError:
            return None

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against Argon2id hash (sync version).

        For async code, use verify_password_async().
        """
        try:
            _hasher.verify(hashed_password, plain_password)
            return True
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    @staticmethod
    async def hash_password(password: str) -> str:
        """Hash password with Argon2id asynchronously.

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the CPU/memory-intensive Argon2id hashing operation.
        """
        return await asyncio.to_thread(_hasher.hash, password)

    @staticmethod
    async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
        """Verify password against Argon2id hash asynchronously.

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the CPU/memory-intensive Argon2id verification operation.
        """
        try:
            return await asyncio.to_thread(_hasher.verify, hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
