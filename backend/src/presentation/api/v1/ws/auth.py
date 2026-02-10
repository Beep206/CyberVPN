"""WebSocket authentication and authorization (HIGH-2, HIGH-3).

Security improvements:
- Returns user context including role for authorization
- Ticket-based authentication only (v2.0 — token auth removed)

v2.0 Breaking Change:
- Token-based authentication (?token=<jwt>) has been removed.
- All clients must use ticket-based authentication via POST /api/v1/ws/ticket.
"""

import logging
from dataclasses import dataclass

import redis.asyncio as redis
from fastapi import Depends, Query, WebSocket, WebSocketException, status

from src.application.services.ws_ticket_service import WebSocketTicketService
from src.domain.enums.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.monitoring.metrics import websocket_auth_method_total

logger = logging.getLogger(__name__)


@dataclass
class WSUserContext:
    """User context for WebSocket connections."""

    user_id: str
    role: AdminRole
    login: str | None = None


async def ws_authenticate_ticket(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    redis_client: redis.Redis = Depends(get_redis),
) -> WSUserContext | None:
    """Authenticate WebSocket via single-use ticket.

    Tickets are obtained from POST /api/v1/ws/ticket. They are single-use,
    short-lived, and IP-bound — credentials never appear in URLs.

    Args:
        websocket: The WebSocket connection
        ticket: Single-use ticket from POST /api/v1/ws/ticket
        redis_client: Redis client for ticket lookup

    Returns:
        User context if ticket valid, None otherwise
    """
    if not ticket:
        return None

    # Get client IP for validation
    client_ip = None
    if websocket.client:
        client_ip = websocket.client.host

    ticket_service = WebSocketTicketService(redis_client)
    ticket_data = await ticket_service.validate_and_consume(ticket, client_ip)

    if not ticket_data:
        return None

    # Convert role string to AdminRole enum
    try:
        role = AdminRole(ticket_data.role)
    except ValueError:
        role = AdminRole.VIEWER

    websocket_auth_method_total.labels(method="ticket").inc()

    return WSUserContext(
        user_id=ticket_data.user_id,
        role=role,
        login=ticket_data.login,
    )


async def ws_authenticate(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    redis_client: redis.Redis = Depends(get_redis),
) -> WSUserContext:
    """Authenticate WebSocket connection via ticket.

    Requires a single-use ticket obtained from POST /api/v1/ws/ticket.

    Args:
        websocket: The WebSocket connection
        ticket: Single-use ticket
        redis_client: Redis client

    Returns:
        User context with ID and role for authorization

    Raises:
        WebSocketException: If ticket is missing or invalid
    """
    if ticket:
        user_ctx = await ws_authenticate_ticket(websocket, ticket, redis_client)
        if user_ctx:
            return user_ctx
        logger.warning("WebSocket connection with invalid ticket")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    # No authentication provided
    logger.warning("WebSocket connection without authentication")
    raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
