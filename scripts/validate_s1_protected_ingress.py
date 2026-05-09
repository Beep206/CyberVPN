#!/usr/bin/env python3
"""Validate the Stage 1 protected ingress contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
INGRESS_PATH = REPO_ROOT / "infra" / "ingress" / "stage1-protected-ingress-contract.json"

REQUIRED_DEPENDENCIES = {
    "S1-INFRA-001",
    "S1-INFRA-003",
    "S1-INFRA-004",
    "S1-INFRA-008",
    "S1-BE-003",
    "S1-BE-004",
    "S1-BE-005",
    "S1-ADM-001",
    "S1-AUTH-004",
}
REQUIRED_ENTRYPOINTS = {
    "public_site_primary",
    "public_site_www",
    "public_site_mirror",
    "public_site_mirror_www",
    "public_api",
    "payment_webhooks",
    "telegram_webhook",
    "oauth_callbacks",
    "admin_primary",
    "admin_mirror",
}
REQUIRED_HOSTS = {
    "cyber-vpn.net",
    "www.cyber-vpn.net",
    "cyber-vpn.org",
    "www.cyber-vpn.org",
    "api.cyber-vpn.net",
    "admin.cyber-vpn.net",
    "admin.cyber-vpn.org",
}
REQUIRED_PRIVATE_COMPONENTS = {
    "backend_container_port",
    "admin_container_port",
    "worker_scheduler",
    "telegram_bot_runtime",
    "remnawave_control_plane_api",
    "postgresql",
    "valkey",
    "metrics_and_traces",
}
REQUIRED_BLOCKED_POLICIES = {
    "block_admin_paths_on_customer_web",
    "block_docs_in_production",
    "block_internal_api_publicly",
}
REQUIRED_NOT_ALLOWED = {
    "direct_public_backend_origin",
    "direct_public_admin_origin_without_access_gate",
    "independent_admin_session_on_admin_cyber_vpn_org",
    "admin_api_served_from_customer_domain_without_host_guard",
    "public_remnawave_api",
    "public_postgresql",
    "public_valkey",
    "public_metrics_or_traces",
    "interactive_challenge_on_payment_webhooks",
    "interactive_challenge_on_telegram_webhook",
    "interactive_challenge_on_oauth_callbacks",
    "staging_origin_for_customer_production_traffic",
    "home_lab_origin_for_customer_production_traffic",
    "floating_main_ingress_deploy",
}
REQUIRED_EVIDENCE_TERMS = {
    "edge route inventory",
    "redacted reverse proxy configuration",
    "origin firewall or security-group proof",
    "admin.cyber-vpn.net Access/IP allowlist/private VPN proof",
    "payment webhook no interactive challenge proof",
    "Telegram webhook no interactive challenge proof",
    "OAuth callback no interactive challenge proof",
    "Remnawave API private/internal proof",
    "PostgreSQL private-only proof",
    "Valkey/Redis private-only proof",
    "admin 2FA/RBAC/audit smoke",
    "rollback route or release pointer proof",
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


def load_ingress(path: Path = INGRESS_PATH) -> dict[str, Any]:
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


def _require_controls(
    errors: list[str],
    entrypoint: dict[str, Any],
    required_controls: set[str],
) -> None:
    controls = set(entrypoint.get("required_controls", []))
    if not required_controls.issubset(controls):
        entrypoint_id = entrypoint.get("id", "<missing>")
        missing = sorted(required_controls - controls)
        errors.append(f"{entrypoint_id} missing controls {missing}")


def validate_ingress(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-005":
        errors.append("backlog_id must be S1-INFRA-005")
    expected_status = "local_protected_ingress_contract_external_deploy_required"
    if data.get("status") != expected_status:
        errors.append("status must mark this as local protected ingress contract")
    if data.get("provider") != "cloudflare_or_equivalent_edge_plus_reverse_proxy":
        errors.append("provider must be cloudflare_or_equivalent_edge_plus_reverse_proxy")

    dependencies = set(data.get("depends_on", []))
    if not REQUIRED_DEPENDENCIES.issubset(dependencies):
        missing = sorted(REQUIRED_DEPENDENCIES - dependencies)
        errors.append(f"depends_on missing {missing}")

    authority = data.get("authority", {})
    expected_false_flags = {
        "go_live_clearance",
        "external_ingress_deployed",
        "backend_direct_public_access_allowed",
        "admin_public_without_access_allowed",
        "admin_mirror_independent_session_allowed",
        "remnawave_api_public_allowed",
        "postgresql_public_allowed",
        "valkey_public_allowed",
        "metrics_public_allowed",
        "home_lab_customer_ingress_allowed",
        "floating_main_allowed",
    }
    for flag in expected_false_flags:
        if authority.get(flag) is not False:
            errors.append(f"authority.{flag} must be false")
    if authority.get("deploy_by_immutable_tag_or_commit_sha_only") is not True:
        errors.append("ingress deploy must use immutable tag or commit sha only")

    entrypoints = data.get("public_entrypoints", [])
    entrypoint_ids = _ids(entrypoints)
    if not REQUIRED_ENTRYPOINTS.issubset(entrypoint_ids):
        missing = sorted(REQUIRED_ENTRYPOINTS - entrypoint_ids)
        errors.append(f"public_entrypoints missing {missing}")

    hosts = {str(entrypoint.get("host", "")) for entrypoint in entrypoints}
    if not REQUIRED_HOSTS.issubset(hosts):
        missing = sorted(REQUIRED_HOSTS - hosts)
        errors.append(f"public_entrypoints missing hosts {missing}")

    public_api = _by_id(entrypoints, "public_api")
    _require_controls(
        errors,
        public_api,
        {
            "cors_allowlist",
            "csrf_for_cookie_flows",
            "swagger_disabled",
            "application_rate_limits",
            "edge_rate_limits",
            "admin_api_host_guard",
            "no_internal_routes",
        },
    )

    admin_primary = _by_id(entrypoints, "admin_primary")
    if admin_primary.get("public") is not False:
        errors.append("admin_primary public flag must be false until protected access is proven")
    _require_controls(
        errors,
        admin_primary,
        {
            "cloudflare_access_or_ip_allowlist_or_private_vpn",
            "admin_host_guard",
            "mandatory_admin_2fa",
            "rbac",
            "privileged_audit_log",
            "no_public_login_before_access_gate",
        },
    )

    admin_mirror = _by_id(entrypoints, "admin_mirror")
    _require_controls(
        errors,
        admin_mirror,
        {
            "redirect_to_admin_primary",
            "no_independent_session_cookie",
            "no_admin_backend_origin",
        },
    )

    for webhook_id in {"payment_webhooks", "telegram_webhook", "oauth_callbacks"}:
        webhook = _by_id(entrypoints, webhook_id)
        _require_controls(errors, webhook, {"no_interactive_edge_challenge"})
        if not webhook.get("paths"):
            errors.append(f"{webhook_id} must define paths")

    blocked_policies = _ids(data.get("blocked_public_paths", []))
    if not REQUIRED_BLOCKED_POLICIES.issubset(blocked_policies):
        missing = sorted(REQUIRED_BLOCKED_POLICIES - blocked_policies)
        errors.append(f"blocked_public_paths missing {missing}")

    private_components = data.get("private_only_components", [])
    private_ids = _ids(private_components)
    if not REQUIRED_PRIVATE_COMPONENTS.issubset(private_ids):
        missing = sorted(REQUIRED_PRIVATE_COMPONENTS - private_ids)
        errors.append(f"private_only_components missing {missing}")
    for component in private_components:
        component_id = component.get("id", "<missing>")
        if component.get("public_dns_allowed") is not False:
            errors.append(f"{component_id} public_dns_allowed must be false")
        if component.get("public_port_allowed") is not False:
            errors.append(f"{component_id} public_port_allowed must be false")
        if not component.get("reachable_only_from"):
            errors.append(f"{component_id} must define reachable_only_from")

    evidence = "\n".join(data.get("required_live_evidence_before_go_live", []))
    for term in REQUIRED_EVIDENCE_TERMS:
        if term not in evidence:
            errors.append(f"required_live_evidence_before_go_live must mention {term}")

    not_allowed = set(data.get("not_allowed", []))
    if not REQUIRED_NOT_ALLOWED.issubset(not_allowed):
        missing = sorted(REQUIRED_NOT_ALLOWED - not_allowed)
        errors.append(f"not_allowed missing {missing}")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_ingress(load_ingress())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("S1-INFRA-005 protected ingress contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
