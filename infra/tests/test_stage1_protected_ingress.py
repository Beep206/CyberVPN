# ruff: noqa: S101

"""Contract tests for the S1 protected ingress manifest."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_protected_ingress.py"

spec = importlib.util.spec_from_file_location("validate_s1_protected_ingress", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _ingress() -> dict:
    return validator.load_ingress()


def test_protected_ingress_contract_is_valid() -> None:
    assert validator.validate_ingress(_ingress()) == []


def test_backend_and_admin_are_not_direct_public_origins() -> None:
    data = _ingress()
    authority = data["authority"]
    private_components = {item["id"]: item for item in data["private_only_components"]}

    assert authority["backend_direct_public_access_allowed"] is False
    assert authority["admin_public_without_access_allowed"] is False
    assert authority["remnawave_api_public_allowed"] is False
    assert authority["postgresql_public_allowed"] is False
    assert authority["valkey_public_allowed"] is False
    assert authority["home_lab_customer_ingress_allowed"] is False

    for component_id in {
        "backend_container_port",
        "admin_container_port",
        "remnawave_control_plane_api",
        "postgresql",
        "valkey",
        "metrics_and_traces",
    }:
        assert private_components[component_id]["public_dns_allowed"] is False
        assert private_components[component_id]["public_port_allowed"] is False


def test_s1_entrypoints_match_approved_domains() -> None:
    data = _ingress()
    entrypoints = {item["id"]: item for item in data["public_entrypoints"]}

    assert entrypoints["public_site_primary"]["host"] == "cyber-vpn.net"
    assert entrypoints["public_site_www"]["host"] == "www.cyber-vpn.net"
    assert entrypoints["public_site_mirror"]["host"] == "cyber-vpn.org"
    assert entrypoints["public_site_mirror_www"]["host"] == "www.cyber-vpn.org"
    assert entrypoints["public_api"]["host"] == "api.cyber-vpn.net"
    assert entrypoints["admin_primary"]["host"] == "admin.cyber-vpn.net"
    assert entrypoints["admin_mirror"]["host"] == "admin.cyber-vpn.org"


def test_admin_surface_requires_access_gate_2fa_rbac_and_audit() -> None:
    data = _ingress()
    entrypoints = {item["id"]: item for item in data["public_entrypoints"]}
    admin_controls = set(entrypoints["admin_primary"]["required_controls"])
    mirror_controls = set(entrypoints["admin_mirror"]["required_controls"])

    assert entrypoints["admin_primary"]["public"] is False
    assert "cloudflare_access_or_ip_allowlist_or_private_vpn" in admin_controls
    assert "admin_host_guard" in admin_controls
    assert "mandatory_admin_2fa" in admin_controls
    assert "rbac" in admin_controls
    assert "privileged_audit_log" in admin_controls
    assert "no_public_login_before_access_gate" in admin_controls

    assert "redirect_to_admin_primary" in mirror_controls
    assert "no_independent_session_cookie" in mirror_controls
    assert "no_admin_backend_origin" in mirror_controls


def test_webhooks_and_oauth_callbacks_have_no_interactive_challenge() -> None:
    data = _ingress()
    entrypoints = {item["id"]: item for item in data["public_entrypoints"]}

    for entrypoint_id in {"payment_webhooks", "telegram_webhook", "oauth_callbacks"}:
        controls = set(entrypoints[entrypoint_id]["required_controls"])
        assert "no_interactive_edge_challenge" in controls
        assert entrypoints[entrypoint_id]["paths"]


def test_blocked_public_paths_cover_admin_docs_and_internal_api() -> None:
    data = _ingress()
    blocked = {item["id"]: item for item in data["blocked_public_paths"]}
    not_allowed = set(data["not_allowed"])

    assert "/api/v1/admin/*" in blocked["block_admin_paths_on_customer_web"]["paths"]
    assert "/docs" in blocked["block_docs_in_production"]["paths"]
    assert "/openapi.json" in blocked["block_docs_in_production"]["paths"]
    assert "/api/v1/internal/*" in blocked["block_internal_api_publicly"]["paths"]

    assert "admin_api_served_from_customer_domain_without_host_guard" in not_allowed
    assert "interactive_challenge_on_payment_webhooks" in not_allowed
    assert "interactive_challenge_on_telegram_webhook" in not_allowed
    assert "interactive_challenge_on_oauth_callbacks" in not_allowed
