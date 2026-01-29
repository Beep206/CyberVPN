from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.events.base import DomainEvent
from src.infrastructure.database.models.audit_log_model import AuditLog


class AuditEventHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, event: DomainEvent, admin_id=None, ip_address="system") -> None:
        log = AuditLog(
            admin_id=admin_id,
            action=event.event_type,
            entity_type=event.data.get("entity_type"),
            entity_id=event.data.get("entity_id"),
            new_value=event.data,
            ip_address=ip_address,
        )
        self._session.add(log)
        await self._session.flush()
