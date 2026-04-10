"""Starlette 1.0-compatible HTTP Prometheus metrics.

This replaces ``prometheus-fastapi-instrumentator`` while preserving the
metric names already used by tests, dashboards, and Prometheus rules.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from http import HTTPStatus
from timeit import default_timer

from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Gauge, Histogram, Summary, generate_latest
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Mount, Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of requests by method, status and handler.",
    ("method", "status", "handler"),
    registry=REGISTRY,
)

HTTP_REQUEST_SIZE_BYTES = Summary(
    "http_request_size_bytes",
    (
        "Content length of incoming requests by handler. "
        "Only value of header is respected. Otherwise ignored. "
        "No percentile calculated. "
    ),
    ("handler",),
    registry=REGISTRY,
)

HTTP_RESPONSE_SIZE_BYTES = Summary(
    "http_response_size_bytes",
    (
        "Content length of outgoing responses by handler. "
        "Only value of header is respected. Otherwise ignored. "
        "No percentile calculated. "
    ),
    ("handler",),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_HIGHR_SECONDS = Histogram(
    "http_request_duration_highr_seconds",
    "Latency with many buckets but no API specific labels. Made for more accurate percentile calculations. ",
    buckets=(
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1,
        1.5,
        2,
        2.5,
        3,
        3.5,
        4,
        4.5,
        5,
        7.5,
        10,
        30,
        60,
        float("inf"),
    ),
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Latency with only few buckets by handler. Made to be only used if aggregation by handler is important. ",
    ("method", "handler"),
    buckets=(0.1, 0.5, 1, float("inf")),
    registry=REGISTRY,
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress.",
    ("method", "handler"),
    multiprocess_mode="livesum",
    registry=REGISTRY,
)


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _get_route_name(scope: Scope, routes: Sequence[Route], route_name: str | None = None) -> str | None:
    for route in routes:
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            route_name = route.path
            child_scope = {**scope, **child_scope}
            if isinstance(route, Mount) and route.routes:
                child_route_name = _get_route_name(child_scope, route.routes, route_name)
                if child_route_name is None:
                    route_name = None
                else:
                    route_name += child_route_name
            return route_name
        if match == Match.PARTIAL and route_name is None:
            route_name = route.path
    return None


def get_route_name(request: Request) -> str | None:
    app = request.app
    scope = request.scope
    route_name = _get_route_name(scope, app.routes)

    if not route_name and app.router.redirect_slashes and scope["path"] != "/":
        redirect_scope = dict(scope)
        if scope["path"].endswith("/"):
            redirect_scope["path"] = scope["path"][:-1]
            trim = True
        else:
            redirect_scope["path"] = scope["path"] + "/"
            trim = False

        route_name = _get_route_name(redirect_scope, app.routes)
        if route_name is not None:
            route_name = route_name + "/" if trim else route_name[:-1]

    return route_name


class HTTPMetricsMiddleware:
    """Pure ASGI middleware that preserves existing Prometheus HTTP metric names."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        excluded_handlers: Sequence[str] = (),
        enabled: bool | None = None,
        env_var_name: str = "ENABLE_METRICS",
    ) -> None:
        self.app = app
        self._enabled = _env_enabled(env_var_name) if enabled is None else enabled
        self._excluded_handlers = [re.compile(path) for path in excluded_handlers]

    def _is_excluded(self, handler: str, *, templated: bool) -> bool:
        if not templated:
            return False
        return any(pattern.search(handler) for pattern in self._excluded_handlers)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._enabled:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        start_time = default_timer()

        route_name = get_route_name(request)
        is_templated = route_name is not None
        handler = route_name or request.url.path
        is_excluded = self._is_excluded(handler, templated=is_templated)
        modified_handler = handler if is_templated else "none"

        if not is_excluded:
            HTTP_REQUESTS_IN_PROGRESS.labels(request.method, modified_handler).inc()

        status_code = 500
        response_headers: list[tuple[bytes, bytes]] = []
        response_body_size = 0
        response_start_time: float | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_body_size, response_headers, response_start_time

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = list(message["headers"])
                response_start_time = default_timer()
            elif message["type"] == "http.response.body":
                response_body_size += len(message.get("body", b""))

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            if not is_excluded:
                HTTP_REQUESTS_IN_PROGRESS.labels(request.method, modified_handler).dec()

                duration = max(default_timer() - start_time, 0.0)
                duration_without_streaming = duration
                if response_start_time is not None:
                    duration_without_streaming = max(response_start_time - start_time, 0.0)

                normalized_status = (
                    str(status_code.value) if isinstance(status_code, HTTPStatus) else str(status_code)
                )
                normalized_status = f"{normalized_status[0]}xx"

                response = Response(content=b"", headers=Headers(raw=response_headers), status_code=status_code)

                request_size = int(request.headers.get("content-length", 0) or 0)
                response_size_header = response.headers.get("content-length")
                response_size = int(response_size_header) if response_size_header else response_body_size

                HTTP_REQUESTS_TOTAL.labels(request.method, normalized_status, modified_handler).inc()
                HTTP_REQUEST_SIZE_BYTES.labels(modified_handler).observe(request_size)
                HTTP_RESPONSE_SIZE_BYTES.labels(modified_handler).observe(response_size)
                HTTP_REQUEST_DURATION_HIGHR_SECONDS.observe(duration)
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    request.method,
                    modified_handler,
                ).observe(duration_without_streaming)


def build_metrics_response() -> Response:
    """Render the default Prometheus registry without mount redirects."""
    payload = generate_latest(REGISTRY)
    return Response(
        content=payload,
        headers={
            "Content-Type": CONTENT_TYPE_LATEST,
            "Content-Length": str(len(payload)),
        },
    )


def add_http_metrics_middleware(
    app: Starlette,
    *,
    excluded_handlers: Sequence[str],
    enabled: bool | None = None,
    env_var_name: str = "ENABLE_METRICS",
) -> None:
    app.add_middleware(
        HTTPMetricsMiddleware,
        excluded_handlers=excluded_handlers,
        enabled=enabled,
        env_var_name=env_var_name,
    )
