"""S1-VPN-003 VPN protocol allowlist checks."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.presentation.api.shared import (
    STAGE1_DEFAULT_VPN_PROFILE_ID,
    STAGE1_XHTTP_VPN_PROFILE_ID,
    Stage1VpnProfileStage,
    Stage1VpnProfileStatus,
    Stage1VpnProtocol,
    Stage1VpnSecurity,
    Stage1VpnTransport,
    get_stage1_vpn_profile,
    is_stage1_vpn_profile_enabled,
    resolve_stage1_remnawave_profile,
    stage1_customer_vpn_protocol_summary,
    stage1_default_vpn_profile,
    stage1_disabled_vpn_profiles,
    stage1_enabled_vpn_profiles,
)


def test_stage1_enabled_protocols_are_vless_reality_only() -> None:
    enabled = stage1_enabled_vpn_profiles()

    assert {profile.profile_id for profile in enabled} == {
        STAGE1_DEFAULT_VPN_PROFILE_ID,
        STAGE1_XHTTP_VPN_PROFILE_ID,
    }
    assert all(profile.protocol == Stage1VpnProtocol.VLESS for profile in enabled)
    assert all(profile.security == Stage1VpnSecurity.REALITY for profile in enabled)
    assert {profile.transport for profile in enabled} == {Stage1VpnTransport.RAW, Stage1VpnTransport.XHTTP}
    assert all(profile.customer_visible for profile in enabled)
    assert all(profile.required_for_s1 for profile in enabled)


def test_stage1_has_exactly_one_default_profile() -> None:
    default = stage1_default_vpn_profile()

    assert default.profile_id == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert default.transport == Stage1VpnTransport.RAW
    assert default.flow == "xtls-rprx-vision"
    assert default.status == Stage1VpnProfileStatus.ENABLED
    assert default.stage == Stage1VpnProfileStage.S1


def test_stage1_xhttp_profile_is_enabled_but_not_default() -> None:
    xhttp = get_stage1_vpn_profile(STAGE1_XHTTP_VPN_PROFILE_ID)

    assert xhttp.enabled is True
    assert xhttp.transport == Stage1VpnTransport.XHTTP
    assert xhttp.security == Stage1VpnSecurity.REALITY
    assert xhttp.default_profile is False
    assert xhttp.required_for_s1 is True


@pytest.mark.parametrize(
    "profile_id",
    ["wireguard", "openvpn", "vmess", "trojan", "shadowsocks", "hysteria2", "tuic", "helix", "verta", "beep"],
)
def test_stage1_non_s1_protocols_are_disabled(profile_id: str) -> None:
    profile = get_stage1_vpn_profile(profile_id)

    assert profile.enabled is False
    assert profile.customer_visible is False
    assert is_stage1_vpn_profile_enabled(profile_id) is False


def test_stage1_private_transports_are_s6_only_and_disabled() -> None:
    disabled_private = {
        profile.profile_id: profile
        for profile in stage1_disabled_vpn_profiles()
        if profile.protocol in {Stage1VpnProtocol.HELIX, Stage1VpnProtocol.VERTA, Stage1VpnProtocol.BEEP}
    }

    assert set(disabled_private) == {"helix", "verta", "beep"}
    assert all(profile.stage == Stage1VpnProfileStage.S6 for profile in disabled_private.values())
    assert all(not profile.enabled for profile in disabled_private.values())


@pytest.mark.parametrize(
    ("protocol", "transport", "security", "expected_profile_id"),
    [
        ("vless", "raw", "reality", STAGE1_DEFAULT_VPN_PROFILE_ID),
        ("vless", "tcp", "reality", STAGE1_DEFAULT_VPN_PROFILE_ID),
        ("vless", "xhttp", "reality", STAGE1_XHTTP_VPN_PROFILE_ID),
    ],
)
def test_stage1_resolves_remnawave_vless_reality_profiles(
    protocol: str,
    transport: str,
    security: str,
    expected_profile_id: str,
) -> None:
    profile = resolve_stage1_remnawave_profile(protocol=protocol, transport=transport, security=security)

    assert profile is not None
    assert profile.profile_id == expected_profile_id


@pytest.mark.parametrize(
    ("protocol", "transport", "security"),
    [
        ("trojan", "raw", "tls"),
        ("shadowsocks", "raw", "none"),
        ("vless", "grpc", "reality"),
        ("vless", "ws", "tls"),
        ("wireguard", "unknown", "unknown"),
        ("vmess", "raw", "tls"),
        ("tuic", "quic", "tls"),
        ("unknown-protocol", "xhttp", "reality"),
        ("vless", "unknown-transport", "reality"),
        ("vless", "xhttp", "unknown-security"),
    ],
)
def test_stage1_does_not_resolve_disabled_or_unapproved_remnawave_profiles(
    protocol: str,
    transport: str,
    security: str,
) -> None:
    assert resolve_stage1_remnawave_profile(protocol=protocol, transport=transport, security=security) is None


def test_stage1_protocol_summary_is_safe_and_customer_scoped() -> None:
    summary = stage1_customer_vpn_protocol_summary()
    serialized = str(summary).lower()

    assert summary == {
        "default_profile_id": STAGE1_DEFAULT_VPN_PROFILE_ID,
        "enabled_profile_ids": [STAGE1_DEFAULT_VPN_PROFILE_ID, STAGE1_XHTTP_VPN_PROFILE_ID],
        "customer_visible_profile_ids": [STAGE1_DEFAULT_VPN_PROFILE_ID, STAGE1_XHTTP_VPN_PROFILE_ID],
        "private_transports_disabled": {"helix": "S6", "verta": "S6", "beep": "S6"},
    }
    assert "subscription" not in serialized
    assert "config_link" not in serialized
    assert "secret" not in serialized
    assert "token" not in serialized


@pytest.mark.asyncio
async def test_stage1_protocol_contract_serializes_through_asgi_route() -> None:
    app = FastAPI()

    @app.get("/s1/vpn/protocols")
    async def protocols() -> dict[str, Any]:
        return {
            "summary": stage1_customer_vpn_protocol_summary(),
            "enabled": [profile.to_api_dict() for profile in stage1_enabled_vpn_profiles()],
            "disabled": [profile.to_api_dict() for profile in stage1_disabled_vpn_profiles()],
        }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://backend") as client:
        response = await client.get("/s1/vpn/protocols")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["default_profile_id"] == STAGE1_DEFAULT_VPN_PROFILE_ID
    assert [profile["profile_id"] for profile in body["enabled"]] == [
        STAGE1_DEFAULT_VPN_PROFILE_ID,
        STAGE1_XHTTP_VPN_PROFILE_ID,
    ]
    assert {profile["profile_id"] for profile in body["disabled"]} >= {"helix", "verta", "beep"}
    assert all(profile["status"] == "enabled" for profile in body["enabled"])
    assert all(profile["customer_visible"] is False for profile in body["disabled"])
