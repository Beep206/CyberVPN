import asyncio
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
    def __init__(self) -> None:
        self._secret = settings.jwt_secret.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._access_expire = settings.access_token_expire_minutes
        self._refresh_expire = settings.refresh_token_expire_days

    def create_access_token(self, subject: str, role: str, extra: dict | None = None) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=self._access_expire)
        payload = {
            "sub": subject,
            "role": role,
            "exp": expire,
            "type": "access",
        }
        if extra:
            payload.update(extra)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, subject: str) -> str:
        expire = datetime.now(UTC) + timedelta(days=self._refresh_expire)
        payload = {
            "sub": subject,
            "exp": expire,
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])

    @staticmethod
    async def hash_password(password: str) -> str:
        """Hash password with Argon2id asynchronously.

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the CPU/memory-intensive Argon2id hashing operation.
        """
        return await asyncio.to_thread(_hasher.hash, password)

    @staticmethod
    async def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against Argon2id hash asynchronously.

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the CPU/memory-intensive Argon2id verification operation.
        """
        try:
            return await asyncio.to_thread(_hasher.verify, hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
