"""Stage 1 route-boundary regression checks.

The goal is not to prove every endpoint's business authorization. It prevents
new routes from silently appearing without being classified as public,
principal-protected, webhook/signature-protected, or internal-token-protected.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, APIWebSocketRoute

from src.main import app

PRINCIPAL_DEPENDENCIES = {
    "role_checker",
    "permission_checker",
    "get_current_active_user",
    "get_current_active_web_user",
    "get_current_user",
    "get_current_web_user",
    "get_current_mobile_user_id",
    "get_current_principal_actor",
    "get_current_pending_mobile_2fa_context",
    "get_current_pending_2fa_user",
}

PUBLIC_EXACT_PATHS = {
    "/.well-known/security.txt",
    "/security.txt",
    "/health",
    "/readiness",
    "/api/v1/status",
    "/api/v1/client-errors/miniapp",
    "/api/v1/client/capabilities",
    "/api/v1/runtime/fingerprint",
    "/api/v3/growth/code-sets/preflight",
}

PUBLIC_GET_EXACT_PATHS = {
    "/api/v1/legal-documents",
    "/api/v1/legal-documents/",
}

SUBSCRIPTION_TOKEN_GET_EXACT_PATHS = {
    "/api/sub/{short_uuid}",
}

PUBLIC_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/mobile/auth",
    "/api/v1/oauth",
    "/api/v1/partner-attribution",
    "/api/v1/plans",
    "/api/v1/addons/catalog",
    "/api/v1/catalog",
    "/api/v1/offers",
    "/api/v1/pricebooks/resolve",
    "/api/v1/program-eligibility",
    "/api/v1/merchant-profiles/resolve",
    "/api/v1/billing-descriptors/resolve",
    "/api/v1/legal-documents/sets/resolve",
    "/api/v1/realms/resolve",
    "/api/v1/referral/attribution",
    "/api/v1/public/network",
    "/api/v1/storefronts",
)

WEBSOCKET_AUTH_DEPENDENCIES = {
    "ws_authenticate",
    "customer_messaging_ws_authenticate",
    "admin_messaging_ws_authenticate",
}


@dataclass(frozen=True)
class RouteBoundary:
    path: str
    methods: frozenset[str]
    dependency_names: set[str]
    source: str


@dataclass(frozen=True)
class WebSocketBoundary:
    path: str
    dependency_names: set[str]


def _dependency_names(dependencies: Iterable[Dependant]) -> set[str]:
    names: set[str] = set()
    pending = list(dependencies)
    while pending:
        dependency = pending.pop()
        names.add(getattr(dependency.call, "__name__", repr(dependency.call)))
        pending.extend(dependency.dependencies)
    return names


def _route_dependency_names(route: APIRoute) -> set[str]:
    return _dependency_names(route.dependant.dependencies)


def _websocket_dependency_names(route: APIWebSocketRoute) -> set[str]:
    return _dependency_names(route.dependant.dependencies)


def _endpoint_source(endpoint: object) -> str:
    try:
        return inspect.getsource(endpoint)
    except OSError:
        return ""


def _route_boundary(
    route: APIRoute,
    *,
    path: str | None = None,
    dependant: Dependant | None = None,
    endpoint: object | None = None,
    methods: Iterable[str] | None = None,
) -> RouteBoundary:
    route_dependant = dependant or route.dependant
    route_endpoint = endpoint or route.endpoint
    route_methods = methods or route.methods or ()
    return RouteBoundary(
        path=path or route.path,
        methods=frozenset(str(method) for method in route_methods),
        dependency_names=_dependency_names(route_dependant.dependencies),
        source=_endpoint_source(route_endpoint),
    )


def _iter_route_boundaries() -> Iterable[RouteBoundary]:
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield _route_boundary(route)
            continue

        effective_route_contexts = getattr(route, "effective_route_contexts", None)
        if effective_route_contexts is None:
            continue

        for context in effective_route_contexts():
            original_route = getattr(context, "original_route", None)
            if not isinstance(original_route, APIRoute):
                continue
            context_dependant = getattr(context, "dependant", None)
            context_path = getattr(context, "path_format", "") or getattr(context, "path", "") or original_route.path
            yield _route_boundary(
                original_route,
                path=context_path,
                dependant=context_dependant if isinstance(context_dependant, Dependant) else None,
                endpoint=getattr(context, "endpoint", None),
                methods=getattr(context, "methods", None),
            )


def _iter_websocket_boundaries() -> Iterable[WebSocketBoundary]:
    for route in app.routes:
        if isinstance(route, APIWebSocketRoute):
            yield WebSocketBoundary(
                path=route.path,
                dependency_names=_websocket_dependency_names(route),
            )
            continue

        effective_route_contexts = getattr(route, "effective_route_contexts", None)
        if effective_route_contexts is None:
            continue

        for context in effective_route_contexts():
            context_route = getattr(context, "starlette_route", None) or getattr(context, "original_route", None)
            if not isinstance(context_route, APIWebSocketRoute):
                continue
            context_path = getattr(context_route, "path", None) or getattr(context, "path_format", "") or ""
            yield WebSocketBoundary(
                path=context_path,
                dependency_names=_websocket_dependency_names(context_route),
            )


def classify_route_boundary(route: RouteBoundary) -> str:
    dependency_names = route.dependency_names
    source = route.source

    if dependency_names & PRINCIPAL_DEPENDENCIES:
        return "principal-protected"
    if "require_partner_reporting_token" in dependency_names:
        return "partner-reporting-token"
    if (
        "_require_telegram_bot_secret" in source
        or "_require_frontend_observability_secret" in source
        or "_require_payment_settlement_worker_secret" in source
        or "_require_backend_internal_secret" in source
        or "_require_task2_xray_webhook_secret" in source
    ):
        return "header-secret-protected"
    if "_resolve_customer_onboarding_actor" in source:
        return "principal-protected"
    if route.path.startswith("/api/v1/webhooks") and ("signature" in source or "webhook_secret" in source):
        return "webhook-signature-protected"
    if route.path in SUBSCRIPTION_TOKEN_GET_EXACT_PATHS and route.methods <= {"GET", "HEAD"}:
        return "subscription-token-protected"
    if route.path in PUBLIC_GET_EXACT_PATHS and route.methods <= {"GET", "HEAD"}:
        return "public-allowlisted"
    if route.path in PUBLIC_EXACT_PATHS or any(route.path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return "public-allowlisted"
    return "needs-review"


def test_stage1_routes_have_explicit_boundary_classification():
    unclassified = [
        f"{','.join(sorted(route.methods))} {route.path}"
        for route in _iter_route_boundaries()
        if classify_route_boundary(route) == "needs-review"
    ]

    assert unclassified == []


def test_stage1_internal_routes_are_not_public_allowlisted():
    internal_public = [
        f"{','.join(sorted(route.methods))} {route.path}"
        for route in _iter_route_boundaries()
        if "/internal/" in route.path and classify_route_boundary(route) == "public-allowlisted"
    ]

    assert internal_public == []


def test_stage1_route_boundary_expected_categories_exist():
    categories = {classify_route_boundary(route) for route in _iter_route_boundaries()}

    assert categories == {
        "header-secret-protected",
        "partner-reporting-token",
        "principal-protected",
        "public-allowlisted",
        "subscription-token-protected",
        "webhook-signature-protected",
    }


def test_stage1_subscription_gateway_is_token_protected():
    subscription_routes = [
        route for route in _iter_route_boundaries() if route.path in SUBSCRIPTION_TOKEN_GET_EXACT_PATHS
    ]

    assert len(subscription_routes) == 1
    assert subscription_routes[0].methods <= {"GET", "HEAD"}
    assert classify_route_boundary(subscription_routes[0]) == "subscription-token-protected"


def test_stage1_websocket_routes_depend_on_ws_authenticate():
    unauthenticated_websockets = [
        route.path
        for route in _iter_websocket_boundaries()
        if not (route.dependency_names & WEBSOCKET_AUTH_DEPENDENCIES)
    ]

    assert unauthenticated_websockets == []
