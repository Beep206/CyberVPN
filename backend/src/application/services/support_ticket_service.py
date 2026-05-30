"""Support ticket application service."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.support_ticket import (
    SupportActorType,
    SupportMessageVisibility,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketEventType,
    SupportTicketNotFoundError,
    SupportTicketOwnerType,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
    assert_customer_category,
    assert_customer_priority,
    assert_status_transition,
    status_after_public_reply,
)
from src.domain.repositories.support_ticket_repository import SupportTicketListResult, SupportTicketRepository


@dataclass(frozen=True, slots=True)
class AdminSupportTicketUpdate:
    status: SupportTicketStatus | None = None
    category: SupportTicketCategory | None = None
    priority: SupportTicketPriority | None = None
    assigned_admin_id: UUID | None = None
    assigned_admin_id_set: bool = False


class SupportTicketService:
    def __init__(self, repository: SupportTicketRepository) -> None:
        self._repository = repository

    async def create_customer_ticket(
        self,
        *,
        customer_account_id: UUID,
        category: SupportTicketCategory,
        subject: str,
        message: str,
        source: SupportTicketSource = SupportTicketSource.CUSTOMER_WEB,
        priority: SupportTicketPriority = SupportTicketPriority.NORMAL,
        metadata: dict[str, object] | None = None,
    ) -> SupportTicket:
        assert_customer_category(category)
        assert_customer_priority(priority)
        if source not in {SupportTicketSource.CUSTOMER_WEB, SupportTicketSource.TELEGRAM_MINI_APP}:
            raise ValueError("Unsupported customer support ticket source")
        return await self._repository.create_ticket(
            public_id=self._new_public_id(),
            owner_type=SupportTicketOwnerType.CUSTOMER,
            customer_account_id=customer_account_id,
            partner_workspace_id=None,
            created_by_actor_type=SupportActorType.CUSTOMER,
            created_by_actor_id=customer_account_id,
            source=source,
            status=SupportTicketStatus.OPEN,
            category=category,
            priority=priority,
            subject=subject.strip(),
            message_body=message.strip(),
            metadata=metadata,
        )

    async def create_partner_ticket(
        self,
        *,
        partner_workspace_id: UUID,
        actor_id: UUID,
        category: SupportTicketCategory,
        subject: str,
        message: str,
        priority: SupportTicketPriority = SupportTicketPriority.NORMAL,
        metadata: dict[str, object] | None = None,
    ) -> SupportTicket:
        assert_customer_category(category)
        assert_customer_priority(priority)
        return await self._repository.create_ticket(
            public_id=self._new_public_id(),
            owner_type=SupportTicketOwnerType.PARTNER,
            customer_account_id=None,
            partner_workspace_id=partner_workspace_id,
            created_by_actor_type=SupportActorType.PARTNER,
            created_by_actor_id=actor_id,
            source=SupportTicketSource.PARTNER_PORTAL,
            status=SupportTicketStatus.OPEN,
            category=category,
            priority=priority,
            subject=subject.strip(),
            message_body=message.strip(),
            metadata=metadata,
        )

    async def list_customer_tickets(
        self,
        *,
        customer_account_id: UUID,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        return await self._repository.list_for_customer(
            customer_account_id=customer_account_id,
            status=status,
            category=category,
            cursor=cursor,
            limit=limit,
        )

    async def list_partner_tickets(
        self,
        *,
        partner_workspace_id: UUID,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        priority: SupportTicketPriority | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        return await self._repository.list_for_partner(
            partner_workspace_id=partner_workspace_id,
            status=status,
            category=category,
            priority=priority,
            cursor=cursor,
            limit=limit,
        )

    async def list_admin_tickets(
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
        return await self._repository.list_for_admin(
            status=status,
            category=category,
            priority=priority,
            assigned_admin_id=assigned_admin_id,
            source=source,
            query=query,
            cursor=cursor,
            limit=limit,
        )

    async def get_customer_ticket(self, *, ticket_ref: str, customer_account_id: UUID) -> SupportTicket:
        ticket = await self._get_ticket(ticket_ref)
        if ticket.owner_type != SupportTicketOwnerType.CUSTOMER or ticket.customer_account_id != customer_account_id:
            raise SupportTicketNotFoundError("Support ticket not found")
        return ticket

    async def get_partner_ticket(self, *, ticket_ref: str, partner_workspace_id: UUID) -> SupportTicket:
        ticket = await self._get_ticket(ticket_ref)
        if (
            ticket.owner_type != SupportTicketOwnerType.PARTNER
            or ticket.partner_workspace_id != partner_workspace_id
        ):
            raise SupportTicketNotFoundError("Support ticket not found")
        return ticket

    async def get_admin_ticket(self, *, ticket_ref: str) -> SupportTicket:
        return await self._get_ticket(ticket_ref)

    async def add_customer_reply(
        self,
        *,
        ticket_ref: str,
        customer_account_id: UUID,
        message: str,
    ) -> SupportTicket:
        ticket = await self.get_customer_ticket(ticket_ref=ticket_ref, customer_account_id=customer_account_id)
        next_status = status_after_public_reply(SupportActorType.CUSTOMER, ticket.status)
        assert_status_transition(
            actor_type=SupportActorType.CUSTOMER,
            current_status=ticket.status,
            requested_status=next_status,
        )
        updated = await self._repository.add_message(
            ticket=ticket,
            author_type=SupportActorType.CUSTOMER,
            author_id=customer_account_id,
            visibility=SupportMessageVisibility.PUBLIC,
            body=message.strip(),
            next_status=next_status,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.CUSTOMER,
            actor_id=customer_account_id,
            event_type=SupportTicketEventType.PUBLIC_REPLY_ADDED,
            audit_summary="Customer public reply added",
        )
        return await self._get_ticket(str(updated.id))

    async def add_partner_reply(
        self,
        *,
        ticket_ref: str,
        partner_workspace_id: UUID,
        actor_id: UUID,
        message: str,
    ) -> SupportTicket:
        ticket = await self.get_partner_ticket(ticket_ref=ticket_ref, partner_workspace_id=partner_workspace_id)
        next_status = status_after_public_reply(SupportActorType.PARTNER, ticket.status)
        assert_status_transition(
            actor_type=SupportActorType.PARTNER,
            current_status=ticket.status,
            requested_status=next_status,
        )
        updated = await self._repository.add_message(
            ticket=ticket,
            author_type=SupportActorType.PARTNER,
            author_id=actor_id,
            visibility=SupportMessageVisibility.PUBLIC,
            body=message.strip(),
            next_status=next_status,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.PARTNER,
            actor_id=actor_id,
            event_type=SupportTicketEventType.PUBLIC_REPLY_ADDED,
            audit_summary="Partner public reply added",
        )
        return await self._get_ticket(str(updated.id))

    async def close_customer_ticket(self, *, ticket_ref: str, customer_account_id: UUID) -> SupportTicket:
        ticket = await self.get_customer_ticket(ticket_ref=ticket_ref, customer_account_id=customer_account_id)
        assert_status_transition(
            actor_type=SupportActorType.CUSTOMER,
            current_status=ticket.status,
            requested_status=SupportTicketStatus.CLOSED,
        )
        updated = await self._repository.update_ticket(
            ticket=ticket,
            actor_type=SupportActorType.CUSTOMER,
            actor_id=customer_account_id,
            status=SupportTicketStatus.CLOSED,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.CUSTOMER,
            actor_id=customer_account_id,
            event_type=SupportTicketEventType.CLOSED,
            from_value=ticket.status.value,
            to_value=SupportTicketStatus.CLOSED.value,
            audit_summary="Customer closed ticket",
        )
        return await self._get_ticket(str(updated.id))

    async def reopen_customer_ticket(self, *, ticket_ref: str, customer_account_id: UUID) -> SupportTicket:
        ticket = await self.get_customer_ticket(ticket_ref=ticket_ref, customer_account_id=customer_account_id)
        return await self._reopen_ticket(
            ticket=ticket,
            actor_type=SupportActorType.CUSTOMER,
            actor_id=customer_account_id,
        )

    async def close_partner_ticket(
        self,
        *,
        ticket_ref: str,
        partner_workspace_id: UUID,
        actor_id: UUID,
    ) -> SupportTicket:
        ticket = await self.get_partner_ticket(ticket_ref=ticket_ref, partner_workspace_id=partner_workspace_id)
        assert_status_transition(
            actor_type=SupportActorType.PARTNER,
            current_status=ticket.status,
            requested_status=SupportTicketStatus.CLOSED,
        )
        updated = await self._repository.update_ticket(
            ticket=ticket,
            actor_type=SupportActorType.PARTNER,
            actor_id=actor_id,
            status=SupportTicketStatus.CLOSED,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.PARTNER,
            actor_id=actor_id,
            event_type=SupportTicketEventType.CLOSED,
            from_value=ticket.status.value,
            to_value=SupportTicketStatus.CLOSED.value,
            audit_summary="Partner closed ticket",
        )
        return await self._get_ticket(str(updated.id))

    async def reopen_partner_ticket(
        self,
        *,
        ticket_ref: str,
        partner_workspace_id: UUID,
        actor_id: UUID,
    ) -> SupportTicket:
        ticket = await self.get_partner_ticket(ticket_ref=ticket_ref, partner_workspace_id=partner_workspace_id)
        return await self._reopen_ticket(ticket=ticket, actor_type=SupportActorType.PARTNER, actor_id=actor_id)

    async def add_admin_reply(self, *, ticket_ref: str, admin_id: UUID, message: str) -> SupportTicket:
        ticket = await self._get_ticket(ticket_ref)
        next_status = status_after_public_reply(SupportActorType.ADMIN, ticket.status)
        assert_status_transition(
            actor_type=SupportActorType.ADMIN,
            current_status=ticket.status,
            requested_status=next_status,
        )
        updated = await self._repository.add_message(
            ticket=ticket,
            author_type=SupportActorType.ADMIN,
            author_id=admin_id,
            visibility=SupportMessageVisibility.PUBLIC,
            body=message.strip(),
            next_status=next_status,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.ADMIN,
            actor_id=admin_id,
            event_type=SupportTicketEventType.PUBLIC_REPLY_ADDED,
            audit_summary="Admin public reply added",
        )
        return await self._get_ticket(str(updated.id))

    async def add_admin_internal_note(self, *, ticket_ref: str, admin_id: UUID, message: str) -> SupportTicket:
        ticket = await self._get_ticket(ticket_ref)
        updated = await self._repository.add_message(
            ticket=ticket,
            author_type=SupportActorType.ADMIN,
            author_id=admin_id,
            visibility=SupportMessageVisibility.INTERNAL,
            body=message.strip(),
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=SupportActorType.ADMIN,
            actor_id=admin_id,
            event_type=SupportTicketEventType.INTERNAL_NOTE_ADDED,
            audit_summary="Admin internal note added",
        )
        return await self._get_ticket(str(updated.id))

    async def update_admin_ticket(
        self,
        *,
        ticket_ref: str,
        admin_id: UUID,
        update: AdminSupportTicketUpdate,
    ) -> SupportTicket:
        ticket = await self._get_ticket(ticket_ref)
        if update.status is not None:
            assert_status_transition(
                actor_type=SupportActorType.ADMIN,
                current_status=ticket.status,
                requested_status=update.status,
            )
        return await self._repository.update_ticket(
            ticket=ticket,
            actor_type=SupportActorType.ADMIN,
            actor_id=admin_id,
            status=update.status,
            category=update.category,
            priority=update.priority,
            assigned_admin_id=update.assigned_admin_id,
            assigned_admin_id_set=update.assigned_admin_id_set,
        )

    async def _reopen_ticket(
        self,
        *,
        ticket: SupportTicket,
        actor_type: SupportActorType,
        actor_id: UUID,
    ) -> SupportTicket:
        assert_status_transition(
            actor_type=actor_type,
            current_status=ticket.status,
            requested_status=SupportTicketStatus.PENDING_SUPPORT,
        )
        updated = await self._repository.update_ticket(
            ticket=ticket,
            actor_type=actor_type,
            actor_id=actor_id,
            status=SupportTicketStatus.PENDING_SUPPORT,
        )
        await self._repository.add_event(
            ticket_id=ticket.id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=SupportTicketEventType.REOPENED,
            from_value=ticket.status.value,
            to_value=SupportTicketStatus.PENDING_SUPPORT.value,
            audit_summary="Ticket reopened",
        )
        return await self._get_ticket(str(updated.id))

    async def _get_ticket(self, ticket_ref: str) -> SupportTicket:
        ticket = await self._repository.get_detail(ticket_ref)
        if ticket is None:
            raise SupportTicketNotFoundError("Support ticket not found")
        return ticket

    @staticmethod
    def _new_public_id() -> str:
        return f"sup_{secrets.token_urlsafe(8).replace('-', '').replace('_', '').lower()[:10]}"
