"""SQLAlchemy repository for support tickets."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.support_ticket import (
    SupportActorType,
    SupportMessageVisibility,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketEvent,
    SupportTicketEventType,
    SupportTicketMessage,
    SupportTicketOwnerType,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
    public_message_preview,
)
from src.domain.repositories.support_ticket_repository import SupportTicketListResult, SupportTicketRepository
from src.infrastructure.database.models.support_ticket_model import (
    SupportTicketEventModel,
    SupportTicketMessageModel,
    SupportTicketModel,
)


def _parse_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        value = int(cursor)
    except ValueError:
        return 0
    return max(value, 0)


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SQLAlchemySupportTicketRepository(SupportTicketRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_ticket(
        self,
        *,
        public_id: str,
        owner_type: SupportTicketOwnerType,
        customer_account_id: UUID | None,
        partner_workspace_id: UUID | None,
        created_by_actor_type: SupportActorType,
        created_by_actor_id: UUID | None,
        source: SupportTicketSource,
        status: SupportTicketStatus,
        category: SupportTicketCategory,
        priority: SupportTicketPriority,
        subject: str,
        message_body: str,
        metadata: dict[str, object] | None = None,
    ) -> SupportTicket:
        now = _utc_now()
        ticket = SupportTicketModel(
            public_id=public_id,
            owner_type=owner_type.value,
            customer_account_id=customer_account_id,
            partner_workspace_id=partner_workspace_id,
            created_by_actor_type=created_by_actor_type.value,
            created_by_actor_id=created_by_actor_id,
            source=source.value,
            status=status.value,
            category=category.value,
            priority=priority.value,
            subject=subject,
            last_message_preview=public_message_preview(message_body),
            metadata_json=metadata or {},
            created_at=now,
            updated_at=now,
            last_customer_message_at=now if owner_type == SupportTicketOwnerType.CUSTOMER else None,
            last_support_message_at=None,
        )
        self._session.add(ticket)
        await self._session.flush()

        self._session.add(
            SupportTicketMessageModel(
                ticket_id=ticket.id,
                author_type=created_by_actor_type.value,
                author_id=created_by_actor_id,
                visibility=SupportMessageVisibility.PUBLIC.value,
                body=message_body,
                created_at=now,
            )
        )
        self._session.add(
            SupportTicketEventModel(
                ticket_id=ticket.id,
                actor_type=created_by_actor_type.value,
                actor_id=created_by_actor_id,
                event_type=SupportTicketEventType.TICKET_CREATED.value,
                audit_summary="Support ticket created",
                created_at=now,
            )
        )
        await self._session.flush()
        return await self._get_required_detail(ticket.id)

    async def get_detail(self, ticket_ref: str) -> SupportTicket | None:
        stmt = self._detail_select()
        ticket_id = _parse_uuid(ticket_ref)
        if ticket_id is None:
            stmt = stmt.where(SupportTicketModel.public_id == ticket_ref)
        else:
            stmt = stmt.where(or_(SupportTicketModel.id == ticket_id, SupportTicketModel.public_id == ticket_ref))

        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model is not None else None

    async def list_for_customer(
        self,
        *,
        customer_account_id: UUID,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        stmt = select(SupportTicketModel).where(SupportTicketModel.customer_account_id == customer_account_id)
        if status is not None:
            stmt = stmt.where(SupportTicketModel.status == status.value)
        if category is not None:
            stmt = stmt.where(SupportTicketModel.category == category.value)
        return await self._list(stmt, cursor=cursor, limit=limit)

    async def list_for_partner(
        self,
        *,
        partner_workspace_id: UUID,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        priority: SupportTicketPriority | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        stmt = select(SupportTicketModel).where(SupportTicketModel.partner_workspace_id == partner_workspace_id)
        if status is not None:
            stmt = stmt.where(SupportTicketModel.status == status.value)
        if category is not None:
            stmt = stmt.where(SupportTicketModel.category == category.value)
        if priority is not None:
            stmt = stmt.where(SupportTicketModel.priority == priority.value)
        return await self._list(stmt, cursor=cursor, limit=limit)

    async def list_for_admin(
        self,
        *,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        priority: SupportTicketPriority | None = None,
        assigned_admin_id: UUID | None = None,
        source: SupportTicketSource | None = None,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        stmt = select(SupportTicketModel)
        if status is not None:
            stmt = stmt.where(SupportTicketModel.status == status.value)
        if category is not None:
            stmt = stmt.where(SupportTicketModel.category == category.value)
        if priority is not None:
            stmt = stmt.where(SupportTicketModel.priority == priority.value)
        if assigned_admin_id is not None:
            stmt = stmt.where(SupportTicketModel.assigned_admin_id == assigned_admin_id)
        if source is not None:
            stmt = stmt.where(SupportTicketModel.source == source.value)

        normalized_query = (query or "").strip()
        if normalized_query:
            like = f"%{normalized_query}%"
            stmt = stmt.where(
                or_(
                    SupportTicketModel.public_id.ilike(like),
                    SupportTicketModel.subject.ilike(like),
                    cast(SupportTicketModel.customer_account_id, String).ilike(like),
                    cast(SupportTicketModel.partner_workspace_id, String).ilike(like),
                )
            )

        return await self._list(stmt, cursor=cursor, limit=limit)

    async def add_message(
        self,
        *,
        ticket: SupportTicket,
        author_type: SupportActorType,
        author_id: UUID | None,
        visibility: SupportMessageVisibility,
        body: str,
        next_status: SupportTicketStatus | None = None,
    ) -> SupportTicket:
        model = await self._get_model(ticket.id)
        if model is None:
            raise LookupError("Support ticket not found")

        now = _utc_now()
        self._session.add(
            SupportTicketMessageModel(
                ticket_id=model.id,
                author_type=author_type.value,
                author_id=author_id,
                visibility=visibility.value,
                body=body,
                created_at=now,
            )
        )
        if visibility == SupportMessageVisibility.PUBLIC:
            model.last_message_preview = public_message_preview(body)
            if author_type in {SupportActorType.CUSTOMER, SupportActorType.PARTNER}:
                model.last_customer_message_at = now
            elif author_type == SupportActorType.ADMIN:
                model.last_support_message_at = now
        if next_status is not None:
            self._set_status_fields(model, next_status, now)
        model.updated_at = now
        await self._session.flush()
        return await self._get_required_detail(model.id)

    async def add_event(
        self,
        *,
        ticket_id: UUID,
        actor_type: SupportActorType,
        actor_id: UUID | None,
        event_type: SupportTicketEventType,
        audit_summary: str,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        self._session.add(
            SupportTicketEventModel(
                ticket_id=ticket_id,
                actor_type=actor_type.value,
                actor_id=actor_id,
                event_type=event_type.value,
                from_value=from_value,
                to_value=to_value,
                audit_summary=audit_summary,
                created_at=_utc_now(),
            )
        )
        await self._session.flush()

    async def update_ticket(
        self,
        *,
        ticket: SupportTicket,
        actor_type: SupportActorType,
        actor_id: UUID | None,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        priority: SupportTicketPriority | None = None,
        assigned_admin_id: UUID | None = None,
        assigned_admin_id_set: bool = False,
    ) -> SupportTicket:
        model = await self._get_model(ticket.id)
        if model is None:
            raise LookupError("Support ticket not found")

        now = _utc_now()
        if status is not None and model.status != status.value:
            previous = model.status
            self._set_status_fields(model, status, now)
            await self.add_event(
                ticket_id=model.id,
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=SupportTicketEventType.STATUS_CHANGED,
                from_value=previous,
                to_value=status.value,
                audit_summary=f"Status changed from {previous} to {status.value}",
            )
        if category is not None and model.category != category.value:
            previous = model.category
            model.category = category.value
            await self.add_event(
                ticket_id=model.id,
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=SupportTicketEventType.CATEGORY_CHANGED,
                from_value=previous,
                to_value=category.value,
                audit_summary=f"Category changed from {previous} to {category.value}",
            )
        if priority is not None and model.priority != priority.value:
            previous = model.priority
            model.priority = priority.value
            await self.add_event(
                ticket_id=model.id,
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=SupportTicketEventType.PRIORITY_CHANGED,
                from_value=previous,
                to_value=priority.value,
                audit_summary=f"Priority changed from {previous} to {priority.value}",
            )
        if assigned_admin_id_set and model.assigned_admin_id != assigned_admin_id:
            previous = str(model.assigned_admin_id) if model.assigned_admin_id is not None else None
            model.assigned_admin_id = assigned_admin_id
            await self.add_event(
                ticket_id=model.id,
                actor_type=actor_type,
                actor_id=actor_id,
                event_type=SupportTicketEventType.ASSIGNED,
                from_value=previous,
                to_value=str(assigned_admin_id) if assigned_admin_id is not None else None,
                audit_summary="Assignment changed",
            )
        model.updated_at = now
        await self._session.flush()
        return await self._get_required_detail(model.id)

    def _detail_select(self):
        return (
            select(SupportTicketModel)
            .options(
                selectinload(SupportTicketModel.messages),
                selectinload(SupportTicketModel.events),
            )
            .execution_options(populate_existing=True)
        )

    async def _get_model(self, ticket_id: UUID) -> SupportTicketModel | None:
        result = await self._session.execute(select(SupportTicketModel).where(SupportTicketModel.id == ticket_id))
        return result.scalar_one_or_none()

    async def _get_required_detail(self, ticket_id: UUID) -> SupportTicket:
        result = await self._session.execute(self._detail_select().where(SupportTicketModel.id == ticket_id))
        model = result.scalar_one()
        return self._to_domain(model)

    async def _list(self, stmt, *, cursor: str | None, limit: int) -> SupportTicketListResult:
        offset = _parse_cursor(cursor)
        bounded_limit = min(max(limit, 1), 100)
        stmt = stmt.options(
            selectinload(SupportTicketModel.messages),
            selectinload(SupportTicketModel.events),
        ).order_by(SupportTicketModel.updated_at.desc(), SupportTicketModel.id.desc())
        result = await self._session.execute(stmt.offset(offset).limit(bounded_limit + 1))
        models = list(result.scalars().all())
        next_cursor = str(offset + bounded_limit) if len(models) > bounded_limit else None
        return SupportTicketListResult(
            tickets=tuple(self._to_domain(model) for model in models[:bounded_limit]),
            next_cursor=next_cursor,
        )

    @staticmethod
    def _set_status_fields(model: SupportTicketModel, status: SupportTicketStatus, now: datetime) -> None:
        model.status = status.value
        if status == SupportTicketStatus.RESOLVED:
            model.resolved_at = now
            model.closed_at = None
        elif status == SupportTicketStatus.CLOSED:
            model.closed_at = now
        elif status == SupportTicketStatus.PENDING_SUPPORT:
            model.resolved_at = None
            model.closed_at = None

    @staticmethod
    def _to_domain(model: SupportTicketModel) -> SupportTicket:
        return SupportTicket(
            id=model.id,
            public_id=model.public_id,
            owner_type=SupportTicketOwnerType(model.owner_type),
            customer_account_id=model.customer_account_id,
            partner_workspace_id=model.partner_workspace_id,
            created_by_actor_type=SupportActorType(model.created_by_actor_type),
            created_by_actor_id=model.created_by_actor_id,
            source=SupportTicketSource(model.source),
            status=SupportTicketStatus(model.status),
            category=SupportTicketCategory(model.category),
            priority=SupportTicketPriority(model.priority),
            subject=model.subject,
            last_message_preview=model.last_message_preview,
            assigned_admin_id=model.assigned_admin_id,
            metadata=dict(model.metadata_json or {}),
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_customer_message_at=model.last_customer_message_at,
            last_support_message_at=model.last_support_message_at,
            resolved_at=model.resolved_at,
            closed_at=model.closed_at,
            messages=tuple(
                SupportTicketMessage(
                    id=message.id,
                    ticket_id=message.ticket_id,
                    author_type=SupportActorType(message.author_type),
                    author_id=message.author_id,
                    visibility=SupportMessageVisibility(message.visibility),
                    body=message.body,
                    created_at=message.created_at,
                )
                for message in model.messages
            ),
            events=tuple(
                SupportTicketEvent(
                    id=event.id,
                    ticket_id=event.ticket_id,
                    actor_type=SupportActorType(event.actor_type),
                    actor_id=event.actor_id,
                    event_type=SupportTicketEventType(event.event_type),
                    from_value=event.from_value,
                    to_value=event.to_value,
                    audit_summary=event.audit_summary,
                    created_at=event.created_at,
                )
                for event in model.events
            ),
        )
