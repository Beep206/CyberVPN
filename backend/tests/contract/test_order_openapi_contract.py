from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_order_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/orders/" in paths
    assert f"{API_V1_PREFIX}/orders/commit" in paths
    assert f"{API_V1_PREFIX}/orders/{{order_id}}" in paths


def test_order_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CreateOrderFromCheckoutRequest" in component_schemas
    assert "OrderResponse" in component_schemas
    assert "OrderItemResponse" in component_schemas


def test_reserved_resource_groups_cover_orders_and_order_items() -> None:
    assert "orders" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "order-items" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
