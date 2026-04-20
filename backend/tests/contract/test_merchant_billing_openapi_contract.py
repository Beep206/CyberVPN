from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_merchant_billing_foundation_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/merchant-profiles/" in paths
    assert f"{API_V1_PREFIX}/merchant-profiles/resolve" in paths
    assert f"{API_V1_PREFIX}/invoice-profiles/" in paths
    assert f"{API_V1_PREFIX}/billing-descriptors/" in paths
    assert f"{API_V1_PREFIX}/billing-descriptors/resolve" in paths


def test_merchant_billing_foundation_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "MerchantProfileResponse" in component_schemas
    assert "InvoiceProfileResponse" in component_schemas
    assert "BillingDescriptorResponse" in component_schemas
    assert "CreateMerchantProfileRequest" in component_schemas
    assert "CreateInvoiceProfileRequest" in component_schemas
    assert "CreateBillingDescriptorRequest" in component_schemas


def test_reserved_resource_groups_cover_phase2_foundations() -> None:
    assert "merchant-profiles" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "invoice-profiles" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "billing-descriptors" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "quotes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "orders" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "payment-disputes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
