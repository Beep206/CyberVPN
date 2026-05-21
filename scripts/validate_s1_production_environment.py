#!/usr/bin/env python3
"""Validate the Stage 1 production environment deployability contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATH = REPO_ROOT / "infra" / "topology" / "stage1-production-environment.json"

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
REQUIRED_SERVICES = {
    "production_edge",
    "production_frontend_web",
    "production_admin_web",
    "production_backend_api",
    "production_worker_scheduler",
    "production_telegram_bot",
    "production_postgresql",
    "production_valkey",
    "production_remnawave_control_plane",
    "production_vpn_nodes",
    "production_observability",
    "production_backup_storage",
}
REQUIRED_SEPARATION = {
    "database_instances_or_databases_are_not_shared_with_staging",
    "database_users_are_not_shared_with_staging",
    "valkey_instance_or_namespace_is_not_shared_with_staging",
    "remnawave_instance_is_not_shared_with_staging",
    "telegram_bot_token_is_not_shared_with_staging",
    "oauth_apps_are_not_shared_with_staging",
    "enabled_payment_provider_credentials_are_not_staging_sandbox_credentials",
    "jwt_totp_encryption_webhook_secrets_are_unique_to_production",
    "sentry_or_observability_dsn_is_not_shared_with_staging",
    "container_images_are_referenced_by_immutable_tag_or_digest",
}
REQUIRED_INGRESS = {
    "production_site_primary",
    "production_site_primary_www",
    "production_org_reserved",
    "production_org_www_reserved",
    "production_api",
    "production_admin_primary",
    "production_admin_org_reserved",
    "production_telegram_webhook",
    "production_payment_webhooks",
    "production_oauth_callbacks",
}
REQUIRED_PREFLIGHT = {
    "fresh_dirty_worktree_scope_map_approved",
    "immutable_release_tag_or_commit_sha_selected",
    "production_image_digests_recorded",
    "production_config_rendered_without_staging_secrets",
    "redacted_production_secret_inventory_without_values",
    "production_environment_contract_validates",
    "clean_migration_plan_and_pre_deploy_backup_recorded",
    "rollback_command_and_release_pointer_recorded",
    "registration_payments_trial_provisioning_kill_switches_validated",
    "dns_tls_redirect_plan_recorded",
    "observability_targets_and_alert_routes_recorded",
    "backup_restore_drill_plan_recorded",
}
REQUIRED_KILL_SWITCHES = {
    "registration",
    "payments",
    "trial",
    "provisioning",
    "telegram_stars",
    "referral",
    "promo",
    "gift",
    "addons",
    "oauth",
    "magic_link_otp",
}
REQUIRED_EXTERNAL_EVIDENCE = {
    "provider_or_hosting_account_recorded_without_secrets",
    "production_public_origins_recorded",
    "production_private_network_boundary_recorded",
    "production_dns_tls_redirect_evidence",
    "production_backend_health_and_readiness_evidence",
    "production_postgresql_private_access_clean_migration_backup_restore_evidence",
    "production_valkey_private_access_memory_monitoring_evidence",
    "production_remnawave_health_node_profile_inbound_evidence",
    "production_botfather_webhook_miniapp_evidence",
    "live_payment_provider_callback_signature_idempotency_evidence",
    "production_observability_alert_delivery_evidence",
    "production_rollback_dry_run_evidence",
    "redacted_production_secrets_inventory_without_values",
    "production_first_admin_bootstrap_2fa_audit_evidence",
    "final_rc_artifact_security_scan_evidence",
}
REQUIRED_SCAFFOLDS = {
    "infra/terraform/live/production/foundation",
    "infra/terraform/live/production/prod-mgmt",
    "infra/terraform/live/production/edge",
    "infra/terraform/live/production/dns",
    "infra/terraform/live/production/control-plane",
    "infra/scripts/prod_mgmt_bootstrap.py",
    "infra/topology/stage1-production-topology.json",
    "infra/topology/stage1-staging-environment.json",
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


def load_production(path: Path = PRODUCTION_PATH) -> dict[str, Any]:
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


def _require_controls(errors: list[str], ingress_item: dict[str, Any], required: set[str]) -> None:
    controls = set(ingress_item.get("required_controls", []))
    if not required.issubset(controls):
        ingress_id = ingress_item.get("id", "<missing>")
        errors.append(f"{ingress_id} missing controls {sorted(required - controls)}")


def validate_production(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-003":
        errors.append("backlog_id must be S1-INFRA-003")
    expected_status = "local_production_deployability_contract_external_environment_required"
    if data.get("status") != expected_status:
        errors.append("status must mark this as local production deployability with external evidence required")
    if not {"S1-INFRA-001", "S1-INFRA-002"}.issubset(set(data.get("depends_on", []))):
        errors.append("production environment contract must depend on S1-INFRA-001 and S1-INFRA-002")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    authority = data.get("authority", {})
    if authority.get("production_authority_when_evidence_complete") is not True:
        errors.append("production authority must be true only after evidence is complete")
    if authority.get("go_live_clearance") is not False:
        errors.append("local production contract must not grant go-live clearance")
    if authority.get("external_production_created") is not False:
        errors.append("external_production_created must remain false until live production exists")
    if authority.get("must_not_use_staging_credentials") is not True:
        errors.append("production must not use staging credentials")
    if authority.get("must_not_share_state_with_staging") is not True:
        errors.append("production must not share state with staging")
    if authority.get("may_use_home_lab_as_authority") is not False:
        errors.append("home lab must not be production authority for S1")
    if authority.get("deploy_by_immutable_tag_or_commit_sha_only") is not True:
        errors.append("production deploy must use immutable tag or commit sha only")
    if authority.get("floating_main_allowed") is not False:
        errors.append("floating main deploys must be forbidden")

    services = data.get("required_services", [])
    service_ids = _ids(services)
    if not REQUIRED_SERVICES.issubset(service_ids):
        errors.append(f"required_services missing {sorted(REQUIRED_SERVICES - service_ids)}")
    for service in services:
        service_id = service.get("id")
        if service.get("must_be_separate_from_staging") is not True:
            errors.append(f"{service_id} must be separate from staging")
        if service.get("external_required") is not True:
            errors.append(f"{service_id} must require external production evidence")
        if not service.get("health_evidence"):
            errors.append(f"{service_id} must define health_evidence")

    postgresql = _by_id(services, "production_postgresql")
    if postgresql.get("version_family") != "17.x":
        errors.append("production_postgresql must use PostgreSQL 17.x")
    for evidence in {
        "private_access_only",
        "clean_migration_transcript",
        "separate_cybervpn_db_user",
        "separate_remnawave_db_user",
        "encrypted_backup_config_recorded",
        "restore_drill_transcript",
    }:
        if evidence not in set(postgresql.get("health_evidence", [])):
            errors.append(f"production_postgresql missing health evidence {evidence}")

    valkey = _by_id(services, "production_valkey")
    if valkey.get("durable_source_of_truth") is not False:
        errors.append("production_valkey must not be durable source of truth")

    remnawave = _by_id(services, "production_remnawave_control_plane")
    if remnawave.get("public") is not False:
        errors.append("production_remnawave_control_plane must not expose public API")
    if remnawave.get("data_lifecycle") != "authoritative_production":
        errors.append("production_remnawave_control_plane must be authoritative production data")

    vpn_nodes = _by_id(services, "production_vpn_nodes")
    if vpn_nodes.get("home_lab_allowed") is not False:
        errors.append("production VPN nodes must not run from home lab")
    if vpn_nodes.get("customer_production_traffic_allowed") is not True:
        errors.append("production VPN nodes must be the only customer-production-traffic node class")

    backup = _by_id(services, "production_backup_storage")
    if backup.get("encrypted") is not True:
        errors.append("production_backup_storage must be encrypted")
    if backup.get("off_host") is not True:
        errors.append("production_backup_storage must be off-host")
    if int(backup.get("retention_days", 0)) < 14:
        errors.append("production_backup_storage retention must be at least 14 days")

    separation = set(data.get("required_environment_separation", []))
    if not REQUIRED_SEPARATION.issubset(separation):
        errors.append(f"required_environment_separation missing {sorted(REQUIRED_SEPARATION - separation)}")

    ingress = data.get("production_public_ingress", [])
    ingress_ids = _ids(ingress)
    if not REQUIRED_INGRESS.issubset(ingress_ids):
        errors.append(f"production_public_ingress missing {sorted(REQUIRED_INGRESS - ingress_ids)}")
    expected_hosts = {
        "production_site_primary": "cyber-vpn.net",
        "production_site_primary_www": "www.cyber-vpn.net",
        "production_org_reserved": "cyber-vpn.org",
        "production_org_www_reserved": "www.cyber-vpn.org",
        "production_api": "api.cyber-vpn.net",
        "production_admin_primary": "admin.cyber-vpn.net",
        "production_admin_org_reserved": "admin.cyber-vpn.org",
    }
    for ingress_id, expected_host in expected_hosts.items():
        ingress_item = _by_id(ingress, ingress_id)
        if ingress_item.get("host") != expected_host:
            errors.append(f"{ingress_id} host must be {expected_host}")

    _require_controls(errors, _by_id(ingress, "production_payment_webhooks"), {"no_interactive_edge_challenge"})
    _require_controls(errors, _by_id(ingress, "production_payment_webhooks"), {"provider_signature_or_recheck"})
    _require_controls(errors, _by_id(ingress, "production_telegram_webhook"), {"no_interactive_edge_challenge"})
    _require_controls(errors, _by_id(ingress, "production_admin_primary"), {"admin_2fa", "rbac", "audit_log"})
    _require_controls(errors, _by_id(ingress, "production_admin_org_reserved"), {"no_public_admin_login"})

    preflight = set(data.get("deployability_preflight", []))
    if not REQUIRED_PREFLIGHT.issubset(preflight):
        errors.append(f"deployability_preflight missing {sorted(REQUIRED_PREFLIGHT - preflight)}")

    kill_switches = set(data.get("kill_switches_required", []))
    if not REQUIRED_KILL_SWITCHES.issubset(kill_switches):
        errors.append(f"kill_switches_required missing {sorted(REQUIRED_KILL_SWITCHES - kill_switches)}")

    scaffolds = set(data.get("existing_repo_scaffolds", []))
    if not REQUIRED_SCAFFOLDS.issubset(scaffolds):
        errors.append(f"existing_repo_scaffolds missing {sorted(REQUIRED_SCAFFOLDS - scaffolds)}")
    for scaffold in sorted(scaffolds):
        if not (REPO_ROOT / scaffold).exists():
            errors.append(f"existing repo scaffold does not exist: {scaffold}")

    external_evidence = set(data.get("evidence_required_to_close_external_production", []))
    if not REQUIRED_EXTERNAL_EVIDENCE.issubset(external_evidence):
        missing = sorted(REQUIRED_EXTERNAL_EVIDENCE - external_evidence)
        errors.append(f"evidence_required_to_close_external_production missing {missing}")

    not_allowed = set(data.get("not_allowed_for_production", []))
    for item in {
        "staging_payment_credentials",
        "staging_telegram_bot_token",
        "staging_remnawave_api_token",
        "home_lab_as_production_authority",
        "floating_main_deploy",
        "production_secrets_in_repository",
        "production_customer_traffic_before_go_no_go",
    }:
        if item not in not_allowed:
            errors.append(f"not_allowed_for_production must include {item}")

    acceptance = data.get("acceptance_result", {})
    if acceptance.get("local_contract_complete") is not True:
        errors.append("acceptance_result.local_contract_complete must be true")
    if acceptance.get("external_production_created") is not False:
        errors.append("acceptance_result.external_production_created must be false until live proof exists")
    if acceptance.get("staging_credentials_allowed") is not False:
        errors.append("acceptance_result.staging_credentials_allowed must be false")
    if acceptance.get("go_live_ready") is not False:
        errors.append("acceptance_result.go_live_ready must be false until external evidence exists")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-or-IP-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_production(load_production())
    if errors:
        print("S1-INFRA-003 production environment validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("S1-INFRA-003 production environment validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
