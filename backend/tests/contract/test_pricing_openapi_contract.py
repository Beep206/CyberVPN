from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_pricing_foundation_openapi_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/offers/" in paths
    assert f"{API_V1_PREFIX}/offers/admin" in paths
    assert f"{API_V1_PREFIX}/pricebooks/resolve" in paths
    assert f"{API_V1_PREFIX}/pricebooks/admin" in paths
    assert f"{API_V1_PREFIX}/program-eligibility/" in paths


def test_pricing_foundation_openapi_components_expose_offer_pricebook_and_eligibility_schemas() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "OfferResponse" in component_schemas
    assert "PricebookResponse" in component_schemas
    assert "PricebookEntryResponse" in component_schemas
    assert "ProgramEligibilityPolicyResponse" in component_schemas
