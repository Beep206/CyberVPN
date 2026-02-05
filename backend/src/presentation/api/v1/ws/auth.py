"""WebSocket authentication and authorization (HIGH-2, HIGH-3).

Security improvements:
- Returns user context including role for authorization
- Supports ticket-based authentication (HIGH-3) - preferred
- Falls back to token-based for backwards compatibility
"""

import logging
from dataclasses import dataclass

from fastapi import Depends, Query, WebSocket, WebSocketException, status
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.ws_ticket_service import WebSocketTicketService
from src.domain.enums.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.presentation.dependencies.database import get_db

import redis.asyncio as redis

logger = logging.getLogger(__name__)

auth_service = AuthService()


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
    """Authenticate WebSocket via ticket (preferred method).

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

    return WSUserContext(
        user_id=ticket_data.user_id,
        role=role,
        login=ticket_data.login,
    )


async def ws_authenticate_token(
    token: str | None,
    db: AsyncSession,
) -> WSUserContext | None:
    """Authenticate WebSocket via JWT token (fallback method).

    WARNING: Token in URL will appear in server logs. Use ticket-based
    authentication when possible.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        User context if token valid, None otherwise
    """
    if not token:
        return None

    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        user_repo = AdminUserRepository(db)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            return None

        try:
            role = AdminRole(user.role)
        except ValueError:
            role = AdminRole.VIEWER

        logger.warning(
            "WebSocket authenticated via token - consider using ticket-based auth",
            extra={"user_id": user_id},
        )

        return WSUserContext(
            user_id=str(user.id),
            role=role,
            login=user.login,
        )

    except JWTError:
        return None


async def ws_authenticate(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> WSUserContext:
    """Authenticate WebSocket connection.

    Supports two authentication methods:
    1. Ticket-based (recommended): ?ticket=<uuid> from POST /api/v1/ws/ticket
    2. Token-based (legacy): ?token=<jwt> - WARNING: appears in logs

    Args:
        websocket: The WebSocket connection
        ticket: Single-use ticket (preferred)
        token: JWT access token (fallback)
        db: Database session
        redis_client: Redis client

    Returns:
        User context with ID and role for authorization

    Raises:
        WebSocketException: If neither ticket nor token is valid
    """
    # Try ticket-based authentication first (preferred)
    if ticket:
        user_ctx = await ws_authenticate_ticket(websocket, ticket, redis_client)
        if user_ctx:
            return user_ctx
        # Invalid ticket
        logger.warning("WebSocket connection with invalid ticket")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    # Fall back to token-based authentication
    if token:
        user_ctx = await ws_authenticate_token(token, db)
        if user_ctx:
            return user_ctx
        # Invalid token
        logger.warning("WebSocket connection with invalid token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    # No authentication provided
    logger.warning("WebSocket connection without authentication")
    raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
