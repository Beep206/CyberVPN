# ruff: noqa: S101

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_production_topology.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_s1_production_topology", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage1_production_topology_validates() -> None:
    validator = _load_validator()
    errors = validator.validate_topology(validator.load_topology())
    assert errors == []


def test_stage1_production_topology_keeps_critical_path_outside_home_lab() -> None:
    validator = _load_validator()
    data = validator.load_topology()
    forbidden = set(data["home_lab_boundary"]["forbidden_for_s1_production"])
    critical_components = {
        component["id"]
        for component in data["components"]
        if component.get("production_critical") is True and component.get("home_lab_allowed") is False
    }

    assert "backend_api" in forbidden
    assert "production_postgresql" in forbidden
    assert "production_remnawave_control_plane" in forbidden
    assert "vpn_exit_node" in forbidden
    assert "backend_api" in critical_components
    assert "managed_postgresql" in critical_components
    assert "remnawave_control_plane" in critical_components


def test_stage1_production_topology_documents_private_state_authority() -> None:
    validator = _load_validator()
    data = validator.load_topology()
    authorities = {item["data"]: item["source_of_truth"] for item in data["data_authority"]}

    assert authorities["user_account_auth_payment_subscription_support_audit"] == "managed_postgresql"
    assert authorities["critical_payment_and_provisioning_jobs"] == "managed_postgresql"
    assert authorities["vpn_access_runtime"] == "remnawave_control_plane"


def test_stage1_production_topology_protects_webhook_and_admin_ingress() -> None:
    validator = _load_validator()
    data = validator.load_topology()
    ingress = {item["id"]: item for item in data["public_ingress"]}

    assert "cloudflare_access_or_ip_allowlist_or_equivalent" in ingress["admin_primary"]["required_controls"]
    assert "no_interactive_edge_challenge" in ingress["payment_webhooks"]["required_controls"]
    assert "no_interactive_edge_challenge" in ingress["telegram_webhook"]["required_controls"]
    assert "no_interactive_edge_challenge" in ingress["oauth_web_callbacks"]["required_controls"]
