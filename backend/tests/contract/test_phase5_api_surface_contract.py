import json
from pathlib import Path

from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX

PHASE5_REQUIRED_PATHS = (
    f"{API_V1_PREFIX}/service-identities/",
    f"{API_V1_PREFIX}/service-identities/legacy/shadow-parity",
    f"{API_V1_PREFIX}/service-identities/legacy/migrate",
    f"{API_V1_PREFIX}/service-identities/inspect/service-state",
    f"{API_V1_PREFIX}/service-identities/{{service_identity_id}}",
    f"{API_V1_PREFIX}/service-identities/{{service_identity_id}}/service-state",
    f"{API_V1_PREFIX}/provisioning-profiles/",
    f"{API_V1_PREFIX}/provisioning-profiles/{{provisioning_profile_id}}",
    f"{API_V1_PREFIX}/entitlements/",
    f"{API_V1_PREFIX}/entitlements/current",
    f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}",
    f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/activate",
    f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/suspend",
    f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/revoke",
    f"{API_V1_PREFIX}/entitlements/{{entitlement_grant_id}}/expire",
    f"{API_V1_PREFIX}/device-credentials/",
    f"{API_V1_PREFIX}/device-credentials/{{device_credential_id}}",
    f"{API_V1_PREFIX}/device-credentials/{{device_credential_id}}/revoke",
    f"{API_V1_PREFIX}/access-delivery-channels/",
    f"{API_V1_PREFIX}/access-delivery-channels/resolve/current",
    f"{API_V1_PREFIX}/access-delivery-channels/current/service-state",
    f"{API_V1_PREFIX}/access-delivery-channels/{{access_delivery_channel_id}}",
    f"{API_V1_PREFIX}/access-delivery-channels/{{access_delivery_channel_id}}/archive",
)

PHASE5_REQUIRED_SCHEMAS = (
    "ServiceIdentityResponse",
    "LegacyServiceAccessShadowRequest",
    "LegacyServiceAccessShadowResponse",
    "MigrateLegacyServiceAccessResponse",
    "ServiceAccessObservabilityRequest",
    "ServiceAccessObservabilityResponse",
    "ProvisioningProfileResponse",
    "EntitlementGrantResponse",
    "CurrentEntitlementStateResponse",
    "DeviceCredentialResponse",
    "AccessDeliveryChannelResponse",
    "ResolveCurrentAccessDeliveryChannelResponse",
    "CurrentServiceStateResponse",
)


def _exported_openapi_schema() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    exported_schema_path = repo_root / "backend" / "docs" / "api" / "openapi.json"
    assert exported_schema_path.exists(), "backend/docs/api/openapi.json must exist for frozen Phase 5 contracts"
    return json.loads(exported_schema_path.read_text(encoding="utf-8"))


def test_live_openapi_contains_phase5_service_access_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    for required_path in PHASE5_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase5_service_access_paths() -> None:
    schema = _exported_openapi_schema()
    paths = schema["paths"]

    for required_path in PHASE5_REQUIRED_PATHS:
        assert required_path in paths


def test_exported_openapi_contains_phase5_service_access_schemas() -> None:
    schema = _exported_openapi_schema()
    components = schema["components"]["schemas"]

    for schema_name in PHASE5_REQUIRED_SCHEMAS:
        assert schema_name in components
