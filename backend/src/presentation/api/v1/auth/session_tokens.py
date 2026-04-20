"""Helpers for storing refresh-token-backed sessions."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
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
    auth_realm_id: UUID | None = None,
    principal_class: str | None = None,
    principal_subject: str | None = None,
    audience: str | None = None,
    scope_family: str | None = None,
    access_token_jti: str | None = None,
) -> None:
    """Persist a refresh token so rotation/revocation and session metrics work."""
    refresh_token_record = RefreshToken(
        user_id=user_id,
        token_hash=sha256(refresh_token.encode()).hexdigest(),
        expires_at=expires_at,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(refresh_token_record)
    await session.flush()

    if auth_realm_id and principal_class and principal_subject and audience and scope_family:
        session.add(
            PrincipalSessionModel(
                auth_realm_id=auth_realm_id,
                principal_subject=principal_subject,
                principal_class=principal_class,
                audience=audience,
                scope_family=scope_family,
                access_token_jti=access_token_jti,
                refresh_token_id=refresh_token_record.id,
                expires_at=expires_at,
            )
        )
        await session.flush()
