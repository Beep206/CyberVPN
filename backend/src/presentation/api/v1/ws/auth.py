"""WebSocket authentication dependency."""

from fastapi import Query, WebSocket, WebSocketException, status
from jwt.exceptions import PyJWTError as JWTError

from src.application.services.auth_service import AuthService

auth_service = AuthService()


async def ws_authenticate(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> str:
    """Authenticate WebSocket connection via query token parameter.

    Args:
        websocket: The WebSocket connection.
        token: JWT access token passed as query parameter.

    Returns:
        The authenticated user ID (sub claim).

    Raises:
        WebSocketException: If token is missing or invalid.
    """
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        payload = auth_service.decode_token(token)
        if payload.get("type") != "access":
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        user_id = payload.get("sub")
        if not user_id:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        return user_id
    except JWTError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
