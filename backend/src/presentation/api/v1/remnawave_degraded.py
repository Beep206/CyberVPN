"""Helpers for optional Remnawave admin read surfaces."""

import logging
from collections.abc import Awaitable, Callable

import httpx

from src.infrastructure.monitoring.metrics import route_operations_total

logger = logging.getLogger(__name__)

_OPTIONAL_UPSTREAM_UNAVAILABLE_STATUS_CODES = {404, 405, 410, 501, 502, 503, 504}


def is_optional_remnawave_read_unavailable(exc: Exception) -> bool:
    """Return true when an optional read-only Remnawave surface is unavailable."""

    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _OPTIONAL_UPSTREAM_UNAVAILABLE_STATUS_CODES
    return False


async def optional_remnawave_read[T](
    *,
    route: str,
    action: str,
    fetch: Callable[[], Awaitable[T]],
    fallback: T,
) -> T:
    """Run an optional Remnawave read and degrade to a safe empty response.

    Admin overview pages should remain usable when a local or older Remnawave
    panel lacks an optional read-only endpoint. Authorization, validation, and
    mutating failures are intentionally not handled here.
    """

    try:
        result = await fetch()
    except Exception as exc:
        if not is_optional_remnawave_read_unavailable(exc):
            raise
        logger.warning(
            "Optional Remnawave read degraded",
            extra={
                "route": route,
                "action": action,
                "error_type": type(exc).__name__,
                "status_code": exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None,
            },
        )
        route_operations_total.labels(route=route, action=action, status="degraded").inc()
        return fallback

    route_operations_total.labels(route=route, action=action, status="success").inc()
    return result
