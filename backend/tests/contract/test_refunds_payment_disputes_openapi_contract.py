from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_refund_and_payment_dispute_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/refunds/" in paths
    assert f"{API_V1_PREFIX}/refunds/{{refund_id}}" in paths
    assert f"{API_V1_PREFIX}/payment-disputes/" in paths
    assert f"{API_V1_PREFIX}/payment-disputes/{{payment_dispute_id}}" in paths


def test_refund_and_payment_dispute_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CreateRefundRequest" in component_schemas
    assert "RefundResponse" in component_schemas
    assert "UpdateRefundRequest" in component_schemas
    assert "UpsertPaymentDisputeRequest" in component_schemas
    assert "PaymentDisputeResponse" in component_schemas


def test_reserved_resource_groups_cover_refunds_and_payment_disputes() -> None:
    assert "refunds" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
    assert "payment-disputes" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
