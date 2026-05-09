#!/usr/bin/env python3
"""Validate the Stage 1 staging environment contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_PATH = REPO_ROOT / "infra" / "topology" / "stage1-staging-environment.json"

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
    "staging_edge",
    "staging_frontend_web",
    "staging_admin_web",
    "staging_backend_api",
    "staging_worker_scheduler",
    "staging_telegram_bot",
    "staging_postgresql",
    "staging_valkey",
    "staging_remnawave_control_plane",
    "staging_vpn_test_node",
    "staging_observability",
}
REQUIRED_SEPARATION = {
    "database_instances_or_databases_are_not_shared_with_production",
    "database_users_are_not_shared_with_production",
    "valkey_instance_or_namespace_is_not_shared_with_production",
    "remnawave_instance_is_not_shared_with_production",
    "telegram_bot_token_is_not_shared_with_production",
    "oauth_apps_are_not_shared_with_production",
    "payment_provider_credentials_are_sandbox_or_test_mode",
    "jwt_totp_encryption_webhook_secrets_are_unique_to_staging",
    "sentry_or_observability_dsn_is_not_shared_with_production",
}
REQUIRED_INGRESS = {
    "staging_site",
    "staging_api",
    "staging_admin",
    "staging_telegram_webhook",
    "staging_payment_webhooks",
}
REQUIRED_E2E = {
    "registration_or_login",
    "trial_activation",
    "trial_to_remnawave_provisioning",
    "qr_subscription_url_config_delivery",
    "sandbox_or_test_payment_success",
    "duplicate_webhook_no_duplicate_side_effects",
    "payment_success_remnawave_failure_retry",
    "expiry_grace_worker_behavior",
    "telegram_bot_miniapp_equivalent_flow",
    "admin_support_safe_inspection",
    "alert_delivery_for_payment_or_provisioning_failure",
    "logs_sentry_no_secret_config_link_leak",
}
REQUIRED_EXTERNAL_EVIDENCE = {
    "provider_or_hosting_account_recorded_without_secrets",
    "staging_public_origins_recorded",
    "staging_private_network_boundary_recorded",
    "staging_dns_tls_redirect_evidence",
    "staging_backend_health_and_readiness_evidence",
    "staging_postgresql_private_access_clean_migration_backup_evidence",
    "staging_valkey_private_access_memory_monitoring_evidence",
    "staging_remnawave_health_node_profile_inbound_evidence",
    "staging_botfather_webhook_miniapp_evidence",
    "staging_payment_sandbox_callback_signature_idempotency_evidence",
    "staging_observability_alert_delivery_evidence",
    "staging_rollback_dry_run_evidence",
    "redacted_staging_secrets_inventory_without_values",
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


def load_staging(path: Path = STAGING_PATH) -> dict[str, Any]:
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


def validate_staging(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-INFRA-002":
        errors.append("backlog_id must be S1-INFRA-002")
    if data.get("status") != "local_staging_contract_external_environment_required":
        errors.append("status must mark this as a local staging contract with external evidence still required")
    if "S1-INFRA-001" not in set(data.get("depends_on", [])):
        errors.append("staging contract must depend on S1-INFRA-001")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    authority = data.get("authority", {})
    if authority.get("go_live_clearance") is not False:
        errors.append("staging contract must not grant go-live clearance")
    if authority.get("must_not_use_production_credentials") is not True:
        errors.append("staging must not use production credentials")
    if authority.get("must_not_share_state_with_production") is not True:
        errors.append("staging must not share state with production")
    if authority.get("may_use_home_lab_as_authority") is not False:
        errors.append("home lab must not be staging authority for S1")

    services = data.get("required_services", [])
    service_ids = _ids(services)
    if not REQUIRED_SERVICES.issubset(service_ids):
        errors.append(f"required_services missing {sorted(REQUIRED_SERVICES - service_ids)}")
    for service in services:
        service_id = service.get("id")
        if service.get("must_be_separate_from_production") is not True:
            errors.append(f"{service_id} must be separate from production")
        if service.get("external_required") is not True:
            errors.append(f"{service_id} must require external/live staging evidence")
        if not service.get("health_evidence"):
            errors.append(f"{service_id} must define health_evidence")

    postgresql = _by_id(services, "staging_postgresql")
    if postgresql.get("version_family") != "17.x":
        errors.append("staging_postgresql must use PostgreSQL 17.x")
    for evidence in {
        "private_access_only",
        "clean_migration_transcript",
        "separate_cybervpn_db_user",
        "separate_remnawave_db_user",
        "backup_config_recorded",
    }:
        if evidence not in set(postgresql.get("health_evidence", [])):
            errors.append(f"staging_postgresql missing health evidence {evidence}")

    valkey = _by_id(services, "staging_valkey")
    if valkey.get("durable_source_of_truth") is not False:
        errors.append("staging_valkey must not be durable source of truth")

    remnawave = _by_id(services, "staging_remnawave_control_plane")
    if remnawave.get("public") is not False:
        errors.append("staging_remnawave_control_plane must not expose public API")
    if remnawave.get("data_lifecycle") != "disposable":
        errors.append("staging_remnawave_control_plane must use disposable data")

    separation = set(data.get("required_environment_separation", []))
    if not REQUIRED_SEPARATION.issubset(separation):
        errors.append(f"required_environment_separation missing {sorted(REQUIRED_SEPARATION - separation)}")

    ingress = data.get("staging_public_ingress", [])
    ingress_ids = _ids(ingress)
    if not REQUIRED_INGRESS.issubset(ingress_ids):
        errors.append(f"staging_public_ingress missing {sorted(REQUIRED_INGRESS - ingress_ids)}")
    for ingress_id in REQUIRED_INGRESS:
        ingress_item = _by_id(ingress, ingress_id)
        if ingress_item.get("host_status") != "to_be_selected_before_external_staging":
            errors.append(f"{ingress_id} host_status must remain explicit until external staging")

    e2e = set(data.get("required_stage1_e2e_flows", []))
    if not REQUIRED_E2E.issubset(e2e):
        errors.append(f"required_stage1_e2e_flows missing {sorted(REQUIRED_E2E - e2e)}")

    external_evidence = set(data.get("evidence_required_to_close_external_staging", []))
    if not REQUIRED_EXTERNAL_EVIDENCE.issubset(external_evidence):
        missing = sorted(REQUIRED_EXTERNAL_EVIDENCE - external_evidence)
        errors.append(f"evidence_required_to_close_external_staging missing {missing}")

    not_allowed = set(data.get("not_allowed_for_staging", []))
    for item in {
        "production_user_data",
        "production_payment_credentials",
        "production_telegram_bot_token",
        "production_remnawave_api_token",
        "production_customer_traffic",
        "home_lab_as_staging_authority",
        "floating_main_deploy",
    }:
        if item not in not_allowed:
            errors.append(f"not_allowed_for_staging must include {item}")

    acceptance = data.get("acceptance_result", {})
    if acceptance.get("local_contract_complete") is not True:
        errors.append("acceptance_result.local_contract_complete must be true")
    if acceptance.get("external_staging_created") is not False:
        errors.append("acceptance_result.external_staging_created must be false until live proof exists")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-or-IP-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_staging(load_staging())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {STAGING_PATH.relative_to(REPO_ROOT)} is valid for S1-INFRA-002")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
