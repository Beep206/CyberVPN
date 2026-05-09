#!/usr/bin/env python3
"""Validate the Stage 1 primary payment provider selection contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "infra" / "payments" / "stage1-primary-payment-provider.json"

REQUIRED_DECISIONS = {
    "DEC-S1-008",
    "DEC-S1-009",
    "DEC-S1-010",
    "DEC-S1-011",
    "DEC-S1-013",
    "DEC-S1-014",
    "DEC-S1-017",
    "DEC-S1-020",
}
REQUIRED_PROVIDERS = {
    "cryptobot",
    "telegram_stars",
    "yookassa",
    "digiseller",
    "payram",
    "nowpayments",
}
REQUIRED_PRIMARY_EVIDENCE_TERMS = {
    "S1-PAY-002 sandbox/testnet success, failure and expiry samples for CryptoBot",
    "S1-PAY-003 production credential inventory without values",
    "provider callback/webhook URL registration for staging and production",
    "valid signature proof and invalid signature rejection proof",
    "duplicate callback proof under durable PostgreSQL/Valkey persistence",
    "payment paid -> subscription -> Remnawave provisioning proof",
    "paid-but-no-access/orphan alert and manual review proof",
    "refund or manual reconciliation proof",
    "admin/support payment-attempt visibility proof without raw provider secrets",
    "rollback and kill-switch proof for paid flow",
}
REQUIRED_NOT_ALLOWED = {
    "enable_all_providers_at_once",
    "documentation_only_provider_enablement",
    "enable_paid_beta_without_provider_credentials",
    "enable_provider_without_sandbox_or_testnet_evidence",
    "enable_provider_without_production_callback_evidence",
    "enable_paid_access_from_pending_or_pre_checkout_status",
    "enable_telegram_stars_for_general_web_checkout",
    "promise_autoprolongation_or_recurring_billing_in_s1",
    "store_provider_secret_values_in_repo_or_evidence_docs",
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


def _by_provider(items: list[dict[str, Any]], provider: str) -> dict[str, Any]:
    return next((item for item in items if item.get("provider") == provider), {})


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


def _require_false(errors: list[str], item: dict[str, Any], flag: str, label: str) -> None:
    if item.get(flag) is not False:
        errors.append(f"{label}.{flag} must be false")


def _require_true(errors: list[str], item: dict[str, Any], flag: str, label: str) -> None:
    if item.get(flag) is not True:
        errors.append(f"{label}.{flag} must be true")


def validate_contract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if data.get("backlog_id") != "S1-PAY-001":
        errors.append("backlog_id must be S1-PAY-001")
    if data.get("status") != "primary_provider_selected_locally_external_evidence_required":
        errors.append("status must show local selection with external evidence still required")
    if data.get("selected_first_live_path_candidate") != "cryptobot":
        errors.append("CryptoBot must be the selected first live path candidate for S1-PAY-001")
    if data.get("next_backlog_id") != "S1-PAY-002":
        errors.append("next_backlog_id must be S1-PAY-002")

    for flag in ("live_payment_path_proven", "paid_beta_clearance", "production_enablement_allowed"):
        if data.get(flag) is not False:
            errors.append(f"{flag} must be false until provider evidence exists")

    decisions = set(data.get("decision_references", []))
    if not REQUIRED_DECISIONS.issubset(decisions):
        errors.append(f"decision_references missing {sorted(REQUIRED_DECISIONS - decisions)}")

    matrix = data.get("provider_matrix", [])
    providers = {item.get("provider") for item in matrix}
    if not REQUIRED_PROVIDERS.issubset(providers):
        errors.append(f"provider_matrix missing {sorted(REQUIRED_PROVIDERS - providers)}")

    for provider in REQUIRED_PROVIDERS:
        item = _by_provider(matrix, provider)
        if not item:
            continue
        for flag in (
            "real_account_evidence_available",
            "credentials_available",
            "sandbox_or_testnet_evidence_available",
            "production_callback_evidence_available",
            "production_enablement_allowed",
        ):
            _require_false(errors, item, flag, provider)
        if not item.get("external_evidence_required_before_enablement"):
            errors.append(f"{provider} must list external evidence required before enablement")

    cryptobot = _by_provider(matrix, "cryptobot")
    if cryptobot.get("s1_role") != "primary_live_path_candidate":
        errors.append("cryptobot.s1_role must be primary_live_path_candidate")
    for flag in (
        "checkout_runtime_support",
        "webhook_runtime_support",
        "provider_status_mapping_local",
        "signature_or_authenticity_local",
        "idempotency_local",
        "orphan_policy_local",
        "reconciliation_local",
        "payment_to_provisioning_failure_local",
    ):
        _require_true(errors, cryptobot, flag, "cryptobot")
    if not {"active", "paid", "expired", "invoice_paid"}.issubset(set(cryptobot.get("doc_statuses", []))):
        errors.append("cryptobot doc_statuses must include active, paid, expired and invoice_paid")

    telegram_stars = _by_provider(matrix, "telegram_stars")
    if telegram_stars.get("channel_scope") != "telegram_bot_and_mini_app_only":
        errors.append("telegram_stars must be Telegram Bot/Mini App only")
    _require_false(errors, telegram_stars, "general_web_checkout_allowed", "telegram_stars")

    yookassa = _by_provider(matrix, "yookassa")
    digiseller = _by_provider(matrix, "digiseller")
    for provider_name, item in (("yookassa", yookassa), ("digiseller", digiseller)):
        if item.get("s1_role") != "russia_path_later":
            errors.append(f"{provider_name}.s1_role must be russia_path_later")

    for provider_name in ("payram", "nowpayments", "digiseller"):
        item = _by_provider(matrix, provider_name)
        _require_false(errors, item, "checkout_runtime_support", provider_name)
        _require_false(errors, item, "webhook_runtime_support", provider_name)

    minimum_evidence = set(data.get("minimum_evidence_to_enable_primary", []))
    if not REQUIRED_PRIMARY_EVIDENCE_TERMS.issubset(minimum_evidence):
        missing = sorted(REQUIRED_PRIMARY_EVIDENCE_TERMS - minimum_evidence)
        errors.append(f"minimum_evidence_to_enable_primary missing {missing}")

    not_allowed = set(data.get("not_allowed", []))
    if not REQUIRED_NOT_ALLOWED.issubset(not_allowed):
        errors.append(f"not_allowed missing {sorted(REQUIRED_NOT_ALLOWED - not_allowed)}")

    sources = {item.get("provider") for item in data.get("official_sources_checked", [])}
    for provider in {"cryptobot", "telegram_stars", "nowpayments", "yookassa"}:
        if provider not in sources:
            errors.append(f"official_sources_checked must include {provider}")

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

    print(f"{CONTRACT_PATH.relative_to(REPO_ROOT)} is valid for S1-PAY-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
