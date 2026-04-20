from src.main import app
from src.presentation.api.v1.router import API_V1_PREFIX


def test_device_credentials_and_access_delivery_channel_routes_exist_in_openapi() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert f"{API_V1_PREFIX}/device-credentials/" in paths
    assert f"{API_V1_PREFIX}/device-credentials/{{device_credential_id}}" in paths
    assert f"{API_V1_PREFIX}/device-credentials/{{device_credential_id}}/revoke" in paths
    assert f"{API_V1_PREFIX}/access-delivery-channels/" in paths
    assert f"{API_V1_PREFIX}/access-delivery-channels/current/service-state" in paths
    assert f"{API_V1_PREFIX}/access-delivery-channels/resolve/current" in paths
    assert f"{API_V1_PREFIX}/access-delivery-channels/{{access_delivery_channel_id}}" in paths
    assert f"{API_V1_PREFIX}/access-delivery-channels/{{access_delivery_channel_id}}/archive" in paths

    assert "CreateDeviceCredentialRequest" in components
    assert "DeviceCredentialResponse" in components
    assert "CreateAccessDeliveryChannelRequest" in components
    assert "AccessDeliveryChannelResponse" in components
    assert "GetCurrentServiceStateRequest" in components
    assert "CurrentServiceStateResponse" in components
    assert "ResolveCurrentAccessDeliveryChannelRequest" in components
    assert "ResolveCurrentAccessDeliveryChannelResponse" in components
