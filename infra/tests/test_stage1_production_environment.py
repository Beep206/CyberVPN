# ruff: noqa: S101

"""Contract tests for the S1 production environment manifest."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_s1_production_environment.py"

spec = importlib.util.spec_from_file_location("validate_s1_production_environment", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _production() -> dict:
    return validator.load_production()


def test_production_contract_is_valid() -> None:
    assert validator.validate_production(_production()) == []


def test_production_never_uses_staging_authority_or_floating_main() -> None:
    data = _production()
    authority = data["authority"]

    assert authority["go_live_clearance"] is False
    assert authority["external_production_created"] is False
    assert authority["must_not_use_staging_credentials"] is True
    assert authority["must_not_share_state_with_staging"] is True
    assert authority["may_use_home_lab_as_authority"] is False
    assert authority["deploy_by_immutable_tag_or_commit_sha_only"] is True
    assert authority["floating_main_allowed"] is False

    forbidden = set(data["not_allowed_for_production"])
    assert "staging_payment_credentials" in forbidden
    assert "staging_telegram_bot_token" in forbidden
    assert "staging_remnawave_api_token" in forbidden
    assert "home_lab_as_production_authority" in forbidden
    assert "floating_main_deploy" in forbidden


def test_production_has_managed_private_state_and_backups() -> None:
    data = _production()
    services = {service["id"]: service for service in data["required_services"]}
    separation = set(data["required_environment_separation"])

    assert services["production_postgresql"]["version_family"] == "17.x"
    assert services["production_postgresql"]["public"] is False
    assert services["production_valkey"]["public"] is False
    assert services["production_valkey"]["durable_source_of_truth"] is False
    assert services["production_remnawave_control_plane"]["public"] is False
    assert services["production_backup_storage"]["encrypted"] is True
    assert services["production_backup_storage"]["off_host"] is True
    assert services["production_backup_storage"]["retention_days"] >= 14

    assert "database_users_are_not_shared_with_staging" in separation
    assert "enabled_payment_provider_credentials_are_not_staging_sandbox_credentials" in separation
    assert "container_images_are_referenced_by_immutable_tag_or_digest" in separation


def test_production_public_ingress_matches_s1_domains_and_webhook_controls() -> None:
    data = _production()
    ingress = {item["id"]: item for item in data["production_public_ingress"]}

    assert ingress["production_site_primary"]["host"] == "cyber-vpn.net"
    assert ingress["production_org_reserved"]["host"] == "cyber-vpn.org"
    assert ingress["production_api"]["host"] == "api.cyber-vpn.net"
    assert ingress["production_admin_primary"]["host"] == "admin.cyber-vpn.net"
    assert ingress["production_admin_org_reserved"]["host"] == "admin.cyber-vpn.org"

    assert "no_interactive_edge_challenge" in ingress["production_payment_webhooks"]["required_controls"]
    assert "provider_signature_or_recheck" in ingress["production_payment_webhooks"]["required_controls"]
    assert "no_interactive_edge_challenge" in ingress["production_telegram_webhook"]["required_controls"]
    assert "no_public_admin_login" in ingress["production_admin_org_reserved"]["required_controls"]


def test_production_deployability_has_preflight_and_kill_switches() -> None:
    data = _production()
    preflight = set(data["deployability_preflight"])
    kill_switches = set(data["kill_switches_required"])

    assert "fresh_dirty_worktree_scope_map_approved" in preflight
    assert "immutable_release_tag_or_commit_sha_selected" in preflight
    assert "production_config_rendered_without_staging_secrets" in preflight
    assert "rollback_command_and_release_pointer_recorded" in preflight
    assert "observability_targets_and_alert_routes_recorded" in preflight

    for kill_switch in {"registration", "payments", "trial", "provisioning", "telegram_stars"}:
        assert kill_switch in kill_switches
