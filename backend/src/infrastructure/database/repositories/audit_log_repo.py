from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.audit_log_model import AuditLog


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        event_type: str,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str = "0.0.0.0",
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create a new audit log entry.

        Args:
            event_type: The type of event (e.g., 'registration_attempt', 'login')
            actor_id: The admin user ID performing the action (None for anonymous)
            resource_type: The type of resource affected (e.g., 'user', 'server')
            resource_id: The ID of the affected resource
            details: Additional details about the event
            ip_address: The IP address of the request
            user_agent: The user agent of the request

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog(
            admin_id=actor_id,
            action=event_type,
            entity_type=resource_type,
            entity_id=resource_id,
            new_value=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(audit_log)
        await self._session.commit()
        await self._session.refresh(audit_log)
        return audit_log

    async def get_paginated(self, offset: int = 0, limit: int = 50) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(AuditLog))
        return result.scalar_one()

    async def get_by_admin_id(self, admin_id: UUID, offset: int = 0, limit: int = 50) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLog)
            .where(AuditLog.admin_id == admin_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
