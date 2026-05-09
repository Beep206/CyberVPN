# ruff: noqa: S101

"""Contract tests for the S1 primary payment provider selection."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_primary_payment_provider.py"

spec = importlib.util.spec_from_file_location("validate_s1_primary_payment_provider", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _contract() -> dict:
    return validator.load_contract()


def test_primary_payment_provider_contract_is_valid() -> None:
    assert validator.validate_contract(_contract()) == []


def test_cryptobot_is_selected_as_first_live_candidate_but_not_enabled() -> None:
    data = _contract()
    matrix = {item["provider"]: item for item in data["provider_matrix"]}
    cryptobot = matrix["cryptobot"]

    assert data["selected_first_live_path_candidate"] == "cryptobot"
    assert data["live_payment_path_proven"] is False
    assert data["paid_beta_clearance"] is False
    assert data["production_enablement_allowed"] is False

    assert cryptobot["s1_role"] == "primary_live_path_candidate"
    assert cryptobot["checkout_runtime_support"] is True
    assert cryptobot["webhook_runtime_support"] is True
    assert cryptobot["credentials_available"] is False
    assert cryptobot["production_enablement_allowed"] is False


def test_telegram_stars_is_limited_to_telegram_surfaces() -> None:
    data = _contract()
    matrix = {item["provider"]: item for item in data["provider_matrix"]}
    stars = matrix["telegram_stars"]

    assert stars["s1_role"] == "telegram_only_secondary_path"
    assert stars["channel_scope"] == "telegram_bot_and_mini_app_only"
    assert stars["general_web_checkout_allowed"] is False
    assert stars["production_enablement_allowed"] is False


def test_later_providers_are_not_misrepresented_as_runtime_ready() -> None:
    data = _contract()
    matrix = {item["provider"]: item for item in data["provider_matrix"]}

    for provider in ("payram", "nowpayments", "digiseller"):
        assert matrix[provider]["checkout_runtime_support"] is False
        assert matrix[provider]["webhook_runtime_support"] is False
        assert matrix[provider]["production_enablement_allowed"] is False

    assert matrix["yookassa"]["s1_role"] == "russia_path_later"
    assert matrix["digiseller"]["s1_role"] == "russia_path_later"


def test_primary_enablement_requires_provider_and_operational_evidence() -> None:
    data = _contract()
    required = set(data["minimum_evidence_to_enable_primary"])
    not_allowed = set(data["not_allowed"])

    assert "S1-PAY-002 sandbox/testnet success, failure and expiry samples for CryptoBot" in required
    assert "S1-PAY-003 production credential inventory without values" in required
    assert "payment paid -> subscription -> Remnawave provisioning proof" in required
    assert "paid-but-no-access/orphan alert and manual review proof" in required

    assert "documentation_only_provider_enablement" in not_allowed
    assert "enable_paid_beta_without_provider_credentials" in not_allowed
    assert "enable_all_providers_at_once" in not_allowed
    assert "enable_telegram_stars_for_general_web_checkout" in not_allowed
