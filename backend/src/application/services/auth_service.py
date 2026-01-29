import asyncio
from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from src.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


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
        """Hash password asynchronously (bcrypt is CPU-intensive).

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the expensive bcrypt hashing operation.

        Args:
            password: Plain text password to hash.

        Returns:
            Hashed password string.
        """
        return await asyncio.to_thread(pwd_context.hash, password)

    @staticmethod
    async def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password asynchronously (bcrypt is CPU-intensive).

        Uses asyncio.to_thread() to avoid blocking the event loop during
        the expensive bcrypt verification operation.

        Args:
            plain_password: Plain text password to verify.
            hashed_password: Previously hashed password to compare against.

        Returns:
            True if password matches, False otherwise.
        """
        return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)
