import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.infrastructure.messaging.websocket_manager import ws_manager

from .auth import ws_authenticate
from .schemas import WSSubscribeMessage

logger = logging.getLogger("cybervpn.ws")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/monitoring")
async def monitoring_ws(
    websocket: WebSocket,
    user_id: str = Depends(ws_authenticate),
):
    """Real-time monitoring WebSocket. Requires ?token=JWT query parameter."""
    await ws_manager.connect(websocket, "monitoring")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = WSSubscribeMessage.model_validate_json(data)
                for topic in message.topics:
                    await ws_manager.connect(websocket, f"monitoring:{topic}")
            except ValidationError:
                raw = json.loads(data)
                if raw.get("type") == "subscribe":
                    topics = raw.get("topics", [])
                    for topic in topics:
                        await ws_manager.connect(websocket, f"monitoring:{topic}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "monitoring")
