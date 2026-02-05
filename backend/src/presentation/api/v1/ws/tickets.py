"""WebSocket ticket endpoints (HIGH-3).

Provides ticket-based WebSocket authentication:
1. Client requests single-use ticket via POST /api/v1/ws/ticket
2. WebSocket connects with ?ticket=<uuid> instead of JWT
3. JWT never appears in WebSocket URL (which gets logged)
"""

import logging

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request

from src.application.services.ws_ticket_service import WebSocketTicketService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.auth import get_current_active_user

from .schemas import WSTicketResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.post(
    "/ticket",
    response_model=WSTicketResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def create_ws_ticket(
    request: Request,
    current_user: AdminUserModel = Depends(get_current_active_user),
    redis_client: redis.Redis = Depends(get_redis),
) -> WSTicketResponse:
    """Create a single-use WebSocket authentication ticket.

    The ticket:
    - Is valid for 30 seconds
    - Can only be used once
    - Contains user context (ID, role)
    - Should be used as ?ticket=<uuid> when connecting to WebSocket

    This prevents JWT tokens from appearing in WebSocket URLs,
    which would be logged by servers and proxies.
    """
    # Get client IP for ticket binding
    client_ip = None
    if request.client:
        client_ip = request.client.host

    ticket_service = WebSocketTicketService(redis_client)
    ticket_id = await ticket_service.create_ticket(
        user_id=str(current_user.id),
        role=current_user.role,
        login=current_user.login,
        ip_address=client_ip,
    )

    return WSTicketResponse(
        ticket=ticket_id,
        expires_in=30,
    )
