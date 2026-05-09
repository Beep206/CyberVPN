# ruff: noqa: S101

"""Contract tests for the S1 CryptoBot sandbox/testnet runtime contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_cryptobot_sandbox.py"

spec = importlib.util.spec_from_file_location("validate_s1_cryptobot_sandbox", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _contract() -> dict:
    return validator.load_contract()


def test_cryptobot_sandbox_contract_is_valid() -> None:
    assert validator.validate_contract(_contract()) == []


def test_cryptobot_network_modes_are_fixed_to_official_endpoints() -> None:
    data = _contract()
    modes = {item["network"]: item for item in data["runtime_network_modes"]}

    assert modes["mainnet"]["base_url"] == "https://pay.crypt.bot/api"
    assert modes["mainnet"]["production_allowed"] is True
    assert modes["testnet"]["base_url"] == "https://testnet-pay.crypt.bot/api"
    assert modes["testnet"]["production_allowed"] is False


def test_backend_and_worker_have_production_testnet_guards() -> None:
    data = _contract()
    components = {item["component"]: item for item in data["runtime_components"]}

    for component_name in ("backend_api", "task_worker"):
        component = components[component_name]
        assert component["config_key"] == "CRYPTOBOT_NETWORK"
        assert component["default_network"] == "mainnet"
        assert component["testnet_runtime_selectable"] is True
        assert component["production_rejects_testnet"] is True
        assert component["arbitrary_base_url_allowed"] is False


def test_real_provider_evidence_is_still_required_before_paid_beta() -> None:
    data = _contract()
    local = data["local_contract_evidence"]
    required = set(data["minimum_external_evidence_before_paid_beta"])
    not_allowed = set(data["not_allowed"])

    assert data["paid_beta_clearance"] is False
    assert data["production_enablement_allowed"] is False
    assert local["real_testnet_credentials_available"] is False
    assert "testnet paid invoice status sample" in required
    assert "testnet expired invoice status sample as cancel-equivalent" in required
    assert "enable_paid_beta_without_real_cryptobot_testnet_credentials" in not_allowed
    assert "use_testnet_in_production" in not_allowed
