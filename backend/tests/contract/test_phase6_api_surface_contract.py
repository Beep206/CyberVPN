from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_phase6_surface_families_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    expected_paths = [
        f"{API_V1_PREFIX}/quotes/",
        f"{API_V1_PREFIX}/checkout-sessions/",
        f"{API_V1_PREFIX}/orders/",
        f"{API_V1_PREFIX}/orders/commit",
        f"{API_V1_PREFIX}/payment-attempts/",
        f"{API_V1_PREFIX}/entitlements/current",
        f"{API_V1_PREFIX}/access-delivery-channels/current/service-state",
        f"{API_V1_PREFIX}/pricebooks/resolve",
        f"{API_V1_PREFIX}/legal-documents/sets/resolve",
        f"{API_V1_PREFIX}/policy-acceptance/",
        f"{API_V1_PREFIX}/policy-acceptance/me",
        f"{API_V1_PREFIX}/partner-workspaces/me",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/codes",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/statements",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/conversion-records",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/analytics-metrics",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/report-exports",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/review-requests",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/traffic-declarations",
        f"{API_V1_PREFIX}/partner-workspaces/{{workspace_id}}/cases",
        f"{API_V1_PREFIX}/admin/mobile-users/{{user_id}}/operations-insight",
        f"{API_V1_PREFIX}/service-identities/inspect/service-state",
        f"{API_V1_PREFIX}/orders/{{order_id}}/explainability",
    ]

    for path in expected_paths:
        assert path in paths

    expected_components = [
        "QuoteSessionResponse",
        "CheckoutSessionResponse",
        "OrderResponse",
        "PaymentAttemptResponse",
        "CurrentEntitlementStateResponse",
        "CurrentServiceStateResponse",
        "PartnerWorkspaceResponse",
        "PartnerWorkspaceTrafficDeclarationResponse",
        "PartnerWorkspaceCaseResponse",
        "AdminCustomerOperationsInsightResponse",
        "ServiceAccessObservabilityResponse",
        "OrderExplainabilityResponse",
    ]

    for component in expected_components:
        assert component in components
