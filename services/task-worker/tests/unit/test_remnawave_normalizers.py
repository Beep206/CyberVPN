"""Unit tests for task-worker Remnawave payload normalizers."""

from src.services.remnawave_normalizers import normalize_node, normalize_nodes, normalize_user, normalize_users
from tests.remnawave_fixtures import load_remnawave_fixture


def test_normalize_user_handles_uppercase_status_and_nested_traffic() -> None:
    payload = load_remnawave_fixture("user_2_7_4.json")

    normalized = normalize_user(payload)

    assert normalized["status"] == "active"
    assert normalized["expire_at"] == "2027-12-31T23:59:59+00:00"
    assert normalized["expiresAt"] == "2027-12-31T23:59:59+00:00"
    assert normalized["traffic_limit_bytes"] == 1024
    assert normalized["dataLimit"] == 1024
    assert normalized["used_traffic_bytes"] == 64
    assert normalized["usedTrafficBytes"] == 64
    assert normalized["dataUsed"] == 64
    assert normalized["lifetime_used_traffic_bytes"] == 128
    assert normalized["telegram_id"] == 123456
    assert normalized["telegramId"] == 123456
    assert normalized["online_at"] == "2026-04-12T13:00:00+00:00"
    assert normalized["is_online"] is True
    assert normalized["isOnline"] is True


def test_normalize_user_preserves_existing_snake_case_fields() -> None:
    payload = {
        "uuid": "550e8400-e29b-41d4-a716-446655440010",
        "username": "snake-case-user",
        "status": "disabled",
        "expire_at": "2027-01-01T00:00:00+00:00",
        "traffic_limit_bytes": 2048,
        "used_traffic_bytes": 256,
        "telegram_id": 999,
        "is_online": False,
    }

    normalized = normalize_user(payload)

    assert normalized["status"] == "disabled"
    assert normalized["expire_at"] == "2027-01-01T00:00:00+00:00"
    assert normalized["expiresAt"] == "2027-01-01T00:00:00+00:00"
    assert normalized["trafficLimitBytes"] == 2048
    assert normalized["dataLimit"] == 2048
    assert normalized["usedTrafficBytes"] == 256
    assert normalized["dataUsed"] == 256
    assert normalized["telegramId"] == 999
    assert normalized["isOnline"] is False


def test_normalize_node_handles_versions_and_plugin_fields() -> None:
    payload = load_remnawave_fixture("node_2_7_4.json")

    normalized = normalize_node(payload)

    assert normalized["address"] == "fra-01.example.com"
    assert normalized["hostname"] == "fra-01.example.com"
    assert normalized["is_connected"] is True
    assert normalized["isConnected"] is True
    assert normalized["is_disabled"] is False
    assert normalized["isDisabled"] is False
    assert normalized["enabled"] is True
    assert normalized["country_code"] == "DE"
    assert normalized["countryCode"] == "DE"
    assert normalized["traffic_up"] == 10
    assert normalized["trafficUp"] == 10
    assert normalized["traffic_down"] == 20
    assert normalized["trafficDown"] == 20
    assert normalized["current_bandwidth"] == 30
    assert normalized["currentBandwidth"] == 30
    assert normalized["node_version"] == "2.7.4"
    assert normalized["nodeVersion"] == "2.7.4"
    assert normalized["xray_version"] == "1.8.24"
    assert normalized["xrayVersion"] == "1.8.24"
    assert normalized["active_plugin_uuid"] == "550e8400-e29b-41d4-a716-446655440021"
    assert normalized["activePluginUuid"] == "550e8400-e29b-41d4-a716-446655440021"


def test_collection_normalizers_apply_element_wise() -> None:
    users = normalize_users([{"uuid": "u-1", "username": "a", "status": "ACTIVE"}])
    nodes = normalize_nodes([{"uuid": "n-1", "name": "node", "enabled": True}])

    assert users[0]["status"] == "active"
    assert nodes[0]["is_disabled"] is False
