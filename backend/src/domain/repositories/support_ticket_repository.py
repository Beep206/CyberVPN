"""Support ticket repository contract."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.support_ticket import (
    SupportActorType,
    SupportMessageVisibility,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketEventType,
    SupportTicketOwnerType,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
)


@dataclass(frozen=True, slots=True)
class SupportTicketListResult:
    tickets: tuple[SupportTicket, ...]
    next_cursor: str | None = None


class SupportTicketRepository:
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
        raise NotImplementedError

    async def get_detail(self, ticket_ref: str) -> SupportTicket | None:
        raise NotImplementedError

    async def list_for_customer(
        self,
        *,
        customer_account_id: UUID,
        status: SupportTicketStatus | None = None,
        category: SupportTicketCategory | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> SupportTicketListResult:
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError
