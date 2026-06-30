from __future__ import annotations

from src.infrastructure.remnawave.contracts import (
    RemnawaveHostResponse,
    RemnawaveInboundResponse,
    RemnawaveNodeResponse,
    RemnawaveSubscriptionDetailsResponse,
)


def test_remnawave_2_8_node_host_inbound_and_subscription_payloads_validate() -> None:
    node = RemnawaveNodeResponse.model_validate(
        {
            "uuid": "node-1",
            "name": "premium-smart-ru-de",
            "address": "10.0.0.10",
            "port": 62050,
            "isConnected": True,
            "isDisabled": False,
            "isConnecting": False,
            "createdAt": "2026-06-30T00:00:00Z",
            "updatedAt": "2026-06-30T00:01:00Z",
            "tags": ["CYBERVPN_PREMIUM_SMART_RU", "xhttp"],
            "metrics": {"cpuLoad1m": 0.41, "cpuLoad5m": 0.37, "cpuLoad15m": 0.32},
            "versions": {"xray": "25.6.8", "node": "2.8.0"},
            "nodeConsumptionMultiplier": 1.0,
        }
    )
    host = RemnawaveHostResponse.model_validate(
        {
            "uuid": "host-1",
            "inboundUuid": "inbound-1",
            "remark": "Premium Smart RU XHTTP",
            "address": "de-1.cyber-vpn.org",
            "port": 8443,
            "path": "/s1-xhttp-9fec0898",
            "isDisabled": False,
            "security": "reality",
            "tags": ["CYBERVPN_PREMIUM_SMART_RU", "xhttp", "canary"],
            "xhttpExtraParams": {"mode": "auto", "host": "de-1.cyber-vpn.org"},
        }
    )
    inbound = RemnawaveInboundResponse.model_validate(
        {
            "uuid": "inbound-1",
            "tag": "VLESS_XHTTP_REALITY_8443",
            "protocol": "vless",
            "port": 8443,
            "network": "xhttp",
            "security": "reality",
            "nodeUuid": "node-1",
            "tags": ["xhttp", "premium_smart_ru"],
        }
    )
    subscription = RemnawaveSubscriptionDetailsResponse.model_validate(
        {
            "isFound": True,
            "user": {
                "shortUuid": "xhttp-user",
                "username": "xhttp-user",
                "userStatus": "ACTIVE",
                "isActive": True,
            },
            "links": ["vless://stable-user@example.com:443?type=tcp&security=reality#stable"],
            "xhttpLinks": ["vless://xhttp-user@example.com:8443?type=xhttp&security=reality#xhttp"],
            "subscriptionUrl": "https://sub.example.com/xhttp-user",
        }
    )

    assert node.is_connected is True
    assert node.cpu_load_1m == 0.41
    assert node.cpu_load_5m == 0.37
    assert node.cpu_load_15m == 0.32
    assert node.xray_version == "25.6.8"
    assert node.node_version == "2.8.0"
    assert host.is_disabled is False
    assert "xhttp" in host.tags
    assert host.xhttp_extra_params == {"mode": "auto", "host": "de-1.cyber-vpn.org"}
    assert inbound.network == "xhttp"
    assert inbound.node_uuid == node.uuid
    assert subscription.xhttp_links
    assert subscription.links


def test_remnawave_2_8_config_profile_inbound_payload_validates_without_raw_secret_leakage() -> None:
    inbound = RemnawaveInboundResponse.model_validate(
        {
            "uuid": "inbound-2",
            "tag": "VLESS_REALITY_443",
            "type": "vless",
            "network": "tcp",
            "security": "reality",
            "port": 443,
            "rawInbound": {
                "protocol": "vless",
                "settings": {"clients": [{"id": "client-secret-id"}]},
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "privateKey": "server-private-key",
                        "publicKey": "server-public-key",
                    },
                },
                "sniffing": {"enabled": True},
            },
            "activeSquads": [],
        }
    )

    assert inbound.protocol == "vless"
    assert inbound.settings == {}
    assert inbound.stream_settings == {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {"publicKey": "server-public-key"},
    }
    dumped = inbound.model_dump(by_alias=True)
    assert "rawInbound" not in dumped
    assert "activeSquads" not in dumped
    dumped_repr = repr(dumped)
    assert "privateKey" not in dumped_repr
    assert "server-private-key" not in dumped_repr
    assert "client-secret-id" not in dumped_repr
