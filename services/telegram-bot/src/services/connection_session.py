"""Short-lived Telegram connection callback sessions."""

from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING

from pydantic import ValidationError

from src.models.connection import ConnectionSession

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models.connection import ConnectionPlatform
    from src.services.cache_service import CacheService

CONNECTION_SESSION_TTL_SECONDS = 20 * 60
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,24}$")


def is_valid_connection_session_id(value: str) -> bool:
    """Return whether a callback session id is safe to use in a cache key."""
    return bool(_SESSION_ID_PATTERN.fullmatch(value))


class ConnectionSessionStore:
    """Persist safe callback session metadata in Redis."""

    def __init__(
        self,
        cache: CacheService,
        *,
        id_factory: Callable[[], str] | None = None,
        ttl_seconds: int = CONNECTION_SESSION_TTL_SECONDS,
    ) -> None:
        self._cache = cache
        self._id_factory = id_factory or (lambda: secrets.token_urlsafe(9))
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _key(session_id: str) -> str:
        return f"connection-session:{session_id}"

    async def create(
        self,
        *,
        telegram_id: int,
        platform_hint: ConnectionPlatform = "unknown",
        flow_key: str | None = None,
        version: int | None = None,
        backend_connection_session_id: str | None = None,
    ) -> ConnectionSession:
        """Create a session containing only non-sensitive routing metadata."""
        session_id = self._id_factory()
        if not is_valid_connection_session_id(session_id):
            msg = "generated connection session id is invalid"
            raise ValueError(msg)

        session = ConnectionSession(
            session_id=session_id,
            telegram_id=telegram_id,
            platform_hint=platform_hint,
            flow_key=flow_key,
            version=version,
            backend_connection_session_id=backend_connection_session_id,
        )
        await self._cache.set_json(
            self._key(session_id),
            session.model_dump(mode="json"),
            ttl=self._ttl_seconds,
        )
        return session

    async def get(self, session_id: str) -> ConnectionSession | None:
        """Load and validate a connection session."""
        if not is_valid_connection_session_id(session_id):
            return None

        data = await self._cache.get_json(self._key(session_id))
        if not isinstance(data, dict):
            return None

        try:
            return ConnectionSession.model_validate(data)
        except ValidationError:
            return None
