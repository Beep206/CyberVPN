from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_entitlement_grant_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/entitlements/" in paths
    assert f"{API_V1_PREFIX}/entitlements/current" in paths
    assert f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}" in paths
    assert f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/activate" in paths
    assert f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/suspend" in paths
    assert f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/revoke" in paths
    assert f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/expire" in paths

    assert "CreateEntitlementGrantRequest" in components
    assert "CurrentEntitlementStateResponse" in components
    assert "EntitlementGrantResponse" in components
    assert "EntitlementGrantTransitionRequest" in components
