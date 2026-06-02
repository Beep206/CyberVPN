"""Customer and admin messaging REST routes."""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import redis.asyncio as redis
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events.outbox import EventOutboxService
from src.application.services.messaging_service import AdminMessagingConversationUpdate, MessagingService
from src.application.services.ws_ticket_service import MESSAGING_REALTIME_TICKET_SCOPE, WebSocketTicketService
from src.application.use_cases.auth.permissions import Permission
from src.config.settings import settings
from src.domain.entities.messaging import (
    BroadcastCampaign,
    BroadcastCampaignNotFoundError,
    MessagingConversation,
    MessagingConversationCategory,
    MessagingConversationClosedError,
    MessagingConversationNotFoundError,
    MessagingConversationStatus,
    MessagingForbiddenError,
    MessagingMessage,
    MessagingMessageVisibility,
    MessagingPriority,
    MessagingSenderType,
    SiteNotificationDelivery,
    SiteNotificationDeliveryStatus,
    SiteNotificationNotFoundError,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.messaging_repository import SQLAlchemyMessagingRepository
from src.infrastructure.messaging.presence import MessagingPresenceIdentity, MessagingPresenceRegistry
from src.infrastructure.messaging.realtime_contract import build_sync_cursor, build_sync_required_payload
from src.infrastructure.messaging.sse_manager import _format_sse_event, sse_manager
from src.infrastructure.messaging.websocket_manager import ws_manager
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .schemas import (
    AdminConversationDetailResponse,
    AdminConversationListResponse,
    AdminConversationSummaryResponse,
    AdminConversationUpdateRequest,
    AdminCreateConversationRequest,
    BroadcastCampaignResponse,
    BroadcastCreateRequest,
    CustomerConversationDetailResponse,
    CustomerConversationListResponse,
    CustomerConversationSummaryResponse,
    CustomerMessagingMessageResponse,
    CustomerMessagingMessageWriteResponse,
    MessagingMessageResponse,
    MessagingMessageWriteResponse,
    MessagingReadRequest,
    MessagingReadStateResponse,
    MessagingRealtimeSyncResponse,
    MessagingRealtimeTicketResponse,
    MessagingUnreadCountsResponse,
    MessagingWriteRequest,
    SiteNotificationDismissRequest,
    SiteNotificationDismissResponse,
    SiteNotificationListResponse,
    SiteNotificationReadRequest,
    SiteNotificationReadResponse,
    SiteNotificationResponse,
)

router = APIRouter(tags=["messaging"])
customer_router = APIRouter(prefix="/me", tags=["messaging"])
admin_router = APIRouter(prefix="/admin/messaging", tags=["admin", "messaging"])
admin_notifications_router = APIRouter(prefix="/admin/notifications", tags=["admin", "notifications"])


@dataclass(frozen=True, slots=True)
class MessagingRealtimePrincipal:
    principal_type: str
    principal_id: str

    @property
    def channel(self) -> str:
        return _messaging_channel(self.principal_type, self.principal_id)


def _service(db: AsyncSession) -> MessagingService:
    return MessagingService(SQLAlchemyMessagingRepository(db), EventOutboxService(db))


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _websocket_client_ip(websocket: WebSocket) -> str | None:
    return websocket.client.host if websocket.client else None


def _messaging_channel(principal_type: str, principal_id: str) -> str:
    return f"messaging:{principal_type}:{principal_id}"


def _new_connection_id() -> str:
    return secrets.token_urlsafe(16)


def _sync_cursor() -> str:
    return build_sync_cursor()


def _connection_payload(*, principal: MessagingRealtimePrincipal, connection_id: str, transport: str) -> dict[str, str]:
    return {
        "type": "connected",
        "principal_type": principal.principal_type,
        "connection_id": connection_id,
        "transport": transport,
        "sync_cursor": _sync_cursor(),
        "recovery": "rest_sync",
    }


def _presence_registry(redis_client: redis.Redis) -> MessagingPresenceRegistry:
    return MessagingPresenceRegistry(redis_client, ttl_seconds=settings.messaging_presence_ttl_seconds)


def _presence_identity(
    *,
    principal: MessagingRealtimePrincipal,
    connection_id: str,
    transport: str,
) -> MessagingPresenceIdentity:
    return MessagingPresenceIdentity(
        participant_type=principal.principal_type,
        participant_id=principal.principal_id,
        connection_id=connection_id,
        transport=transport,
    )


def _is_authorized_channel(principal: MessagingRealtimePrincipal, channel: str) -> bool:
    return channel in {principal.channel, "self"}


def _subscription_response(principal: MessagingRealtimePrincipal, channel: str) -> dict[str, str]:
    if _is_authorized_channel(principal, channel):
        return {"type": "subscribed", "channel": "self"}
    return {"type": "error", "code": "UNAUTHORIZED_CHANNEL", "channel": channel}


async def _create_realtime_ticket(
    *,
    redis_client: redis.Redis,
    user_id: str,
    role: str,
    request: Request,
    principal_type: str,
    login: str | None = None,
) -> MessagingRealtimeTicketResponse:
    ticket_service = WebSocketTicketService(redis_client)
    ticket = await ticket_service.create_ticket(
        user_id=user_id,
        role=role,
        login=login,
        ip_address=_client_ip(request),
        principal_type=principal_type,
        scope=MESSAGING_REALTIME_TICKET_SCOPE,
    )
    return MessagingRealtimeTicketResponse(ticket=ticket, expires_in=WebSocketTicketService.TTL_SECONDS)


async def _authenticate_messaging_ws_ticket(
    *,
    websocket: WebSocket,
    ticket: str | None,
    expected_principal_type: str,
    redis_client: redis.Redis,
) -> MessagingRealtimePrincipal:
    if not ticket:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    ticket_service = WebSocketTicketService(redis_client)
    ticket_data = await ticket_service.validate_and_consume(ticket, _websocket_client_ip(websocket))
    if (
        ticket_data is None
        or ticket_data.principal_type != expected_principal_type
        or ticket_data.scope != MESSAGING_REALTIME_TICKET_SCOPE
    ):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    if not ticket_data.user_id:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return MessagingRealtimePrincipal(
        principal_type=expected_principal_type,
        principal_id=ticket_data.user_id,
    )


async def customer_messaging_ws_authenticate(
    websocket: WebSocket,
    ticket: str | None = Query(None),
    redis_client: redis.Redis = Depends(get_redis),
) -> MessagingRealtimePrincipal:
    return await _authenticate_messaging_ws_ticket(
        websocket=websocket,
        ticket=ticket,
        expected_principal_type="customer",
        redis_client=redis_client,
    )


async def admin_messaging_ws_authenticate(
    websocket: WebSocket,
    ticket: str | None = Query(None),
    redis_client: redis.Redis = Depends(get_redis),
) -> MessagingRealtimePrincipal:
    return await _authenticate_messaging_ws_ticket(
        websocket=websocket,
        ticket=ticket,
        expected_principal_type="admin",
        redis_client=redis_client,
    )


async def _serve_messaging_ws(
    *,
    websocket: WebSocket,
    principal: MessagingRealtimePrincipal,
    redis_client: redis.Redis,
) -> None:
    connection_id = _new_connection_id()
    identity = _presence_identity(principal=principal, connection_id=connection_id, transport="websocket")
    presence = _presence_registry(redis_client)
    await ws_manager.connect(websocket, principal.channel)
    await presence.register(identity)
    await websocket.send_json(
        _connection_payload(principal=principal, connection_id=connection_id, transport="websocket")
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            await presence.refresh(identity)
            await _handle_realtime_ws_message(websocket=websocket, principal=principal, raw_message=raw_message)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, principal.channel)
        await presence.disconnect(identity)


async def _handle_realtime_ws_message(
    *,
    websocket: WebSocket,
    principal: MessagingRealtimePrincipal,
    raw_message: str,
) -> None:
    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "code": "INVALID_JSON"})
        return
    if not isinstance(message, dict):
        await websocket.send_json({"type": "error", "code": "INVALID_MESSAGE"})
        return

    message_type = message.get("type")
    if message_type == "ping":
        await websocket.send_json({"type": "pong", "sync_cursor": _sync_cursor()})
        return
    if message_type == "subscribe":
        channels = message.get("channels")
        if not isinstance(channels, list) or not all(isinstance(channel, str) for channel in channels):
            await websocket.send_json({"type": "error", "code": "INVALID_CHANNELS"})
            return
        for channel in channels:
            await websocket.send_json(_subscription_response(principal, channel))
        return
    if message_type == "sync":
        await websocket.send_json({"type": "sync_required", **build_sync_required_payload(reason="client_requested")})
        return
    await websocket.send_json({"type": "error", "code": "UNKNOWN_MESSAGE_TYPE"})


def _sse_response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }


async def _create_messaging_sse_response(
    *,
    principal: MessagingRealtimePrincipal,
    redis_client: redis.Redis,
) -> StreamingResponse:
    connection_id = _new_connection_id()
    identity = _presence_identity(principal=principal, connection_id=connection_id, transport="sse")
    presence = _presence_registry(redis_client)

    async def stream() -> AsyncGenerator[str]:
        await presence.register(identity)
        try:
            yield _format_sse_event(
                "connected",
                _connection_payload(principal=principal, connection_id=connection_id, transport="sse"),
            )
            async for chunk in sse_manager.create_stream(
                principal.channel,
                heartbeat_interval_seconds=settings.messaging_realtime_heartbeat_seconds,
                max_queue_size=settings.messaging_realtime_queue_size,
            ):
                await presence.refresh(identity)
                yield chunk
        finally:
            await presence.disconnect(identity)

    return StreamingResponse(stream(), media_type="text/event-stream", headers=_sse_response_headers())


def _raise_http(exc: Exception) -> None:
    if isinstance(
        exc, (MessagingConversationNotFoundError, SiteNotificationNotFoundError, BroadcastCampaignNotFoundError)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Messaging resource not found") from exc
    if isinstance(exc, MessagingConversationClosedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, MessagingForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    raise exc


def _customer_message_response(message: MessagingMessage) -> CustomerMessagingMessageResponse:
    return CustomerMessagingMessageResponse(
        id=message.id,
        public_id=message.public_id,
        conversation_id=message.conversation_id,
        sender_type=message.sender_type,
        visibility=message.visibility,
        body=message.body,
        created_at=message.created_at,
    )


def _message_response(message: MessagingMessage) -> MessagingMessageResponse:
    return MessagingMessageResponse(
        id=message.id,
        public_id=message.public_id,
        conversation_id=message.conversation_id,
        sender_type=message.sender_type,
        sender_id=message.sender_id,
        visibility=message.visibility,
        body=message.body,
        body_format=message.body_format,
        client_message_id=message.client_message_id,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _customer_summary_response(conversation: MessagingConversation) -> CustomerConversationSummaryResponse:
    return CustomerConversationSummaryResponse(
        id=conversation.id,
        public_id=conversation.public_id,
        status=conversation.status,
        response_state=conversation.response_state,
        category=conversation.category,
        priority=conversation.priority,
        subject=conversation.subject,
        unread_count=MessagingService.unread_count(conversation, own_sender_type=MessagingSenderType.CUSTOMER),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        closed_at=conversation.closed_at,
    )


def _customer_detail_response(conversation: MessagingConversation) -> CustomerConversationDetailResponse:
    return CustomerConversationDetailResponse(
        **_customer_summary_response(conversation).model_dump(),
        messages=[_customer_message_response(message) for message in conversation.messages],
    )


def _admin_summary_response(conversation: MessagingConversation) -> AdminConversationSummaryResponse:
    return AdminConversationSummaryResponse(
        id=conversation.id,
        public_id=conversation.public_id,
        customer_account_id=conversation.customer_account_id,
        status=conversation.status,
        response_state=conversation.response_state,
        category=conversation.category,
        priority=conversation.priority,
        subject=conversation.subject,
        created_by_admin_id=conversation.created_by_admin_id,
        assigned_admin_id=conversation.assigned_admin_id,
        related_support_ticket_id=conversation.related_support_ticket_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        closed_at=conversation.closed_at,
    )


def _admin_detail_response(conversation: MessagingConversation) -> AdminConversationDetailResponse:
    return AdminConversationDetailResponse(
        **_admin_summary_response(conversation).model_dump(),
        messages=[_message_response(message) for message in conversation.messages],
        read_states=[
            MessagingReadStateResponse(
                id=read_state.id,
                conversation_id=read_state.conversation_id,
                participant_id=read_state.participant_id,
                last_read_message_id=read_state.last_read_message_id,
                last_read_at=read_state.last_read_at,
                updated_at=read_state.updated_at,
            )
            for read_state in conversation.read_states
        ],
    )


def _notification_response(notification, delivery: SiteNotificationDelivery) -> SiteNotificationResponse:
    return SiteNotificationResponse(
        id=notification.id,
        delivery_id=delivery.id,
        notification_type=notification.notification_type,
        severity=notification.severity,
        title=notification.title,
        body=notification.body,
        action_url=notification.action_url,
        aggregate_type=notification.aggregate_type,
        aggregate_id=notification.aggregate_id,
        conversation_id=notification.conversation_id,
        message_id=notification.message_id,
        status=delivery.status,
        created_at=notification.created_at,
        updated_at=delivery.updated_at,
        read_at=delivery.read_at,
    )


def _broadcast_response(campaign: BroadcastCampaign) -> BroadcastCampaignResponse:
    return BroadcastCampaignResponse(
        id=campaign.id,
        public_id=campaign.public_id,
        name=campaign.name,
        status=campaign.status,
        audience_type=campaign.audience_type,
        audience_filter=campaign.audience_filter,
        title=campaign.title,
        body=campaign.body,
        action_url=campaign.action_url,
        scheduled_at=campaign.scheduled_at,
        created_by_admin_id=campaign.created_by_admin_id,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@customer_router.get("/conversations", response_model=CustomerConversationListResponse)
async def list_customer_conversations(
    conversation_status: MessagingConversationStatus | None = Query(None, alias="status"),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> CustomerConversationListResponse:
    result = await _service(db).list_customer_conversations(
        customer_account_id=customer_account_id,
        status=conversation_status,
        cursor=cursor,
        limit=limit,
    )
    return CustomerConversationListResponse(
        conversations=[_customer_summary_response(conversation) for conversation in result.conversations],
        next_cursor=result.next_cursor,
    )


@customer_router.get("/conversations/{conversation_id}", response_model=CustomerConversationDetailResponse)
async def get_customer_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> CustomerConversationDetailResponse:
    try:
        conversation = await _service(db).get_customer_conversation(
            conversation_ref=conversation_id,
            customer_account_id=customer_account_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _customer_detail_response(conversation)


@customer_router.post("/conversations/{conversation_id}/messages", response_model=CustomerMessagingMessageWriteResponse)
async def add_customer_message(
    conversation_id: str,
    payload: MessagingWriteRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> CustomerMessagingMessageWriteResponse:
    try:
        result = await _service(db).add_customer_message(
            conversation_ref=conversation_id,
            customer_account_id=customer_account_id,
            body=payload.body,
            client_message_id=payload.client_message_id,
            header_idempotency_key=idempotency_key,
        )
    except Exception as exc:
        _raise_http(exc)
    return CustomerMessagingMessageWriteResponse(
        message=_customer_message_response(result.message),
        conversation=_customer_summary_response(result.conversation),
        created=result.created,
    )


@customer_router.post("/conversations/{conversation_id}/read", response_model=MessagingReadStateResponse)
async def mark_customer_conversation_read(
    conversation_id: str,
    payload: MessagingReadRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> MessagingReadStateResponse:
    try:
        read_state = await _service(db).mark_customer_read(
            conversation_ref=conversation_id,
            customer_account_id=customer_account_id,
            last_read_message_id=payload.last_read_message_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return MessagingReadStateResponse(
        id=read_state.id,
        conversation_id=read_state.conversation_id,
        participant_id=read_state.participant_id,
        last_read_message_id=read_state.last_read_message_id,
        last_read_at=read_state.last_read_at,
        updated_at=read_state.updated_at,
    )


@customer_router.get("/notifications", response_model=SiteNotificationListResponse)
async def list_customer_notifications(
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> SiteNotificationListResponse:
    result = await _service(db).list_customer_notifications(
        customer_account_id=customer_account_id,
        cursor=cursor,
        limit=limit,
    )
    return SiteNotificationListResponse(
        notifications=[
            _notification_response(view.notification, view.delivery)
            for view in result.notifications
            if view.delivery.status != SiteNotificationDeliveryStatus.DISMISSED
        ],
        next_cursor=result.next_cursor,
    )


@customer_router.post("/notifications/read", response_model=SiteNotificationReadResponse)
async def mark_customer_notifications_read(
    payload: SiteNotificationReadRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> SiteNotificationReadResponse:
    try:
        views = await _service(db).mark_customer_notifications_read(
            customer_account_id=customer_account_id,
            notification_ids=tuple(payload.notification_ids),
            read_all_before=payload.read_all_before,
        )
    except Exception as exc:
        _raise_http(exc)
    return SiteNotificationReadResponse(
        notifications=[_notification_response(view.notification, view.delivery) for view in views],
    )


@customer_router.post("/notifications/dismiss", response_model=SiteNotificationDismissResponse)
async def dismiss_customer_notifications(
    payload: SiteNotificationDismissRequest,
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> SiteNotificationDismissResponse:
    try:
        views = await _service(db).dismiss_customer_notifications(
            customer_account_id=customer_account_id,
            notification_ids=tuple(payload.notification_ids),
            read_all_before=payload.read_all_before,
        )
    except Exception as exc:
        _raise_http(exc)
    return SiteNotificationDismissResponse(
        notifications=[_notification_response(view.notification, view.delivery) for view in views],
    )


@customer_router.post("/realtime/ticket", response_model=MessagingRealtimeTicketResponse)
async def create_customer_realtime_ticket(
    request: Request,
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
    redis_client: redis.Redis = Depends(get_redis),
) -> MessagingRealtimeTicketResponse:
    return await _create_realtime_ticket(
        redis_client=redis_client,
        user_id=str(customer_account_id),
        role="customer",
        request=request,
        principal_type="customer",
    )


@customer_router.websocket("/realtime/ws")
async def customer_realtime_ws(
    websocket: WebSocket,
    principal: MessagingRealtimePrincipal = Depends(customer_messaging_ws_authenticate),
    redis_client: redis.Redis = Depends(get_redis),
) -> None:
    await _serve_messaging_ws(websocket=websocket, principal=principal, redis_client=redis_client)


@customer_router.get("/realtime/sse")
async def customer_realtime_sse(
    redis_client: redis.Redis = Depends(get_redis),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> StreamingResponse:
    return await _create_messaging_sse_response(
        principal=MessagingRealtimePrincipal(principal_type="customer", principal_id=str(customer_account_id)),
        redis_client=redis_client,
    )


@customer_router.get("/realtime/sync", response_model=MessagingRealtimeSyncResponse)
async def sync_customer_realtime(
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    customer_account_id: UUID = Depends(get_current_mobile_user_id),
) -> MessagingRealtimeSyncResponse:
    result = await _service(db).sync_customer_realtime(
        customer_account_id=customer_account_id,
        cursor=cursor,
        limit=limit,
    )
    return MessagingRealtimeSyncResponse(
        cursor=result.cursor,
        conversations=[_customer_summary_response(conversation) for conversation in result.conversations],
        notifications=[_notification_response(view.notification, view.delivery) for view in result.notifications],
        unread_counts=MessagingUnreadCountsResponse(
            conversations=result.unread_conversations,
            notifications=result.unread_notifications,
        ),
    )


@admin_router.post("/realtime/ticket", response_model=MessagingRealtimeTicketResponse)
async def create_admin_realtime_ticket(
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_READ)),
    redis_client: redis.Redis = Depends(get_redis),
) -> MessagingRealtimeTicketResponse:
    return await _create_realtime_ticket(
        redis_client=redis_client,
        user_id=str(current_user.id),
        role=current_user.role,
        login=current_user.login,
        request=request,
        principal_type="admin",
    )


@admin_router.websocket("/realtime/ws")
async def admin_realtime_ws(
    websocket: WebSocket,
    principal: MessagingRealtimePrincipal = Depends(admin_messaging_ws_authenticate),
    redis_client: redis.Redis = Depends(get_redis),
) -> None:
    await _serve_messaging_ws(websocket=websocket, principal=principal, redis_client=redis_client)


@admin_router.get("/realtime/sse")
async def admin_realtime_sse(
    redis_client: redis.Redis = Depends(get_redis),
    current_user: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_READ)),
) -> StreamingResponse:
    return await _create_messaging_sse_response(
        principal=MessagingRealtimePrincipal(principal_type="admin", principal_id=str(current_user.id)),
        redis_client=redis_client,
    )


@admin_router.get("/conversations", response_model=AdminConversationListResponse)
async def list_admin_conversations(
    conversation_status: MessagingConversationStatus | None = Query(None, alias="status"),
    category: MessagingConversationCategory | None = None,
    priority: MessagingPriority | None = None,
    assigned_admin_id: UUID | None = None,
    customer_account_id: UUID | None = None,
    query: str | None = Query(None, min_length=1, max_length=120),
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_READ)),
) -> AdminConversationListResponse:
    result = await _service(db).list_admin_conversations(
        status=conversation_status,
        category=category,
        priority=priority,
        assigned_admin_id=assigned_admin_id,
        customer_account_id=customer_account_id,
        query=query,
        cursor=cursor,
        limit=limit,
    )
    return AdminConversationListResponse(
        conversations=[_admin_summary_response(conversation) for conversation in result.conversations],
        next_cursor=result.next_cursor,
    )


@admin_router.post(
    "/conversations",
    response_model=AdminConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_conversation(
    payload: AdminCreateConversationRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_CREATE)),
) -> AdminConversationDetailResponse:
    try:
        conversation = await _service(db).create_admin_conversation(
            admin_id=current_user.id,
            customer_account_id=payload.customer_account_id,
            subject=payload.subject,
            category=payload.category,
            priority=payload.priority,
            assigned_admin_id=payload.assigned_admin_id,
            related_support_ticket_id=payload.related_support_ticket_id,
            initial_message_body=payload.initial_message.body,
            initial_message_client_id=payload.initial_message.client_message_id,
            header_idempotency_key=idempotency_key,
        )
    except Exception as exc:
        _raise_http(exc)
    return _admin_detail_response(conversation)


@admin_router.get("/conversations/{conversation_id}", response_model=AdminConversationDetailResponse)
async def get_admin_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_READ)),
) -> AdminConversationDetailResponse:
    try:
        conversation = await _service(db).get_admin_conversation(conversation_ref=conversation_id)
    except Exception as exc:
        _raise_http(exc)
    return _admin_detail_response(conversation)


@admin_router.post("/conversations/{conversation_id}/messages", response_model=MessagingMessageWriteResponse)
async def add_admin_message(
    conversation_id: str,
    payload: MessagingWriteRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MESSAGING_MESSAGE_WRITE)),
) -> MessagingMessageWriteResponse:
    try:
        result = await _service(db).add_admin_message(
            conversation_ref=conversation_id,
            admin_id=current_user.id,
            body=payload.body,
            client_message_id=payload.client_message_id,
            header_idempotency_key=idempotency_key,
            visibility=MessagingMessageVisibility.PUBLIC,
        )
    except Exception as exc:
        _raise_http(exc)
    return MessagingMessageWriteResponse(
        message=_message_response(result.message),
        conversation=_admin_summary_response(result.conversation),
        created=result.created,
    )


@admin_router.post("/conversations/{conversation_id}/internal-notes", response_model=MessagingMessageWriteResponse)
async def add_admin_internal_note(
    conversation_id: str,
    payload: MessagingWriteRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.MESSAGING_INTERNAL_NOTE_WRITE)),
) -> MessagingMessageWriteResponse:
    try:
        result = await _service(db).add_admin_message(
            conversation_ref=conversation_id,
            admin_id=current_user.id,
            body=payload.body,
            client_message_id=payload.client_message_id,
            header_idempotency_key=idempotency_key,
            visibility=MessagingMessageVisibility.INTERNAL,
        )
    except Exception as exc:
        _raise_http(exc)
    return MessagingMessageWriteResponse(
        message=_message_response(result.message),
        conversation=_admin_summary_response(result.conversation),
        created=result.created,
    )


@admin_router.patch("/conversations/{conversation_id}", response_model=AdminConversationDetailResponse)
async def update_admin_conversation(
    conversation_id: str,
    payload: AdminConversationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_ASSIGN)),
) -> AdminConversationDetailResponse:
    try:
        conversation = await _service(db).update_admin_conversation(
            conversation_ref=conversation_id,
            update=AdminMessagingConversationUpdate(
                category=payload.category,
                priority=payload.priority,
                assigned_admin_id=payload.assigned_admin_id,
                assigned_admin_id_set="assigned_admin_id" in payload.model_fields_set,
            ),
        )
    except Exception as exc:
        _raise_http(exc)
    return _admin_detail_response(conversation)


@admin_router.post("/conversations/{conversation_id}/close", response_model=AdminConversationDetailResponse)
async def close_admin_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_CLOSE)),
) -> AdminConversationDetailResponse:
    try:
        conversation = await _service(db).close_admin_conversation(conversation_ref=conversation_id)
    except Exception as exc:
        _raise_http(exc)
    return _admin_detail_response(conversation)


@admin_router.post("/conversations/{conversation_id}/reopen", response_model=AdminConversationDetailResponse)
async def reopen_admin_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_permission(Permission.MESSAGING_CONVERSATION_CLOSE)),
) -> AdminConversationDetailResponse:
    try:
        conversation = await _service(db).reopen_admin_conversation(conversation_ref=conversation_id)
    except Exception as exc:
        _raise_http(exc)
    return _admin_detail_response(conversation)


@admin_notifications_router.post(
    "/broadcasts",
    response_model=BroadcastCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_notification_broadcast(
    payload: BroadcastCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.NOTIFICATION_BROADCAST_CREATE)),
) -> BroadcastCampaignResponse:
    try:
        campaign = await _service(db).create_broadcast_campaign(
            admin_id=current_user.id,
            name=payload.name,
            audience_type=payload.audience_type,
            audience_filter=payload.audience_filter,
            title=payload.title,
            body=payload.body,
            action_url=payload.action_url,
            scheduled_at=payload.scheduled_at,
        )
    except Exception as exc:
        _raise_http(exc)
    return _broadcast_response(campaign)


@admin_notifications_router.post(
    "/broadcasts/{campaign_id}/cancel",
    response_model=BroadcastCampaignResponse,
)
async def cancel_admin_notification_broadcast(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_permission(Permission.NOTIFICATION_BROADCAST_CREATE)),
) -> BroadcastCampaignResponse:
    try:
        campaign = await _service(db).cancel_broadcast_campaign(
            admin_id=current_user.id,
            campaign_ref=campaign_id,
        )
    except Exception as exc:
        _raise_http(exc)
    return _broadcast_response(campaign)


router.include_router(customer_router)
router.include_router(admin_router)
router.include_router(admin_notifications_router)
