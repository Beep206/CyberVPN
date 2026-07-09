import json
from collections.abc import Iterable

from starlette.types import Message, Scope

from src.presentation.middleware.request_body_limit import RequestBodyLimitMiddleware


class _BodyCaptureApp:
    def __init__(self) -> None:
        self.called = False
        self.body = b""

    async def __call__(self, scope: Scope, receive, send) -> None:
        self.called = True
        chunks: list[bytes] = []

        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            if isinstance(chunk, bytes):
                chunks.append(chunk)
            if not message.get("more_body", False):
                break

        self.body = b"".join(chunks)
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"size": len(self.body)}).encode("utf-8"),
                "more_body": False,
            }
        )


def _scope(*, headers: Iterable[tuple[bytes, bytes]] = (), method: str = "POST") -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": "/echo",
        "raw_path": b"/echo",
        "query_string": b"",
        "headers": list(headers),
        "client": ("203.0.113.10", 52344),
        "server": ("testserver", 443),
    }


async def _call(
    app,
    *,
    scope: Scope,
    messages: Iterable[Message] = (),
) -> tuple[list[Message], int]:
    sent: list[Message] = []
    receive_calls = 0
    message_iter = iter(messages)

    async def receive() -> Message:
        nonlocal receive_calls
        receive_calls += 1
        try:
            return next(message_iter)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    await app(scope, receive, send)
    return sent, receive_calls


def _status(messages: list[Message]) -> int:
    for message in messages:
        if message["type"] == "http.response.start":
            status = message["status"]
            assert isinstance(status, int)
            return status
    raise AssertionError("response start was not sent")


def _json_body(messages: list[Message]) -> dict:
    body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return json.loads(body)


async def test_content_length_over_limit_rejects_before_route_or_receive() -> None:
    inner_app = _BodyCaptureApp()
    app = RequestBodyLimitMiddleware(inner_app, max_body_bytes=8)

    sent, receive_calls = await _call(
        app,
        scope=_scope(headers=[(b"content-length", b"9")]),
    )

    assert _status(sent) == 413
    assert _json_body(sent)["detail"]["code"] == "REQUEST_BODY_TOO_LARGE"
    assert receive_calls == 0
    assert inner_app.called is False


async def test_chunked_body_without_content_length_is_rejected_before_route() -> None:
    inner_app = _BodyCaptureApp()
    app = RequestBodyLimitMiddleware(inner_app, max_body_bytes=8)

    sent, _receive_calls = await _call(
        app,
        scope=_scope(headers=[(b"transfer-encoding", b"chunked")]),
        messages=[
            {"type": "http.request", "body": b"abcd", "more_body": True},
            {"type": "http.request", "body": b"efghi", "more_body": False},
        ],
    )

    assert _status(sent) == 413
    assert _json_body(sent)["detail"] == {
        "code": "REQUEST_BODY_TOO_LARGE",
        "message": "Request body is too large.",
        "max_body_bytes": 8,
    }
    assert inner_app.called is False


async def test_body_within_limit_is_replayed_to_downstream_app() -> None:
    inner_app = _BodyCaptureApp()
    app = RequestBodyLimitMiddleware(inner_app, max_body_bytes=8)

    sent, _receive_calls = await _call(
        app,
        scope=_scope(headers=[(b"transfer-encoding", b"chunked")]),
        messages=[
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.request", "body": b"de", "more_body": False},
        ],
    )

    assert _status(sent) == 200
    assert _json_body(sent) == {"size": 5}
    assert inner_app.called is True
    assert inner_app.body == b"abcde"


async def test_malformed_content_length_is_rejected_before_route() -> None:
    inner_app = _BodyCaptureApp()
    app = RequestBodyLimitMiddleware(inner_app, max_body_bytes=8)

    sent, receive_calls = await _call(
        app,
        scope=_scope(headers=[(b"content-length", b"not-a-number")]),
    )

    assert _status(sent) == 400
    assert _json_body(sent)["detail"]["code"] == "MALFORMED_CONTENT_LENGTH"
    assert receive_calls == 0
    assert inner_app.called is False
