from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.infrastructure.messaging.websocket_manager import ws_manager

from .auth import ws_authenticate

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/notifications")
async def notifications_ws(
    websocket: WebSocket,
    user_id: str = Depends(ws_authenticate),
):
    """Real-time notifications WebSocket. Requires ?token=JWT query parameter."""
    await ws_manager.connect(websocket, "notifications")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "notifications")
