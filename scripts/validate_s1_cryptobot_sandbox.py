#!/usr/bin/env python3
"""Validate the Stage 1 CryptoBot sandbox/testnet contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "infra" / "payments" / "stage1-cryptobot-sandbox-contract.json"

REQUIRED_DECISIONS = {
    "DEC-S1-008",
    "DEC-S1-009",
    "DEC-S1-010",
    "DEC-S1-013",
    "DEC-S1-017",
    "DEC-S1-020",
}
REQUIRED_COMPONENTS = {"backend_api", "task_worker", "telegram_bot"}
REQUIRED_EXTERNAL_EVIDENCE = {
    "@CryptoTestnetBot app/account ownership proof without secret values",
    "redacted testnet credential inventory through approved secret process",
    "successful testnet createInvoice sample with invoice URL redacted as needed",
    "testnet paid invoice status sample",
    "testnet expired invoice status sample as cancel-equivalent",
    "testnet invalid token or provider failure sample with no access granted",
    "valid crypto-pay-api-signature callback sample",
    "invalid signature rejection sample",
    "duplicate callback/idempotency proof against durable storage",
    "payment paid -> order/subscription -> Remnawave provisioning proof",
    "paid-but-no-access/orphan manual review proof within 24 hours",
}
REQUIRED_NOT_ALLOWED = {
    "enable_paid_beta_without_real_cryptobot_testnet_credentials",
    "enable_paid_beta_from_documentation_only_samples",
    "use_testnet_in_production",
    "allow_arbitrary_cryptobot_base_url_from_env",
    "commit_provider_secret_values_or_full_unredacted_invoice_urls",
    "map_active_or_expired_to_paid_access",
    "skip_webhook_signature_or_status_recheck_evidence",
    "leave_paid_but_no_access_orphan_payment_unreviewed_over_24h",
}
SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"password\s*[:=]\s*[^<\s][^\s]{8,}",
        r"api[_-]?token\s*[:=]\s*[a-z0-9_-]{16,}",
        r"secret\s*[:=]\s*[a-z0-9_-]{16,}",
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
        r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    )
]


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _network_modes(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("network"): item for item in data.get("runtime_network_modes", [])}


def _components(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("component"): item for item in data.get("runtime_components", [])}


def validate_contract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-PAY-002":
        errors.append("backlog_id must be S1-PAY-002")
    if data.get("provider") != "cryptobot":
        errors.append("provider must be cryptobot")
    if data.get("status") != "local_sandbox_runtime_contract_complete_external_testnet_evidence_required":
        errors.append("status must show local runtime contract with external testnet evidence still required")
    if data.get("next_backlog_id") != "S1-PAY-003":
        errors.append("next_backlog_id must be S1-PAY-003")
    if data.get("paid_beta_clearance") is not False:
        errors.append("paid_beta_clearance must be false until real provider evidence exists")
    if data.get("production_enablement_allowed") is not False:
        errors.append("production_enablement_allowed must be false until real provider evidence exists")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    source = data.get("official_source", {})
    if source.get("mainnet_base_url") != "https://pay.crypt.bot/api":
        errors.append("official_source.mainnet_base_url must match Crypto Pay mainnet API URL")
    if source.get("testnet_base_url") != "https://testnet-pay.crypt.bot/api":
        errors.append("official_source.testnet_base_url must match Crypto Pay testnet API URL")
    if set(source.get("invoice_statuses", [])) != {"active", "paid", "expired"}:
        errors.append("official_source.invoice_statuses must be active, paid and expired")
    if source.get("webhook_update_type_for_paid_invoice") != "invoice_paid":
        errors.append("official_source.webhook_update_type_for_paid_invoice must be invoice_paid")

    modes = _network_modes(data)
    if set(modes) != {"mainnet", "testnet"}:
        errors.append("runtime_network_modes must define mainnet and testnet only")
    else:
        if modes["mainnet"].get("base_url") != "https://pay.crypt.bot/api":
            errors.append("mainnet base_url must be https://pay.crypt.bot/api")
        if modes["mainnet"].get("production_allowed") is not True:
            errors.append("mainnet must be production_allowed")
        if modes["testnet"].get("base_url") != "https://testnet-pay.crypt.bot/api":
            errors.append("testnet base_url must be https://testnet-pay.crypt.bot/api")
        if modes["testnet"].get("production_allowed") is not False:
            errors.append("testnet must not be production_allowed")

    components = _components(data)
    if not REQUIRED_COMPONENTS.issubset(components):
        errors.append(f"runtime_components missing {sorted(REQUIRED_COMPONENTS - set(components))}")
    for component_name in ("backend_api", "task_worker"):
        component = components.get(component_name, {})
        if component.get("config_key") != "CRYPTOBOT_NETWORK":
            errors.append(f"{component_name}.config_key must be CRYPTOBOT_NETWORK")
        if component.get("default_network") != "mainnet":
            errors.append(f"{component_name}.default_network must be mainnet")
        if component.get("testnet_runtime_selectable") is not True:
            errors.append(f"{component_name}.testnet_runtime_selectable must be true")
        if component.get("production_rejects_testnet") is not True:
            errors.append(f"{component_name}.production_rejects_testnet must be true")
        if component.get("arbitrary_base_url_allowed") is not False:
            errors.append(f"{component_name}.arbitrary_base_url_allowed must be false")

    local = data.get("local_contract_evidence", {})
    for key in (
        "testnet_endpoint_selectable_without_real_credentials",
        "mainnet_endpoint_remains_default",
        "production_testnet_guard",
        "unknown_network_rejected",
    ):
        if local.get(key) is not True:
            errors.append(f"local_contract_evidence.{key} must be true")
    for key in (
        "real_testnet_credentials_available",
        "real_testnet_invoice_success_evidence_available",
        "real_testnet_invoice_failure_evidence_available",
        "real_testnet_invoice_expiry_or_cancel_equivalent_evidence_available",
        "real_testnet_webhook_signature_evidence_available",
    ):
        if local.get(key) is not False:
            errors.append(f"local_contract_evidence.{key} must be false")

    external = set(data.get("minimum_external_evidence_before_paid_beta", []))
    if not REQUIRED_EXTERNAL_EVIDENCE.issubset(external):
        missing = sorted(REQUIRED_EXTERNAL_EVIDENCE - external)
        errors.append(f"minimum_external_evidence_before_paid_beta missing {missing}")

    not_allowed = set(data.get("not_allowed", []))
    if not REQUIRED_NOT_ALLOWED.issubset(not_allowed):
        errors.append(f"not_allowed missing {sorted(REQUIRED_NOT_ALLOWED - not_allowed)}")

    for value in _walk_values(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                errors.append(f"secret-or-IP-looking value found: {value[:80]}")

    return errors


def main() -> int:
    errors = validate_contract(load_contract())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"{CONTRACT_PATH.relative_to(REPO_ROOT)} is valid for S1-PAY-002")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
