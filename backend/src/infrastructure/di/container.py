"""Central dependency injection container.

Provides a single registry for all injectable dependencies.
Override via container.override() for testing.
"""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.infrastructure.database.session import AsyncSessionLocal


class Container:
    """Lightweight DI container mapping dependency keys to factory functions."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., Any]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._factories["db"] = self._default_db
        self._factories["redis"] = self._default_redis
        self._factories["auth_service"] = self._default_auth_service
        self._factories["remnawave_client"] = self._default_remnawave_client
        self._factories["cryptobot_client"] = self._default_cryptobot_client

    # -- Default factories ------------------------------------------------

    @staticmethod
    async def _default_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @staticmethod
    async def _default_redis() -> AsyncGenerator[redis.Redis, None]:
        from src.infrastructure.cache.redis_client import get_redis

        async for client in get_redis():
            yield client

    @staticmethod
    def _default_auth_service() -> AuthService:
        return AuthService()

    @staticmethod
    def _default_remnawave_client():  # type: ignore[no-untyped-def]
        from src.infrastructure.remnawave.client import remnawave_client

        return remnawave_client

    @staticmethod
    def _default_cryptobot_client():  # type: ignore[no-untyped-def]
        from src.infrastructure.payments.cryptobot.client import cryptobot_client

        return cryptobot_client

    # -- Public API -------------------------------------------------------

    def get(self, key: str) -> Callable[..., Any]:
        """Return the factory function for the given key."""
        return self._factories[key]

    def override(self, key: str, factory: Callable[..., Any]) -> None:
        """Replace a factory (useful in tests)."""
        self._factories[key] = factory

    def reset(self, key: str | None = None) -> None:
        """Reset one or all factories to defaults."""
        if key is None:
            self._register_defaults()
        else:
            default_method = getattr(self, f"_default_{key}", None)
            if default_method:
                self._factories[key] = default_method


# Module-level singleton
container = Container()
