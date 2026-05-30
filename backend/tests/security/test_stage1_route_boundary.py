"""Stage 1 route-boundary regression checks.

The goal is not to prove every endpoint's business authorization. It prevents
new routes from silently appearing without being classified as public,
principal-protected, webhook/signature-protected, or internal-token-protected.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable

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
    "/api/v1/client/capabilities",
}

PUBLIC_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/mobile/auth",
    "/api/v1/oauth",
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
    "/api/v1/public/network",
    "/api/v1/storefronts",
)


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


def _route_source(route: APIRoute) -> str:
    try:
        return inspect.getsource(route.endpoint)
    except OSError:
        return ""


def classify_route_boundary(route: APIRoute) -> str:
    dependency_names = _route_dependency_names(route)
    source = _route_source(route)

    if dependency_names & PRINCIPAL_DEPENDENCIES:
        return "principal-protected"
    if "require_partner_reporting_token" in dependency_names:
        return "partner-reporting-token"
    if "_require_telegram_bot_secret" in source or "_require_frontend_observability_secret" in source:
        return "header-secret-protected"
    if route.path.startswith("/api/v1/webhooks") and ("signature" in source or "webhook_secret" in source):
        return "webhook-signature-protected"
    if route.path in PUBLIC_EXACT_PATHS or any(route.path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return "public-allowlisted"
    return "needs-review"


def test_stage1_routes_have_explicit_boundary_classification():
    unclassified = [
        f"{','.join(sorted(route.methods or []))} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute) and classify_route_boundary(route) == "needs-review"
    ]

    assert unclassified == []


def test_stage1_internal_routes_are_not_public_allowlisted():
    internal_public = [
        f"{','.join(sorted(route.methods or []))} {route.path}"
        for route in app.routes
        if isinstance(route, APIRoute)
        and "/internal/" in route.path
        and classify_route_boundary(route) == "public-allowlisted"
    ]

    assert internal_public == []


def test_stage1_route_boundary_expected_categories_exist():
    categories = {classify_route_boundary(route) for route in app.routes if isinstance(route, APIRoute)}

    assert categories == {
        "header-secret-protected",
        "partner-reporting-token",
        "principal-protected",
        "public-allowlisted",
        "webhook-signature-protected",
    }


def test_stage1_websocket_routes_depend_on_ws_authenticate():
    unauthenticated_websockets = [
        route.path
        for route in app.routes
        if isinstance(route, APIWebSocketRoute) and "ws_authenticate" not in _websocket_dependency_names(route)
    ]

    assert unauthenticated_websockets == []
