from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_service_identity_and_provisioning_profile_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/service-identities/" in paths
    assert f"{API_V1_PREFIX}/service-identities/legacy/shadow-parity" in paths
    assert f"{API_V1_PREFIX}/service-identities/legacy/migrate" in paths
    assert f"{API_V1_PREFIX}/service-identities/inspect/service-state" in paths
    assert f"{API_V1_PREFIX}/service-identities/{{service_identity_id}}" in paths
    assert f"{API_V1_PREFIX}/service-identities/{{service_identity_id}}/service-state" in paths
    assert f"{API_V1_PREFIX}/provisioning-profiles/" in paths
    assert f"{API_V1_PREFIX}/provisioning-profiles/{{provisioning_profile_id}}" in paths

    assert "CreateServiceIdentityRequest" in components
    assert "LegacyServiceAccessShadowRequest" in components
    assert "LegacyServiceAccessShadowResponse" in components
    assert "MigrateLegacyServiceAccessResponse" in components
    assert "ServiceAccessObservabilityRequest" in components
    assert "ServiceAccessObservabilityResponse" in components
    assert "ServiceIdentityResponse" in components
    assert "CreateProvisioningProfileRequest" in components
    assert "ProvisioningProfileResponse" in components
