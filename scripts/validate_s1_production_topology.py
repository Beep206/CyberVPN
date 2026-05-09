#!/usr/bin/env python3
"""Validate the Stage 1 production topology contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_PATH = REPO_ROOT / "infra" / "topology" / "stage1-production-topology.json"

REQUIRED_DECISIONS = {
    "DEC-S1-001",
    "DEC-S1-002",
    "DEC-S1-003",
    "DEC-S1-004",
    "DEC-S1-005",
    "DEC-S1-006",
    "DEC-S1-007",
    "DEC-S1-014",
    "DEC-S1-015",
    "DEC-S1-017",
}
REQUIRED_ENVIRONMENTS = {"local", "staging", "production"}
REQUIRED_NETWORK_ZONES = {
    "public_edge",
    "container_runtime",
    "private_data",
    "vpn_control",
    "vpn_transport",
    "observability",
}
REQUIRED_COMPONENTS = {
    "edge_tls_waf",
    "frontend_web",
    "admin_web",
    "backend_api",
    "telegram_bot",
    "worker_scheduler",
    "managed_postgresql",
    "private_valkey",
    "remnawave_control_plane",
    "vpn_nodes",
    "observability_stack",
    "backup_storage",
}
REQUIRED_INGRESS = {
    "public_site_primary",
    "public_site_mirror",
    "api_public",
    "oauth_web_callbacks",
    "admin_primary",
    "admin_mirror",
    "telegram_webhook",
    "payment_webhooks",
}
REQUIRED_EVIDENCE_TERMS = {
    "staging_environment_health_evidence",
    "production_environment_deployability_checklist",
    "dns_tls_redirect_evidence_for_primary_and_mirror_domains",
    "protected_admin_ingress_evidence",
    "managed_postgresql_private_access_backup_restore_evidence",
    "private_valkey_memory_policy_monitoring_evidence",
    "separate_staging_and_production_remnawave_health_evidence",
    "observability_live_target_dashboard_alert_delivery_evidence",
    "rollback_dry_run_on_final_rc_artifacts",
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


def load_topology(path: Path = TOPOLOGY_PATH) -> dict[str, Any]:
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


def validate_topology(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-001":
        errors.append("backlog_id must be S1-INFRA-001")
    if data.get("status") != "local_topology_spec_external_evidence_required":
        errors.append("status must mark this as local spec with external evidence still required")
    if data.get("topology_name") != "Simple Controlled Hybrid Container Topology":
        errors.append("topology_name must match the owner-approved decision")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references must include {sorted(REQUIRED_DECISIONS)}")

    environments = data.get("environments", [])
    environment_ids = _ids(environments)
    if not REQUIRED_ENVIRONMENTS.issubset(environment_ids):
        errors.append(f"environments must include {sorted(REQUIRED_ENVIRONMENTS)}")
    for env_id in ("staging", "production"):
        env = _by_id(environments, env_id)
        if env.get("may_use_home_lab") is not False:
            errors.append(f"{env_id} must not use home lab for S1 authority")
        if env.get("required_before_go_live") is not True:
            errors.append(f"{env_id} must be required before go-live")

    if not REQUIRED_NETWORK_ZONES.issubset(_ids(data.get("network_zones", []))):
        errors.append(f"network_zones must include {sorted(REQUIRED_NETWORK_ZONES)}")

    components = data.get("components", [])
    component_ids = _ids(components)
    if not REQUIRED_COMPONENTS.issubset(component_ids):
        errors.append(f"components must include {sorted(REQUIRED_COMPONENTS)}")

    for component in components:
        if component.get("production_critical") is True and component.get("home_lab_allowed") is not False:
            errors.append(f"production-critical component {component.get('id')} must not be home-lab allowed")

    postgres = _by_id(components, "managed_postgresql")
    if postgres.get("version_family") != "17.x":
        errors.append("managed_postgresql must be version_family 17.x")
    postgres_requirements = set(postgres.get("requirements", []))
    for requirement in {
        "private_only",
        "staging_separate_from_production",
        "separate_db_and_users_for_cybervpn_and_remnawave",
        "daily_encrypted_backups_14_days",
    }:
        if requirement not in postgres_requirements:
            errors.append(f"managed_postgresql missing requirement {requirement}")

    valkey = _by_id(components, "private_valkey")
    if valkey.get("durable_source_of_truth") is not False:
        errors.append("private_valkey must not be durable source of truth")
    valkey_requirements = set(valkey.get("requirements", []))
    if "critical_jobs_recover_from_postgresql" not in valkey_requirements:
        errors.append("private_valkey must require critical job recovery from PostgreSQL")

    remnawave = _by_id(components, "remnawave_control_plane")
    if remnawave.get("public") is not False:
        errors.append("remnawave_control_plane API must not be public")
    if "private_internal_api" not in set(remnawave.get("requirements", [])):
        errors.append("remnawave_control_plane must require private_internal_api")

    ingress = data.get("public_ingress", [])
    if not REQUIRED_INGRESS.issubset(_ids(ingress)):
        errors.append(f"public_ingress must include {sorted(REQUIRED_INGRESS)}")
    ingress_hosts = {host for item in ingress for host in item.get("hosts", [])}
    for host in {"cyber-vpn.net", "cyber-vpn.org", "admin.cyber-vpn.net", "admin.cyber-vpn.org", "api.cyber-vpn.net"}:
        if host not in ingress_hosts:
            errors.append(f"public_ingress hosts must include {host}")

    admin_primary = _by_id(ingress, "admin_primary")
    admin_controls = set(admin_primary.get("required_controls", []))
    for control in {"cloudflare_access_or_ip_allowlist_or_equivalent", "admin_2fa", "rbac", "audit_log"}:
        if control not in admin_controls:
            errors.append(f"admin_primary missing control {control}")

    for ingress_id in ("payment_webhooks", "telegram_webhook", "oauth_web_callbacks"):
        controls = set(_by_id(ingress, ingress_id).get("required_controls", []))
        if "no_interactive_edge_challenge" not in controls:
            errors.append(f"{ingress_id} must require no_interactive_edge_challenge")

    private_edges = {(edge.get("from"), edge.get("to")) for edge in data.get("private_dependencies", [])}
    for edge in {
        ("backend_api", "managed_postgresql"),
        ("backend_api", "private_valkey"),
        ("backend_api", "remnawave_control_plane"),
        ("worker_scheduler", "managed_postgresql"),
        ("telegram_bot", "backend_api"),
        ("remnawave_control_plane", "managed_postgresql"),
    }:
        if edge not in private_edges:
            errors.append(f"private_dependencies missing {edge[0]} -> {edge[1]}")

    home_forbidden = set(data.get("home_lab_boundary", {}).get("forbidden_for_s1_production", []))
    for forbidden in {"backend_api", "production_postgresql", "production_remnawave_control_plane", "vpn_exit_node"}:
        if forbidden not in home_forbidden:
            errors.append(f"home_lab_boundary must forbid {forbidden}")

    out_of_scope = set(data.get("out_of_scope_runtime", []))
    for item in {
        "partner_portal_public_launch",
        "helix_verta_beep_production_transport",
        "kubernetes_talos_gitops_required_path",
        "home_server_production_critical_path",
    }:
        if item not in out_of_scope:
            errors.append(f"out_of_scope_runtime must include {item}")

    deployment_rules = set(data.get("deployment_rules", []))
    if "deploy_by_immutable_tag_or_commit_sha_only" not in deployment_rules:
        errors.append("deployment_rules must require immutable tag or commit SHA")
    if "do_not_deploy_floating_main" not in deployment_rules:
        errors.append("deployment_rules must forbid floating main deploys")

    evidence = set(data.get("evidence_required_before_go_live", []))
    if not REQUIRED_EVIDENCE_TERMS.issubset(evidence):
        errors.append(f"evidence_required_before_go_live missing {sorted(REQUIRED_EVIDENCE_TERMS - evidence)}")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-or-IP-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_topology(load_topology())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {TOPOLOGY_PATH.relative_to(REPO_ROOT)} is valid for S1-INFRA-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
