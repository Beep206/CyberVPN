# ruff: noqa: S101

"""Deployment contract for the proxy-only VPN runtime agent."""

from __future__ import annotations

from pathlib import Path

STAGE1_COMPOSE = (
    Path(__file__).resolve().parents[1]
    / "deploy"
    / "stage1"
    / "docker-compose.stage1.yml"
)


def test_vpn_test_agent_has_backend_and_egress_networks() -> None:
    compose = STAGE1_COMPOSE.read_text(encoding="utf-8")
    service = compose.split("  cybervpn-vpn-test-agent:\n", 1)[1].split(
        "\n  cybervpn-worker:", 1
    )[0]

    assert "      cybervpn-backend: {}" in service
    assert "      cybervpn-egress: {}" in service
    assert "VPN_TEST_AGENT_TUN_ENABLED: ${VPN_TEST_AGENT_TUN_ENABLED:-false}" in service
