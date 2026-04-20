from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX, PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS


def test_payment_attempt_paths_are_exposed() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert f"{API_V1_PREFIX}/payment-attempts/" in paths
    assert f"{API_V1_PREFIX}/payment-attempts/{{payment_attempt_id}}" in paths


def test_payment_attempt_components_are_exposed() -> None:
    schema = app.openapi()
    component_schemas = schema["components"]["schemas"]

    assert "CreatePaymentAttemptRequest" in component_schemas
    assert "PaymentAttemptResponse" in component_schemas


def test_reserved_resource_groups_cover_payment_attempts() -> None:
    assert "payment-attempts" in PARTNER_PLATFORM_RESERVED_RESOURCE_GROUPS
