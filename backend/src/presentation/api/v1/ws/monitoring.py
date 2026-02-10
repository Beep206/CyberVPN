"""WebSocket monitoring with topic authorization (HIGH-2).

Security improvements:
- Role-based topic authorization
- Audit logging for unauthorized subscription attempts
- Error messages sent via WebSocket for failed subscriptions
"""

import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.application.services.ws_topic_authorization import WSTopicAuthorizationService
from src.infrastructure.messaging.websocket_manager import ws_manager

from .auth import WSUserContext, ws_authenticate
from .schemas import WSSubscribeMessage

logger = logging.getLogger("cybervpn.ws")

router = APIRouter(tags=["websocket"])

# Authorization service instance
topic_auth = WSTopicAuthorizationService()


async def _send_error(websocket: WebSocket, message: str, topic: str | None = None) -> None:
    """Send error message to WebSocket client."""
    error_payload = {
        "type": "error",
        "message": message,
    }
    if topic:
        error_payload["topic"] = topic
    await websocket.send_json(error_payload)


async def _subscribe_with_auth(
    websocket: WebSocket,
    user_ctx: WSUserContext,
    topic: str,
) -> bool:
    """Subscribe to topic with authorization check.

    Args:
        websocket: The WebSocket connection
        user_ctx: User context with ID and role
        topic: Topic to subscribe to (without 'monitoring:' prefix)

    Returns:
        True if subscription succeeded, False otherwise
    """
    authorized, error = topic_auth.authorize_subscription(
        user_id=user_ctx.user_id,
        role=user_ctx.role,
        topic=topic,
    )

    if not authorized:
        await _send_error(websocket, error or "Unauthorized", topic)
        return False

    await ws_manager.connect(websocket, f"monitoring:{topic}")

    # Send subscription confirmation
    await websocket.send_json(
        {
            "type": "subscribed",
            "topic": topic,
        }
    )

    return True


@router.websocket("/ws/monitoring")
async def monitoring_ws(
    websocket: WebSocket,
    user_ctx: WSUserContext = Depends(ws_authenticate),
):
    """Real-time monitoring WebSocket. Requires ?token=JWT query parameter.

    Topics:
    - servers: Server status and metrics (ADMIN, SUPER_ADMIN, OPERATOR)
    - users: User activity (SUPER_ADMIN only)
    - system: System metrics (SUPER_ADMIN only)
    - payments: Payment notifications (ADMIN, SUPER_ADMIN)
    - general: General notifications (all authenticated users)

    Messages:
    - Subscribe: {"type": "subscribe", "topics": ["servers", "users"]}
    - Unsubscribe: {"type": "unsubscribe", "topics": ["servers"]}

    Errors:
    - {"type": "error", "message": "...", "topic": "..."}

    On connect, sends available topics for user's role:
    - {"type": "available_topics", "topics": [...]}
    """
    await ws_manager.connect(websocket, "monitoring")

    # Send available topics for this user's role
    available = topic_auth.get_allowed_topics(user_ctx.role)
    await websocket.send_json(
        {
            "type": "available_topics",
            "topics": available,
            "role": user_ctx.role.value,
        }
    )

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = WSSubscribeMessage.model_validate_json(data)
                for topic in message.topics:
                    await _subscribe_with_auth(websocket, user_ctx, topic)
            except ValidationError:
                # Try raw JSON parsing for backwards compatibility
                try:
                    raw = json.loads(data)
                    msg_type = raw.get("type")

                    if msg_type == "subscribe":
                        topics = raw.get("topics", [])
                        for topic in topics:
                            if isinstance(topic, str):
                                await _subscribe_with_auth(websocket, user_ctx, topic)

                    elif msg_type == "unsubscribe":
                        topics = raw.get("topics", [])
                        for topic in topics:
                            if isinstance(topic, str):
                                ws_manager.disconnect(websocket, f"monitoring:{topic}")
                                await websocket.send_json(
                                    {
                                        "type": "unsubscribed",
                                        "topic": topic,
                                    }
                                )

                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

                    else:
                        await _send_error(websocket, f"Unknown message type: {msg_type}")

                except json.JSONDecodeError:
                    await _send_error(websocket, "Invalid JSON message")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "monitoring")
        logger.info(
            "WebSocket disconnected",
            extra={"user_id": user_ctx.user_id},
        )
