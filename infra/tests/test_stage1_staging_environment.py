# ruff: noqa: S101

"""Contract tests for the S1 staging environment manifest."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_staging_environment.py"

spec = importlib.util.spec_from_file_location("validate_s1_staging_environment", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _staging() -> dict:
    return validator.load_staging()


def test_staging_contract_is_valid() -> None:
    assert validator.validate_staging(_staging()) == []


def test_staging_never_shares_production_authority_or_credentials() -> None:
    data = _staging()
    authority = data["authority"]

    assert authority["go_live_clearance"] is False
    assert authority["must_not_use_production_credentials"] is True
    assert authority["must_not_share_state_with_production"] is True

    forbidden = set(data["not_allowed_for_staging"])
    assert "production_payment_credentials" in forbidden
    assert "production_telegram_bot_token" in forbidden
    assert "production_remnawave_api_token" in forbidden
    assert "floating_main_deploy" in forbidden


def test_staging_has_separate_database_valkey_remnawave_bot_and_payment_mode() -> None:
    data = _staging()
    services = {service["id"]: service for service in data["required_services"]}
    separation = set(data["required_environment_separation"])

    for service_id in {
        "staging_postgresql",
        "staging_valkey",
        "staging_remnawave_control_plane",
        "staging_telegram_bot",
    }:
        assert services[service_id]["must_be_separate_from_production"] is True
        assert services[service_id]["external_required"] is True

    assert services["staging_postgresql"]["version_family"] == "17.x"
    assert services["staging_valkey"]["durable_source_of_truth"] is False
    assert services["staging_remnawave_control_plane"]["public"] is False
    assert "payment_provider_credentials_are_sandbox_or_test_mode" in separation


def test_staging_ingress_and_e2e_require_no_challenge_webhooks() -> None:
    data = _staging()
    ingress = {item["id"]: item for item in data["staging_public_ingress"]}
    e2e = set(data["required_stage1_e2e_flows"])

    assert "no_interactive_edge_challenge" in ingress["staging_telegram_webhook"]["required_controls"]
    assert "no_interactive_edge_challenge" in ingress["staging_payment_webhooks"]["required_controls"]
    assert "provider_signature_or_recheck" in ingress["staging_payment_webhooks"]["required_controls"]
    assert "trial_to_remnawave_provisioning" in e2e
    assert "payment_success_remnawave_failure_retry" in e2e
    assert "alert_delivery_for_payment_or_provisioning_failure" in e2e
