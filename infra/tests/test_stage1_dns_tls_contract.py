# ruff: noqa: S101

"""Contract tests for the S1 DNS/TLS manifest."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_dns_tls_contract.py"

spec = importlib.util.spec_from_file_location("validate_s1_dns_tls_contract", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _contract() -> dict:
    return validator.load_contract()


def test_dns_tls_contract_is_valid() -> None:
    assert validator.validate_contract(_contract()) == []


def test_dns_tls_contract_covers_required_hosts() -> None:
    data = _contract()
    hosts = {record["host"] for record in data["records"]}
    cert_hosts = set(data["tls_requirements"]["certificate_hosts_required"])

    required = {
        "cyber-vpn.net",
        "www.cyber-vpn.net",
        "api.cyber-vpn.net",
        "admin.cyber-vpn.net",
        "de-1.cyber-vpn.org",
        "de-1.node.cyber-vpn.org",
    }

    assert required.issubset(hosts)
    assert {"cyber-vpn.net", "www.cyber-vpn.net", "api.cyber-vpn.net", "admin.cyber-vpn.net"}.issubset(
        cert_hosts
    )


def test_dns_tls_contract_keeps_org_for_nodes_not_mirrors() -> None:
    data = _contract()
    records = {record["id"]: record for record in data["records"]}
    redirects = {item["source"] for item in data["redirect_requirements"]}

    assert records["vpn_node_de_1"]["host"] == "de-1.cyber-vpn.org"
    assert records["vpn_node_de_1"]["proxied_or_edge_terminated"] is False
    assert records["vpn_node_de_1_alias"]["host"] == "de-1.node.cyber-vpn.org"
    assert records["vpn_node_de_1_alias"]["proxied_or_edge_terminated"] is False
    assert "http_or_https://cyber-vpn.org/*" not in redirects
    assert "http_or_https://admin.cyber-vpn.org/*" not in redirects


def test_dns_tls_contract_keeps_status_route_on_primary_domain_for_s1() -> None:
    data = _contract()
    status = data["status_endpoint"]

    assert status["canonical_url"] == "https://cyber-vpn.net/status"
    assert status["separate_status_subdomain_required_for_s1"] is False
    assert "no_secret_values" in status["required_behavior"]
    assert "no_internal_metrics_dump" in status["required_behavior"]


def test_dns_tls_contract_blocks_staging_home_lab_and_challenged_webhooks() -> None:
    data = _contract()
    forbidden = set(data["not_allowed"])
    callback_controls = set(data["webhook_and_callback_controls"])

    assert "dns_records_pointing_to_staging_origins" in forbidden
    assert "dns_records_pointing_to_home_lab_origins_for_customer_path" in forbidden
    assert "payment_or_telegram_webhooks_behind_interactive_browser_challenge" in forbidden
    assert "public_remnawave_api_dns_record" in forbidden

    assert "payment_webhook_paths_must_not_receive_interactive_edge_challenges" in callback_controls
    assert "telegram_webhook_paths_must_not_receive_interactive_edge_challenges" in callback_controls
    assert "oauth_callback_paths_must_not_receive_interactive_edge_challenges" in callback_controls
