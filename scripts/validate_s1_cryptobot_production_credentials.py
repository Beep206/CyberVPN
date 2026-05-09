#!/usr/bin/env python3
"""Validate the Stage 1 CryptoBot production credential inventory contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "infra" / "payments" / "stage1-cryptobot-production-credentials-contract.json"

REQUIRED_DECISIONS = {
    "DEC-S1-008",
    "DEC-S1-010",
    "DEC-S1-011",
    "DEC-S1-014",
    "DEC-S1-017",
    "DEC-S1-020",
}
REQUIRED_RUNTIME_COMPONENTS = {"backend_api", "task_worker", "telegram_bot"}
REQUIRED_EXTERNAL_EVIDENCE = {
    "CryptoBot production app/account ownership proof without secret values",
    "production CRYPTOBOT_TOKEN stored in approved secret store without value disclosure",
    "runtime env references prove backend_api receives CRYPTOBOT_TOKEN and CRYPTOBOT_NETWORK=mainnet",
    (
        "runtime env references prove task_worker receives CRYPTOBOT_TOKEN and CRYPTOBOT_NETWORK=mainnet "
        "if reconciliation/verification jobs use CryptoBot"
    ),
    (
        "runtime env references prove telegram_bot receives CRYPTOBOT_TOKEN only if CryptoBot gateway is enabled "
        "for Telegram surface"
    ),
    "secret access matrix showing legal seller/project owner and limited technical runtime access",
    "rotation procedure and emergency revoke procedure",
    "production callback/webhook registration proof without token values",
    "low-value production smoke or approved provider account proof before real paid beta traffic",
}
REQUIRED_NOT_ALLOWED = {
    "commit_cryptobot_token_or_provider_secret_values",
    "generate_fake_cryptobot_token_for_production",
    "use_placeholder_or_test_token_in_production",
    "use_testnet_network_in_production",
    "share_staging_and_production_provider_credentials",
    "enable_paid_beta_without_secret_store_evidence",
    "enable_paid_beta_without_provider_account_ownership_evidence",
    "enable_paid_beta_without_webhook_callback_registration_evidence",
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


def _inventory(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("secret_name"): item for item in data.get("credential_inventory_without_values", [])}


def _runtime_components(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item.get("component"): item for item in data.get("runtime_guards", [])}


def validate_contract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-PAY-003":
        errors.append("backlog_id must be S1-PAY-003")
    if data.get("provider") != "cryptobot":
        errors.append("provider must be cryptobot")
    if data.get("status") != "local_production_credential_inventory_complete_real_secret_storage_evidence_required":
        errors.append("status must show local credential inventory with real storage evidence still required")
    if data.get("next_backlog_id") != "S1-PAY-004":
        errors.append("next_backlog_id must be S1-PAY-004")
    if data.get("paid_beta_clearance") is not False:
        errors.append("paid_beta_clearance must remain false")
    if data.get("production_enablement_allowed") is not False:
        errors.append("production_enablement_allowed must remain false")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    source = data.get("official_source", {})
    if source.get("production_base_url") != "https://pay.crypt.bot/api":
        errors.append("official_source.production_base_url must match Crypto Pay production API")
    if source.get("credential_transport") != "Crypto-Pay-API-Token header":
        errors.append("official_source.credential_transport must be Crypto-Pay-API-Token header")

    inventory = _inventory(data)
    if set(inventory) != {"CRYPTOBOT_TOKEN", "CRYPTOBOT_NETWORK"}:
        errors.append("credential_inventory_without_values must include CRYPTOBOT_TOKEN and CRYPTOBOT_NETWORK only")
    token = inventory.get("CRYPTOBOT_TOKEN", {})
    if token.get("value_recorded_in_repo") is not False:
        errors.append("CRYPTOBOT_TOKEN value_recorded_in_repo must be false")
    if token.get("placeholder_allowed_in_production") is not False:
        errors.append("CRYPTOBOT_TOKEN placeholder_allowed_in_production must be false")
    if token.get("required_storage") != "approved_production_secret_store_or_restricted_runtime_env":
        errors.append("CRYPTOBOT_TOKEN required_storage must use approved production secret storage")

    network = inventory.get("CRYPTOBOT_NETWORK", {})
    if network.get("required_value") != "mainnet":
        errors.append("CRYPTOBOT_NETWORK required_value must be mainnet")
    if network.get("testnet_allowed_in_production") is not False:
        errors.append("CRYPTOBOT_NETWORK testnet_allowed_in_production must be false")

    components = _runtime_components(data)
    if not REQUIRED_RUNTIME_COMPONENTS.issubset(components):
        errors.append(f"runtime_guards missing {sorted(REQUIRED_RUNTIME_COMPONENTS - set(components))}")
    for component_name in ("backend_api", "task_worker"):
        component = components.get(component_name, {})
        for key in (
            "production_requires_cryptobot_token",
            "production_rejects_placeholder_token",
            "production_rejects_testnet_network",
        ):
            if component.get(key) is not True:
                errors.append(f"{component_name}.{key} must be true")
    telegram = components.get("telegram_bot", {})
    if telegram.get("production_requires_cryptobot_token_when_gateway_enabled") is not True:
        errors.append("telegram_bot must require CRYPTOBOT_TOKEN when CryptoBot gateway is enabled")
    if telegram.get("production_rejects_placeholder_token") is not True:
        errors.append("telegram_bot.production_rejects_placeholder_token must be true")

    local = data.get("local_contract_evidence", {})
    for key in (
        "credential_inventory_without_values_complete",
        "placeholder_generation_disabled",
        "backend_placeholder_guard",
        "task_worker_placeholder_guard",
        "telegram_bot_placeholder_guard",
        "production_mainnet_guard",
    ):
        if local.get(key) is not True:
            errors.append(f"local_contract_evidence.{key} must be true")
    for key in (
        "real_production_credential_value_present_in_repo",
        "real_provider_account_evidence_available",
        "real_secret_store_screenshot_or_transcript_available",
        "real_production_callback_evidence_available",
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

    print(f"{CONTRACT_PATH.relative_to(REPO_ROOT)} is valid for S1-PAY-003")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
