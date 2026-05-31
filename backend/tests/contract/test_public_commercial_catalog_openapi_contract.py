from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_public_commercial_catalog_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/catalog/context" in paths
    assert f"{API_V1_PREFIX}/catalog/" in paths


def test_public_commercial_catalog_components_expose_context_and_catalog_schemas() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "PublicCatalogContextResponse" in component_schemas
    assert "PublicCommercialCatalogResponse" in component_schemas
    assert "PublicCatalogQuoteHandoffResponse" in component_schemas


def test_quote_handoff_schema_does_not_accept_trusted_price_fields() -> None:
    schema = app.openapi()
    quote_properties = schema["components"]["schemas"]["PublicCatalogQuoteHandoffResponse"]["properties"]

    assert set(quote_properties).isdisjoint({"price", "amount", "visiblePrice", "displayPrice"})
    assert set(quote_properties) == {
        "planId",
        "planCode",
        "billingPeriodDays",
        "currency",
        "catalogItemKey",
        "contextCacheKey",
    }
