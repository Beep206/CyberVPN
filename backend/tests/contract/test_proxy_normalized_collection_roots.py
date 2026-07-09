from fastapi import FastAPI
from fastapi.routing import APIRoute

from src.presentation.api.v1.checkout_sessions.routes import router as checkout_sessions_router
from src.presentation.api.v1.customer_subscriptions.routes import router as customer_subscriptions_router
from src.presentation.api.v1.orders.routes import router as orders_router
from src.presentation.api.v1.payment_attempts.routes import router as payment_attempts_router
from src.presentation.api.v1.quotes.routes import router as quotes_router
from src.presentation.api.v1.router import API_V1_PREFIX


def _build_probe_app() -> FastAPI:
    probe_app = FastAPI()
    probe_app.include_router(customer_subscriptions_router, prefix=API_V1_PREFIX)
    probe_app.include_router(checkout_sessions_router, prefix=API_V1_PREFIX)
    probe_app.include_router(orders_router, prefix=API_V1_PREFIX)
    probe_app.include_router(payment_attempts_router, prefix=API_V1_PREFIX)
    probe_app.include_router(quotes_router, prefix=API_V1_PREFIX)
    return probe_app


def _api_route(router, path: str, method: str) -> APIRoute:
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path == path and method in (route.methods or set()):
            return route
    raise AssertionError(f"{method} {path} route is not registered")


def test_customer_collection_roots_accept_proxy_normalized_paths_without_openapi_aliases() -> None:
    collection_roots = (
        (customer_subscriptions_router, "customer-subscriptions", "GET"),
        (orders_router, "orders", "GET"),
        (quotes_router, "quotes", "POST"),
        (checkout_sessions_router, "checkout-sessions", "POST"),
        (payment_attempts_router, "payment-attempts", "POST"),
        (payment_attempts_router, "payment-attempts", "GET"),
    )

    for router, resource, method in collection_roots:
        canonical = _api_route(router, f"/{resource}/", method)
        proxy_normalized = _api_route(router, f"/{resource}", method)

        assert canonical.include_in_schema is True
        assert proxy_normalized.include_in_schema is False

    schema = _build_probe_app().openapi()
    for _, resource, method in collection_roots:
        canonical_path = f"{API_V1_PREFIX}/{resource}/"
        proxy_normalized_path = f"{API_V1_PREFIX}/{resource}"

        assert canonical_path in schema["paths"]
        assert method.lower() in schema["paths"][canonical_path]
        if any(
            other_resource == resource and other_method != method
            for _, other_resource, other_method in collection_roots
        ):
            assert method.lower() not in schema["paths"].get(proxy_normalized_path, {})
        else:
            assert proxy_normalized_path not in schema["paths"]
