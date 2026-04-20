import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

PHASE2_REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/merchant-profiles/",
    f"{API_V1_PREFIX}/merchant-profiles/resolve",
    f"{API_V1_PREFIX}/invoice-profiles/",
    f"{API_V1_PREFIX}/billing-descriptors/",
    f"{API_V1_PREFIX}/quotes/",
    f"{API_V1_PREFIX}/checkout-sessions/",
    f"{API_V1_PREFIX}/checkout-sessions/{{checkout_session_id}}",
    f"{API_V1_PREFIX}/orders/commit",
    f"{API_V1_PREFIX}/orders/",
    f"{API_V1_PREFIX}/orders/{{order_id}}",
    f"{API_V1_PREFIX}/orders/{{order_id}}/explainability",
    f"{API_V1_PREFIX}/payment-attempts/",
    f"{API_V1_PREFIX}/payment-attempts/{{payment_attempt_id}}",
    f"{API_V1_PREFIX}/refunds/",
    f"{API_V1_PREFIX}/refunds/{{refund_id}}",
    f"{API_V1_PREFIX}/payment-disputes/",
    f"{API_V1_PREFIX}/payment-disputes/{{payment_dispute_id}}",
)

PHASE2_REQUIRED_SCHEMAS = (
    "MerchantProfileResponse",
    "InvoiceProfileResponse",
    "BillingDescriptorResponse",
    "QuoteSessionResponse",
    "CheckoutSessionResponse",
    "OrderResponse",
    "OrderExplainabilityResponse",
    "PaymentAttemptResponse",
    "RefundResponse",
    "PaymentDisputeResponse",
    "CommissionabilityEvaluationResponse",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 2 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_live_openapi_contains_phase2_foundation_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for required_path in PHASE2_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase2_foundation_paths() -> None:
    schema = _exported_openapi_schema()
    paths = schema["paths"]

    for required_path in PHASE2_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase2_foundation_schemas() -> None:
    schema = _exported_openapi_schema()
    components = schema["components"]["schemas"]

    for schema_name in PHASE2_REQUIRED_SCHEMAS:
        assert schema_name in components
