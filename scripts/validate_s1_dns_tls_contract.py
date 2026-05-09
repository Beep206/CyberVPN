#!/usr/bin/env python3
"""Validate the Stage 1 DNS/TLS contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "infra" / "dns" / "stage1-dns-tls-contract.json"

REQUIRED_DECISIONS = {"DEC-S1-001", "DEC-S1-002", "DEC-S1-003", "DEC-S1-014", "DEC-S1-017"}
REQUIRED_ZONES = {"cyber-vpn.net", "cyber-vpn.org"}
REQUIRED_RECORDS = {
    "public_apex_primary": "cyber-vpn.net",
    "public_www_primary": "www.cyber-vpn.net",
    "public_api_primary": "api.cyber-vpn.net",
    "admin_primary": "admin.cyber-vpn.net",
    "public_apex_mirror": "cyber-vpn.org",
    "public_www_mirror": "www.cyber-vpn.org",
    "admin_mirror": "admin.cyber-vpn.org",
}
REQUIRED_CERT_HOSTS = set(REQUIRED_RECORDS.values())
REQUIRED_ADMIN_CONTROLS = {
    "admin_canonical_host_is_admin_cyber_vpn_net",
    "admin_mirror_redirects_to_primary_admin",
    "admin_mirror_must_not_set_independent_session_cookie",
    "admin_primary_requires_cloudflare_access_ip_allowlist_or_equivalent_before_login",
    "admin_primary_requires_backend_admin_host_guard",
    "admin_primary_requires_admin_2fa",
}
REQUIRED_WEBHOOK_CONTROLS = {
    "api_cyber_vpn_net_tls_valid",
    "payment_webhook_paths_must_not_receive_interactive_edge_challenges",
    "telegram_webhook_paths_must_not_receive_interactive_edge_challenges",
    "oauth_callback_paths_must_not_receive_interactive_edge_challenges",
    "payment_webhooks_still_require_provider_signature_or_status_recheck",
    "telegram_webhooks_still_require_bot_secret_or_telegram_validation",
}
REQUIRED_EVIDENCE_COMMANDS = {
    "dig_or_equivalent_for_each_required_host",
    "curl_head_http_to_https_redirect_for_each_public_host",
    "curl_head_www_and_org_redirects_to_canonical",
    "curl_head_admin_org_redirects_to_admin_cyber_vpn_net",
    "openssl_or_equivalent_tls_certificate_check_for_each_required_host",
    "curl_status_route_https_check_for_https_cyber_vpn_net_status",
    "admin_access_protection_browser_or_curl_proof",
    "payment_webhook_no_interactive_challenge_probe",
    "telegram_webhook_no_interactive_challenge_probe",
    "oauth_callback_no_interactive_challenge_probe",
}
REQUIRED_NOT_ALLOWED = {
    "dns_records_pointing_to_staging_origins",
    "dns_records_pointing_to_home_lab_origins_for_customer_path",
    "wildcard_dns_records_without_explicit_review",
    "admin_cyber_vpn_org_serving_independent_admin_session",
    "public_remnawave_api_dns_record",
    "public_postgresql_dns_record",
    "public_valkey_dns_record",
    "payment_or_telegram_webhooks_behind_interactive_browser_challenge",
    "production_tls_using_staging_or_local_only_certificate",
    "committed_dns_provider_tokens_zone_ids_or_origin_ips",
}
SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"password\s*[:=]\s*[^<\s][^\s]{8,}",
        r"api[_-]?token\s*[:=]\s*[a-z0-9_-]{16,}",
        r"secret\s*[:=]\s*[a-z0-9_-]{16,}",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"zone[_-]?id\s*[:=]\s*[a-f0-9]{16,}",
        r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    )
]


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id", "")) for item in items}


def _by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    return next((item for item in items if item.get("id") == item_id), {})


def _walk_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        output: list[str] = []
        for key, nested in value.items():
            output.append(str(key))
            output.extend(_walk_values(nested))
        return output
    if isinstance(value, list):
        output = []
        for nested in value:
            output.extend(_walk_values(nested))
        return output
    if value is None:
        return []
    return [str(value)]


def validate_contract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-004":
        errors.append("backlog_id must be S1-INFRA-004")
    if data.get("status") != "local_dns_tls_contract_external_dns_required":
        errors.append("status must mark this as local DNS/TLS contract with external evidence required")
    if data.get("provider") != "cloudflare_or_equivalent_dns_tls_edge":
        errors.append("provider must be cloudflare_or_equivalent_dns_tls_edge")
    if not {"S1-INFRA-001", "S1-INFRA-003", "S1-INFRA-008"}.issubset(set(data.get("depends_on", []))):
        errors.append("DNS/TLS contract must depend on topology, production environment and edge baseline")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    authority = data.get("authority", {})
    if authority.get("go_live_clearance") is not False:
        errors.append("local DNS/TLS contract must not grant go-live clearance")
    if authority.get("external_dns_configured") is not False:
        errors.append("external_dns_configured must remain false until live evidence exists")
    if authority.get("external_tls_configured") is not False:
        errors.append("external_tls_configured must remain false until live evidence exists")
    for key in {
        "must_not_point_to_staging_origins",
        "must_not_point_to_home_lab_origins",
        "must_not_use_staging_certificates",
        "requires_live_dns_tls_evidence_before_traffic",
    }:
        if authority.get(key) is not True:
            errors.append(f"authority.{key} must be true")

    zones = {zone.get("domain") for zone in data.get("zones", [])}
    if not REQUIRED_ZONES.issubset(zones):
        errors.append(f"zones must include {sorted(REQUIRED_ZONES)}")

    records = data.get("records", [])
    record_ids = _ids(records)
    if not set(REQUIRED_RECORDS).issubset(record_ids):
        errors.append(f"records missing {sorted(set(REQUIRED_RECORDS) - record_ids)}")
    for record_id, host in REQUIRED_RECORDS.items():
        record = _by_id(records, record_id)
        if record.get("host") != host:
            errors.append(f"{record_id} host must be {host}")
        if record.get("proxied_or_edge_terminated") is not True:
            errors.append(f"{record_id} must be proxied or edge terminated")
        if "staging" in str(record.get("record_policy", "")).lower():
            errors.append(f"{record_id} must not reference staging in record_policy")

    api_record = _by_id(records, "public_api_primary")
    if "without_interactive_challenge" not in str(api_record.get("behavior", "")):
        errors.append("api record behavior must require no interactive challenge for callbacks")

    admin_record = _by_id(records, "admin_primary")
    if "access_protection" not in str(admin_record.get("behavior", "")):
        errors.append("admin primary behavior must require access protection")

    admin_mirror = _by_id(records, "admin_mirror")
    if admin_mirror.get("behavior") != "redirect_to_https_admin_cyber_vpn_net_preserve_path_no_independent_session":
        errors.append("admin mirror must redirect to primary admin without independent session")

    status_endpoint = data.get("status_endpoint", {})
    if status_endpoint.get("canonical_url") != "https://cyber-vpn.net/status":
        errors.append("status endpoint canonical_url must be https://cyber-vpn.net/status")
    if status_endpoint.get("separate_status_subdomain_required_for_s1") is not False:
        errors.append("S1 must not require a separate status subdomain")
    if "no_secret_values" not in set(status_endpoint.get("required_behavior", [])):
        errors.append("status endpoint must forbid secret values")

    tls = data.get("tls_requirements", {})
    if tls.get("edge_tls_required") is not True:
        errors.append("edge TLS must be required")
    if tls.get("full_strict_or_equivalent_required_before_go_live") is not True:
        errors.append("full strict or equivalent TLS must be required before go-live")
    if str(tls.get("minimum_tls_version")) not in {"1.2", "1.3"}:
        errors.append("minimum TLS version must be 1.2 or 1.3")
    cert_hosts = set(tls.get("certificate_hosts_required", []))
    if not REQUIRED_CERT_HOSTS.issubset(cert_hosts):
        errors.append(f"certificate_hosts_required missing {sorted(REQUIRED_CERT_HOSTS - cert_hosts)}")

    redirects = data.get("redirect_requirements", [])
    redirect_targets = {item.get("target") for item in redirects}
    if "https://cyber-vpn.net/$path" not in redirect_targets:
        errors.append("redirects must include canonical public .net target")
    if "https://admin.cyber-vpn.net/$path" not in redirect_targets:
        errors.append("redirects must include canonical admin .net target")
    if not all(item.get("status") == "301_or_308" for item in redirects):
        errors.append("all redirects must use 301_or_308")

    admin_controls = set(data.get("admin_dns_tls_controls", []))
    if not REQUIRED_ADMIN_CONTROLS.issubset(admin_controls):
        errors.append(f"admin_dns_tls_controls missing {sorted(REQUIRED_ADMIN_CONTROLS - admin_controls)}")

    webhook_controls = set(data.get("webhook_and_callback_controls", []))
    if not REQUIRED_WEBHOOK_CONTROLS.issubset(webhook_controls):
        errors.append(f"webhook_and_callback_controls missing {sorted(REQUIRED_WEBHOOK_CONTROLS - webhook_controls)}")

    evidence_commands = set(data.get("evidence_commands_required_before_go_live", []))
    if not REQUIRED_EVIDENCE_COMMANDS.issubset(evidence_commands):
        missing = sorted(REQUIRED_EVIDENCE_COMMANDS - evidence_commands)
        errors.append(f"evidence_commands_required_before_go_live missing {missing}")

    scaffolds = set(data.get("existing_repo_scaffolds", []))
    for scaffold in scaffolds:
        if not (REPO_ROOT / scaffold).exists():
            errors.append(f"existing repo scaffold does not exist: {scaffold}")

    not_allowed = set(data.get("not_allowed", []))
    if not REQUIRED_NOT_ALLOWED.issubset(not_allowed):
        errors.append(f"not_allowed missing {sorted(REQUIRED_NOT_ALLOWED - not_allowed)}")

    acceptance = data.get("acceptance_result", {})
    if acceptance.get("local_contract_complete") is not True:
        errors.append("acceptance_result.local_contract_complete must be true")
    if acceptance.get("external_dns_configured") is not False:
        errors.append("acceptance_result.external_dns_configured must be false")
    if acceptance.get("external_tls_configured") is not False:
        errors.append("acceptance_result.external_tls_configured must be false")
    if acceptance.get("go_live_ready") is not False:
        errors.append("acceptance_result.go_live_ready must be false")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-or-IP-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_contract(load_contract())
    if errors:
        print("S1-INFRA-004 DNS/TLS contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("S1-INFRA-004 DNS/TLS contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
