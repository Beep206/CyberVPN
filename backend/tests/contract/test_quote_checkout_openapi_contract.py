from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_quote_checkout_session_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/quotes/" in paths
    assert f"{API_V1_PREFIX}/quotes/{{quote_session_id}}" in paths
    assert f"{API_V1_PREFIX}/checkout-sessions/" in paths
    assert f"{API_V1_PREFIX}/checkout-sessions/{{checkout_session_id}}" in paths


def test_quote_checkout_session_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CreateQuoteSessionRequest" in component_schemas
    assert "QuoteSessionResponse" in component_schemas
    assert "CreateCheckoutSessionRequest" in component_schemas
    assert "CheckoutSessionResponse" in component_schemas


def test_reserved_resource_groups_cover_quote_and_checkout_sessions() -> None:
    assert "quotes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "checkout-sessions" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
