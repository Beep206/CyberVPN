# ruff: noqa: S101

"""Contract tests for the S1 CryptoBot production credential inventory."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_cryptobot_production_credentials.py"

spec = importlib.util.spec_from_file_location("validate_s1_cryptobot_production_credentials", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _contract() -> dict:
    return validator.load_contract()


def test_cryptobot_production_credentials_contract_is_valid() -> None:
    assert validator.validate_contract(_contract()) == []


def test_inventory_records_no_secret_values() -> None:
    data = _contract()
    inventory = {item["secret_name"]: item for item in data["credential_inventory_without_values"]}

    assert inventory["CRYPTOBOT_TOKEN"]["value_recorded_in_repo"] is False
    assert inventory["CRYPTOBOT_TOKEN"]["placeholder_allowed_in_production"] is False
    assert inventory["CRYPTOBOT_NETWORK"]["required_value"] == "mainnet"
    assert inventory["CRYPTOBOT_NETWORK"]["testnet_allowed_in_production"] is False


def test_runtime_guards_cover_backend_worker_and_bot() -> None:
    data = _contract()
    components = {item["component"]: item for item in data["runtime_guards"]}

    for component_name in ("backend_api", "task_worker"):
        component = components[component_name]
        assert component["production_requires_cryptobot_token"] is True
        assert component["production_rejects_placeholder_token"] is True
        assert component["production_rejects_testnet_network"] is True

    assert components["telegram_bot"]["production_requires_cryptobot_token_when_gateway_enabled"] is True
    assert components["telegram_bot"]["production_rejects_placeholder_token"] is True


def test_real_secret_store_evidence_is_still_required_before_paid_beta() -> None:
    data = _contract()
    local = data["local_contract_evidence"]
    required = set(data["minimum_external_evidence_before_paid_beta"])
    not_allowed = set(data["not_allowed"])

    assert data["paid_beta_clearance"] is False
    assert data["production_enablement_allowed"] is False
    assert local["real_provider_account_evidence_available"] is False
    assert local["real_secret_store_screenshot_or_transcript_available"] is False
    assert "production CRYPTOBOT_TOKEN stored in approved secret store without value disclosure" in required
    assert "enable_paid_beta_without_secret_store_evidence" in not_allowed
