"""Customer, partner, and admin support ticket routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.support_ticket_service import AdminSupportTicketUpdate, SupportTicketService
from src.application.use_cases.auth.permissions import Permission
from src.domain.entities.partner_permission import PartnerPermission
from src.domain.entities.support_ticket import (
    PUBLIC_EVENT_TYPES,
    InvalidSupportTicketTransitionError,
    SupportActorType,
    SupportMessageVisibility,
    SupportTicket,
    SupportTicketCategory,
    SupportTicketNotFoundError,
    SupportTicketPriority,
    SupportTicketSource,
    SupportTicketStatus,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.support_ticket_repo import SQLAlchemySupportTicketRepository
from src.presentation.dependencies.auth import get_current_active_user, get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.partner_workspace import (
    PartnerWorkspaceAccess,
    require_partner_workspace_permission,
)
from src.presentation.dependencies.roles import require_permission

from .schemas import (
    AdminSupportTicketUpdateRequest,
    PartnerSupportTicketCreateRequest,
    PublicSupportTicketDetailResponse,
    PublicSupportTicketEventResponse,
    PublicSupportTicketListResponse,
    PublicSupportTicketMessageResponse,
    PublicSupportTicketSummaryResponse,
    SupportTicketCreateRequest,
    SupportTicketDetailResponse,
    SupportTicketEventResponse,
    SupportTicketListResponse,
    SupportTicketMessageResponse,
    SupportTicketReplyRequest,
    SupportTicketSummaryResponse,
)

router = APIRouter(tags=["support-tickets"])
customer_router = APIRouter(prefix="/support/tickets", tags=["support-tickets"])
partner_router = APIRouter(prefix="/partner-workspaces/{workspace_id}/support/tickets", tags=["partner-support"])
admin_router = APIRouter(prefix="/admin/support/tickets", tags=["admin", "support-tickets"])


def _service(db: AsyncSession) -> SupportTicketService:
    return SupportTicketService(SQLAlchemySupportTicketRepository(db))


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, SupportTicketNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found") from exc
    if isinstance(exc, InvalidSupportTicketTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _summary_response(ticket: SupportTicket) -> SupportTicketSummaryResponse:
    return SupportTicketSummaryResponse(
        id=ticket.id,
        public_id=ticket.public_id,
        owner_type=ticket.owner_type,
        customer_account_id=ticket.customer_account_id,
        partner_workspace_id=ticket.partner_workspace_id,
        source=ticket.source,
        status=ticket.status,
        category=ticket.category,
        priority=ticket.priority,
        subject=ticket.subject,
        last_message_preview=ticket.last_message_preview,
        assigned_admin_id=ticket.assigned_admin_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_customer_message_at=ticket.last_customer_message_at,
        last_support_message_at=ticket.last_support_message_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
    )


def _detail_response(ticket: SupportTicket, *, include_internal: bool) -> SupportTicketDetailResponse:
    messages = [
        SupportTicketMessageResponse(
            id=message.id,
            ticket_id=message.ticket_id,
            author_type=message.author_type,
            author_id=message.author_id,
            visibility=message.visibility,
            body=message.body,
            created_at=message.created_at,
        )
        for message in ticket.messages
        if include_internal or message.visibility == SupportMessageVisibility.PUBLIC
    ]
    events = [
        SupportTicketEventResponse(
            id=event.id,
            ticket_id=event.ticket_id,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            event_type=event.event_type,
            from_value=event.from_value,
            to_value=event.to_value,
            audit_summary=event.audit_summary,
            created_at=event.created_at,
        )
        for event in ticket.events
        if include_internal or event.event_type in PUBLIC_EVENT_TYPES
    ]
    return SupportTicketDetailResponse(
        **_summary_response(ticket).model_dump(),
        messages=messages,
        events=events,
    )


def _public_actor_label(actor_type: SupportActorType) -> str:
    if actor_type == SupportActorType.ADMIN:
        return "support"
    return actor_type.value


def _public_summary_response(ticket: SupportTicket) -> PublicSupportTicketSummaryResponse:
    return PublicSupportTicketSummaryResponse(
        public_id=ticket.public_id,
        status=ticket.status,
        category=ticket.category,
        priority=ticket.priority,
        subject=ticket.subject,
        last_message_preview=ticket.last_message_preview,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_customer_message_at=ticket.last_customer_message_at,
        last_support_message_at=ticket.last_support_message_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
    )


def _public_detail_response(ticket: SupportTicket) -> PublicSupportTicketDetailResponse:
    messages = [
        PublicSupportTicketMessageResponse(
            author_label=_public_actor_label(message.author_type),
            body=message.body,
            created_at=message.created_at,
        )
        for message in ticket.messages
        if message.visibility == SupportMessageVisibility.PUBLIC
    ]
    events = [
        PublicSupportTicketEventResponse(
            actor_label=_public_actor_label(event.actor_type),
            event_type=event.event_type,
            from_value=event.from_value,
            to_value=event.to_value,
            audit_summary=event.audit_summary,
            created_at=event.created_at,
        )
        for event in ticket.events
        if event.event_type in PUBLIC_EVENT_TYPES
    ]
    return PublicSupportTicketDetailResponse(
        **_public_summary_response(ticket).model_dump(),
        messages=messages,
        events=events,
    )


@customer_router.get("", response_model=PublicSupportTicketListResponse)
async def list_customer_support_tickets(
    ticket_status: SupportTicketStatus | None = Query(None, alias="status"),
    category: SupportTicketCategory | None = None,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketListResponse:
    result = await _service(db).list_customer_tickets(
        customer_account_id=customer_account_id,
        status=ticket_status,
        category=category,
        cursor=cursor,
        limit=limit,
    )
    return PublicSupportTicketListResponse(
        tickets=[_public_summary_response(ticket) for ticket in result.tickets],
        next_cursor=result.next_cursor,
    )


@customer_router.post("", response_model=PublicSupportTicketDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_support_ticket(
    payload: SupportTicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).create_customer_ticket(
            customer_account_id=customer_account_id,
            category=payload.category,
            subject=payload.subject,
            message=payload.message,
            source=SupportTicketSource.CUSTOMER_WEB,
            priority=payload.priority,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@customer_router.get("/{ticket_ref}", response_model=PublicSupportTicketDetailResponse)
async def get_customer_support_ticket(
    ticket_ref: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).get_customer_ticket(
            ticket_ref=ticket_ref,
            customer_account_id=customer_account_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@customer_router.post("/{ticket_ref}/replies", response_model=PublicSupportTicketDetailResponse)
async def add_customer_support_reply(
    ticket_ref: str,
    payload: SupportTicketReplyRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).add_customer_reply(
            ticket_ref=ticket_ref,
            customer_account_id=customer_account_id,
            message=payload.message,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@customer_router.post("/{ticket_ref}/close", response_model=PublicSupportTicketDetailResponse)
async def close_customer_support_ticket(
    ticket_ref: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).close_customer_ticket(
            ticket_ref=ticket_ref,
            customer_account_id=customer_account_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@customer_router.post("/{ticket_ref}/reopen", response_model=PublicSupportTicketDetailResponse)
async def reopen_customer_support_ticket(
    ticket_ref: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).reopen_customer_ticket(
            ticket_ref=ticket_ref,
            customer_account_id=customer_account_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@partner_router.get("", response_model=PublicSupportTicketListResponse)
async def list_partner_support_tickets(
    ticket_status: SupportTicketStatus | None = Query(None, alias="status"),
    category: SupportTicketCategory | None = None,
    priority: SupportTicketPriority | None = None,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)
    ),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketListResponse:
    result = await _service(db).list_partner_tickets(
        partner_workspace_id=workspace_access.workspace.id,
        status=ticket_status,
        category=category,
        priority=priority,
        cursor=cursor,
        limit=limit,
    )
    return PublicSupportTicketListResponse(
        tickets=[_public_summary_response(ticket) for ticket in result.tickets],
        next_cursor=result.next_cursor,
    )


@partner_router.post("", response_model=PublicSupportTicketDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_support_ticket(
    payload: PartnerSupportTicketCreateRequest,
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)
    ),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).create_partner_ticket(
            partner_workspace_id=workspace_access.workspace.id,
            actor_id=current_user.id,
            category=payload.category,
            subject=payload.subject,
            message=payload.message,
            priority=payload.priority,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@partner_router.get("/{ticket_ref}", response_model=PublicSupportTicketDetailResponse)
async def get_partner_support_ticket(
    ticket_ref: str,
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.WORKSPACE_READ)
    ),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).get_partner_ticket(
            ticket_ref=ticket_ref,
            partner_workspace_id=workspace_access.workspace.id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@partner_router.post("/{ticket_ref}/replies", response_model=PublicSupportTicketDetailResponse)
async def add_partner_support_reply(
    ticket_ref: str,
    payload: SupportTicketReplyRequest,
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)
    ),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).add_partner_reply(
            ticket_ref=ticket_ref,
            partner_workspace_id=workspace_access.workspace.id,
            actor_id=current_user.id,
            message=payload.message,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@partner_router.post("/{ticket_ref}/close", response_model=PublicSupportTicketDetailResponse)
async def close_partner_support_ticket(
    ticket_ref: str,
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)
    ),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).close_partner_ticket(
            ticket_ref=ticket_ref,
            partner_workspace_id=workspace_access.workspace.id,
            actor_id=current_user.id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@partner_router.post("/{ticket_ref}/reopen", response_model=PublicSupportTicketDetailResponse)
async def reopen_partner_support_ticket(
    ticket_ref: str,
    workspace_access: PartnerWorkspaceAccess = Depends(
        require_partner_workspace_permission(PartnerPermission.OPERATIONS_WRITE)
    ),
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PublicSupportTicketDetailResponse:
    try:
        ticket = await _service(db).reopen_partner_ticket(
            ticket_ref=ticket_ref,
            partner_workspace_id=workspace_access.workspace.id,
            actor_id=current_user.id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _public_detail_response(ticket)


@admin_router.get("", response_model=SupportTicketListResponse)
async def list_admin_support_tickets(
    ticket_status: SupportTicketStatus | None = Query(None, alias="status"),
    category: SupportTicketCategory | None = None,
    priority: SupportTicketPriority | None = None,
    assigned_admin_id: UUID | None = None,
    source: SupportTicketSource | None = None,
    query: str | None = Query(None, min_length=1, max_length=120),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.SUPPORT_TICKET_READ)),
) -> SupportTicketListResponse:
    result = await _service(db).list_admin_tickets(
        status=ticket_status,
        category=category,
        priority=priority,
        assigned_admin_id=assigned_admin_id,
        source=source,
        query=query,
        cursor=cursor,
        limit=limit,
    )
    return SupportTicketListResponse(
        tickets=[_summary_response(ticket) for ticket in result.tickets],
        next_cursor=result.next_cursor,
    )


@admin_router.get("/{ticket_ref}", response_model=SupportTicketDetailResponse)
async def get_admin_support_ticket(
    ticket_ref: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.SUPPORT_TICKET_READ)),
) -> SupportTicketDetailResponse:
    try:
        ticket = await _service(db).get_admin_ticket(ticket_ref=ticket_ref)
    except Exception as exc:
        _raise_http(exc)
    return _detail_response(ticket, include_internal=True)


@admin_router.post("/{ticket_ref}/replies", response_model=SupportTicketDetailResponse)
async def add_admin_support_reply(
    ticket_ref: str,
    payload: SupportTicketReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.USER_UPDATE)),
) -> SupportTicketDetailResponse:
    try:
        ticket = await _service(db).add_admin_reply(
            ticket_ref=ticket_ref,
            admin_id=current_user.id,
            message=payload.message,
        )
    except Exception as exc:
        _raise_http(exc)
    return _detail_response(ticket, include_internal=True)


@admin_router.post("/{ticket_ref}/internal-notes", response_model=SupportTicketDetailResponse)
async def add_admin_support_internal_note(
    ticket_ref: str,
    payload: SupportTicketReplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.USER_UPDATE)),
) -> SupportTicketDetailResponse:
    try:
        ticket = await _service(db).add_admin_internal_note(
            ticket_ref=ticket_ref,
            admin_id=current_user.id,
            message=payload.message,
        )
    except Exception as exc:
        _raise_http(exc)
    return _detail_response(ticket, include_internal=True)


@admin_router.patch("/{ticket_ref}", response_model=SupportTicketDetailResponse)
async def update_admin_support_ticket(
    ticket_ref: str,
    payload: AdminSupportTicketUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.USER_UPDATE)),
) -> SupportTicketDetailResponse:
    try:
        ticket = await _service(db).update_admin_ticket(
            ticket_ref=ticket_ref,
            admin_id=current_user.id,
            update=AdminSupportTicketUpdate(
                status=payload.status,
                category=payload.category,
                priority=payload.priority,
                assigned_admin_id=payload.assigned_admin_id,
                assigned_admin_id_set="assigned_admin_id" in payload.model_fields_set,
            ),
        )
    except Exception as exc:
        _raise_http(exc)
    return _detail_response(ticket, include_internal=True)


router.include_router(customer_router)
router.include_router(partner_router)
router.include_router(admin_router)
