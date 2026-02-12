import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.application.services.auth_service import AuthService

logger = logging.getLogger(__name__)

auth_service = AuthService()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user = None
        request.state.user_id = None
        request.state.role = None

        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = auth_service.decode_token(token)
                if payload.get("type") == "access":
                    request.state.user_id = payload.get("sub")
                    request.state.role = payload.get("role")
            except Exception as e:
                logger.warning("Auth middleware token decode failed: %s", e)

        return await call_next(request)
