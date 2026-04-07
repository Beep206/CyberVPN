"""Helpers for storing refresh-token-backed sessions."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.refresh_token_model import RefreshToken


async def store_refresh_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    refresh_token: str,
    expires_at: datetime,
    device_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a refresh token so rotation/revocation and session metrics work."""
    session.add(
        RefreshToken(
            user_id=user_id,
            token_hash=sha256(refresh_token.encode()).hexdigest(),
            expires_at=expires_at,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    await session.flush()
