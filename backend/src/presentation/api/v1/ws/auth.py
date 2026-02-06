"""WebSocket authentication and authorization (HIGH-2, HIGH-3).

Security improvements:
- Returns user context including role for authorization
- Supports ticket-based authentication (HIGH-3) - preferred
- Falls back to token-based for backwards compatibility

Deprecation notice (LOW-006):
- Token-based authentication is DEPRECATED and will be removed in v2.0 (Q3 2026)
- Use ticket-based authentication via POST /api/v1/ws/ticket instead
- Tokens in URLs appear in server logs, browser history, and proxy logs
"""

import logging
import warnings
from dataclasses import dataclass

from fastapi import Depends, Query, WebSocket, WebSocketException, status
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_service import AuthService
from src.application.services.ws_ticket_service import WebSocketTicketService
from src.domain.enums.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.monitoring.metrics import websocket_auth_method_total
from src.presentation.dependencies.database import get_db

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# LOW-006: Deprecation notice for token-based WebSocket authentication
_TOKEN_AUTH_DEPRECATION_MSG = (
    "WebSocket token-based authentication is DEPRECATED and will be removed in v2.0 (Q3 2026). "
    "Use ticket-based authentication via POST /api/v1/ws/ticket instead. "
    "Tokens in URLs appear in server logs, browser history, and proxy logs."
)

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

    This is the recommended authentication method for WebSocket connections.
    Tickets are single-use, short-lived, and don't expose credentials in URLs.

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

    # LOW-006: Track preferred auth method usage
    websocket_auth_method_total.labels(method="ticket").inc()

    return WSUserContext(
        user_id=ticket_data.user_id,
        role=role,
        login=ticket_data.login,
    )


async def ws_authenticate_token(
    token: str | None,
    db: AsyncSession,
) -> WSUserContext | None:
    """Authenticate WebSocket via JWT token (DEPRECATED fallback method).

    .. deprecated:: 1.0
        Token-based WebSocket authentication is deprecated and will be removed
        in v2.0 (Q3 2026). Use ticket-based authentication via
        POST /api/v1/ws/ticket instead.

    WARNING: Token in URL will appear in server logs, browser history,
    and proxy logs. This is a security concern.

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

        # LOW-006: Emit deprecation warning
        warnings.warn(_TOKEN_AUTH_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)

        # LOW-006: Log deprecation with structured data for monitoring
        logger.warning(
            "DEPRECATED: WebSocket token-based authentication used. "
            "This method will be removed in v2.0 (Q3 2026). "
            "Migrate to ticket-based auth via POST /api/v1/ws/ticket.",
            extra={
                "user_id": user_id,
                "auth_method": "token",
                "deprecation_removal_version": "v2.0",
                "deprecation_removal_date": "Q3 2026",
            },
        )

        # LOW-006: Track deprecated auth method usage
        websocket_auth_method_total.labels(method="token").inc()

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
