"""Unit tests for task-worker Remnawave payload normalizers."""

import pytest

from src.services.remnawave_normalizers import normalize_node, normalize_nodes, normalize_user, normalize_users
from tests.remnawave_fixtures import load_remnawave_fixture


def test_normalize_user_handles_uppercase_status_and_nested_traffic() -> None:
    payload = load_remnawave_fixture("user_3_4_1.json")

    normalized = normalize_user(payload)

    assert normalized["id"] == 42
    assert normalized["user_id"] == 42
    assert normalized["userId"] == 42
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
        "id": 43,
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
    payload = load_remnawave_fixture("node_3_4_1.json")

    normalized = normalize_node(payload)

    assert normalized["id"] == 17
    assert normalized["node_id"] == 17
    assert normalized["uuid"] == "550e8400-e29b-41d4-a716-446655440020"
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
    assert normalized["node_version"] == "3.4.1"
    assert normalized["nodeVersion"] == "3.4.1"
    assert normalized["xray_version"] == "26.7.31"
    assert normalized["xrayVersion"] == "26.7.31"
    assert normalized["active_plugin_uuid"] == "550e8400-e29b-41d4-a716-446655440021"
    assert normalized["activePluginUuid"] == "550e8400-e29b-41d4-a716-446655440021"
    assert normalized["integration_uuids"] == ["550e8400-e29b-41d4-a716-446655440022"]
    assert normalized["ips"] == [
        {"ip": "203.0.113.17", "status": "INBOUND"},
        {"ip": "2001:db8::17", "status": "MANAGEMENT"},
    ]


def test_collection_normalizers_apply_element_wise() -> None:
    users = normalize_users([{"id": 1, "username": "a", "status": "ACTIVE"}])
    nodes = normalize_nodes(
        [
            {
                "id": 2,
                "uuid": "550e8400-e29b-41d4-a716-446655440020",
                "name": "node",
                "enabled": True,
                "integrationUuids": [],
                "ips": [],
            }
        ]
    )

    assert users[0]["status"] == "active"
    assert users[0]["user_id"] == 1
    assert nodes[0]["is_disabled"] is False
    assert nodes[0]["node_id"] == 2


@pytest.mark.parametrize("invalid_user_id", [None, True, 0, -1, "42"])
def test_normalize_user_rejects_non_numeric_or_non_positive_identity(invalid_user_id: object) -> None:
    with pytest.raises(ValueError, match="user id must be a positive integer"):
        normalize_user({"id": invalid_user_id, "username": "invalid"})


@pytest.mark.parametrize(
    "field_override",
    [
        {"id": "17"},
        {"ips": [{"ip": "not-an-ip", "status": "INBOUND"}]},
        {"ips": [{"ip": "203.0.113.17", "status": "UNSUPPORTED"}]},
        {"ips": [{"ip": f"203.0.113.{index % 250 + 1}", "status": "INBOUND"} for index in range(65)]},
        {"integrationUuids": ["not-a-uuid"]},
    ],
)
def test_normalize_node_rejects_invalid_3_4_contract_fields(field_override: dict[str, object]) -> None:
    payload = load_remnawave_fixture("node_3_4_1.json")
    payload.update(field_override)

    with pytest.raises(ValueError):
        normalize_node(payload)
