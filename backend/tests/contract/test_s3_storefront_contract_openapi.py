from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_s3_storefront_preview_contract_is_exposed_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/storefronts/{{storefront_key}}/preview" in paths
    assert "StorefrontPreviewResponse" in components
    assert "StorefrontRouteContractResponse" in components
    assert "StorefrontBrandingBoundaryResponse" in components
    assert "StorefrontPricingBoundaryResponse" in components
    assert "StorefrontAttributionContractResponse" in components
    assert "StorefrontAnalyticsContractResponse" in components
