"""Bound untrusted HTTP request bodies before route processing."""

from __future__ import annotations

from collections.abc import Iterable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_METHODS_WITH_BODIES = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_LIMIT_RESPONSE_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "X-Content-Type-Options": "nosniff",
}


class RequestBodyLimitMiddleware:
    """Reject oversized or malformed HTTP request bodies at the ASGI boundary."""

    def __init__(self, app: ASGIApp, *, max_body_bytes: int, enabled: bool = True) -> None:
        self.app = app
        self.max_body_bytes = max(1, int(max_body_bytes))
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        method = str(scope.get("method", "GET")).upper()
        if method not in _METHODS_WITH_BODIES and not _declares_request_body(headers):
            await self.app(scope, receive, send)
            return

        content_length = headers.get("content-length")
        if content_length is not None:
            parsed_length = _parse_content_length(content_length)
            if parsed_length is None:
                await _send_malformed_content_length(scope, receive, send)
                return
            if parsed_length > self.max_body_bytes:
                await _send_payload_too_large(scope, receive, send, max_body_bytes=self.max_body_bytes)
                return

        buffered_messages: list[Message] = []
        total_body_bytes = 0

        while True:
            message = await receive()
            buffered_messages.append(message)

            if message["type"] != "http.request":
                break

            chunk = message.get("body", b"")
            if isinstance(chunk, bytes):
                total_body_bytes += len(chunk)
            if total_body_bytes > self.max_body_bytes:
                await _send_payload_too_large(scope, receive, send, max_body_bytes=self.max_body_bytes)
                return

            if not message.get("more_body", False):
                break

        replay_receive = _ReplayReceive(buffered_messages)
        await self.app(scope, replay_receive, send)


class _ReplayReceive:
    def __init__(self, messages: Iterable[Message]) -> None:
        self._messages = iter(messages)

    async def __call__(self) -> Message:
        try:
            return next(self._messages)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}


def _declares_request_body(headers: Headers) -> bool:
    content_length = headers.get("content-length")
    if content_length is not None and content_length.strip() not in {"", "0"}:
        return True
    return bool(headers.get("transfer-encoding"))


def _parse_content_length(value: str) -> int | None:
    try:
        parsed = int(value.strip())
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


async def _send_payload_too_large(scope: Scope, receive: Receive, send: Send, *, max_body_bytes: int) -> None:
    await JSONResponse(
        status_code=413,
        content={
            "detail": {
                "code": "REQUEST_BODY_TOO_LARGE",
                "message": "Request body is too large.",
                "max_body_bytes": max_body_bytes,
            }
        },
        headers=_LIMIT_RESPONSE_HEADERS,
    )(scope, receive, send)


async def _send_malformed_content_length(scope: Scope, receive: Receive, send: Send) -> None:
    await JSONResponse(
        status_code=400,
        content={
            "detail": {
                "code": "MALFORMED_CONTENT_LENGTH",
                "message": "Content-Length must be a non-negative integer.",
            }
        },
        headers=_LIMIT_RESPONSE_HEADERS,
    )(scope, receive, send)
