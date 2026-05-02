from __future__ import annotations

import logging
from hmac import compare_digest
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-observability-secret",
}
SENSITIVE_FIELD_MARKERS = (
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "certificate",
    "private_key",
    "openbao",
    "opentofu",
    "nats",
)


def is_observability_authorized(configured_secret: str, provided_secret: str | None) -> bool:
    configured = configured_secret.strip()
    provided = (provided_secret or "").strip()
    if not configured or not provided:
        return False
    return compare_digest(configured, provided)


def _scrub_sensitive_mapping(payload: dict[str, Any]) -> None:
    for key, value in list(payload.items()):
        lowered_key = key.lower()
        if any(marker in lowered_key for marker in SENSITIVE_FIELD_MARKERS):
            payload[key] = "[Filtered]"
            continue

        if isinstance(value, dict):
            _scrub_sensitive_mapping(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _scrub_sensitive_mapping(item)


def _scrub_request_headers(headers: Any) -> None:
    if not isinstance(headers, dict):
        return

    for header_name in list(headers):
        if header_name.lower() in SENSITIVE_HEADER_NAMES:
            headers[header_name] = "[Filtered]"


def before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        _scrub_request_headers(request.get("headers"))
        if "data" in request:
            request["data"] = "[Filtered]"
        if "cookies" in request:
            request["cookies"] = "[Filtered]"

    user = event.get("user")
    if isinstance(user, dict):
        for key in ("ip_address", "email", "username"):
            user.pop(key, None)

    for section_name in ("extra", "contexts"):
        section = event.get(section_name)
        if isinstance(section, dict):
            _scrub_sensitive_mapping(section)

    return event


def before_send_transaction(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    request = event.get("request")
    if isinstance(request, dict):
        url = request.get("url")
        if isinstance(url, str):
            path = urlparse(url).path
            if path in {"/api/v1/health/live", "/api/v1/observability/sentry-contract"}:
                return None

    return event


def setup_sentry(settings) -> bool:
    dsn = settings.sentry_dsn.strip()
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        release=settings.sentry_release or None,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        in_app_include=["src"],
        traces_sample_rate=1.0 if settings.environment == "development" else 0.1,
        integrations=[
            StarletteIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={403, *range(500, 600)},
                middleware_spans=True,
            ),
            FastApiIntegration(
                transaction_style="endpoint",
                failed_request_status_codes={403, *range(500, 600)},
                middleware_spans=True,
            ),
        ],
        before_send=before_send,
        before_send_transaction=before_send_transaction,
    )
    sentry_sdk.set_tag("runtime_surface", "node-fleet-controller")
    sentry_sdk.set_tag("service.name", settings.service_name)
    logger.info(
        "Sentry SDK initialized for node fleet controller",
        extra={
            "environment": settings.environment,
            "release": settings.sentry_release or "",
        },
    )
    return True
