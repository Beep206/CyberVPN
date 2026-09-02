# ruff: noqa: S101

"""Deployment wiring checks for keyed webhook-log fingerprints."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ANSIBLE_ROOT = REPO_ROOT / "infra" / "ansible"
PRODUCTION_INVENTORY = (
    ANSIBLE_ROOT
    / "inventories"
    / "production"
    / "group_vars"
    / "control_plane_production"
    / "main.yml"
)
STAGING_INVENTORY = (
    ANSIBLE_ROOT
    / "inventories"
    / "staging"
    / "group_vars"
    / "control_plane_staging"
    / "main.yml"
)
PRODUCTION_VAULT = PRODUCTION_INVENTORY.with_name("vault.yml.example")
STAGING_VAULT = STAGING_INVENTORY.with_name("vault.yml.example")
VAULT_SOURCE = ANSIBLE_ROOT / "examples" / "control-plane-vault-source.yml.example"
VAULT_BOOTSTRAP = ANSIBLE_ROOT / "scripts" / "bootstrap_control_plane_vault.py"
ANSIBLE_VALIDATE = (
    ANSIBLE_ROOT / "roles" / "control_plane_stack" / "tasks" / "validate.yml"
)
STAGE1_COMPOSE = REPO_ROOT / "infra" / "deploy" / "stage1" / "docker-compose.stage1.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_vault_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "bootstrap_control_plane_vault", VAULT_BOOTSTRAP
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_production_and_staging_inventories_wire_a_dedicated_secret() -> None:
    expected = (
        "'WEBHOOK_LOG_FINGERPRINT_SECRET': "
        "vault_control_plane_backend_webhook_log_fingerprint_secret"
    )
    for inventory_path in (PRODUCTION_INVENTORY, STAGING_INVENTORY):
        inventory = _read(inventory_path)
        assert inventory.count(expected) == 1

    for vault_path in (PRODUCTION_VAULT, STAGING_VAULT):
        assert "vault_control_plane_backend_webhook_log_fingerprint_secret:" in _read(
            vault_path
        )

    assert "webhook_log_fingerprint_secret:" in _read(VAULT_SOURCE)


def test_vault_bootstrap_requires_the_fingerprint_secret() -> None:
    bootstrap = _load_vault_bootstrap()
    source = {
        vault_key: f"value-for-{source_path}"
        for source_path, vault_key in bootstrap.REQUIRED_SOURCE_MAPPING.items()
        if source_path != "backend.webhook_log_fingerprint_secret"
    }

    with pytest.raises(RuntimeError, match="backend.webhook_log_fingerprint_secret"):
        bootstrap.build_vault_payload(source)

    source["vault_control_plane_backend_webhook_log_fingerprint_secret"] = "w" * 48
    payload = bootstrap.build_vault_payload(source)
    assert (
        payload["vault_control_plane_backend_webhook_log_fingerprint_secret"]
        == "w" * 48
    )


def test_ansible_rejects_missing_weak_or_reused_fingerprint_keys() -> None:
    validate = _read(ANSIBLE_VALIDATE)

    assert "'WEBHOOK_LOG_FINGERPRINT_SECRET'" in validate
    assert (
        "control_plane_stack_backend_env.WEBHOOK_LOG_FINGERPRINT_SECRET | length >= 32"
        in validate
    )
    assert "webhook_log_fingerprint_placeholder_pattern" in validate
    for other in (
        "JWT_SECRET",
        "REMNAWAVE_TOKEN",
        "REMNAWAVE_WEBHOOK_SECRET",
        "REMNAWAVE_STREAM_IP_HMAC_SECRET",
        "CRYPTOBOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "BACKEND_INTERNAL_SECRET",
        "PAYMENT_SETTLEMENT_WORKER_SECRET",
        "TOTP_ENCRYPTION_KEY",
        "OAUTH_TOKEN_ENCRYPTION_KEY",
        "HELIX_ADAPTER_TOKEN",
    ):
        assert (
            "control_plane_stack_backend_env.WEBHOOK_LOG_FINGERPRINT_SECRET "
            f"!= control_plane_stack_backend_env.{other}"
        ) in validate
    assert (
        "control_plane_stack_backend_env.WEBHOOK_LOG_FINGERPRINT_SECRET "
        "!= control_plane_stack_remnawave_env.APP_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.WEBHOOK_LOG_FINGERPRINT_SECRET "
        "!= control_plane_postgres_password"
    ) in validate


def test_stage1_compose_requires_secret_and_examples_do_not_supply_a_fallback() -> None:
    compose = _read(STAGE1_COMPOSE)
    expected = (
        "WEBHOOK_LOG_FINGERPRINT_SECRET: "
        "${WEBHOOK_LOG_FINGERPRINT_SECRET:?set a dedicated 32-plus-character webhook log fingerprint secret}"
    )
    assert compose.count(expected) == 1

    for env_example in (
        REPO_ROOT / "backend" / ".env.example",
        REPO_ROOT / "infra" / ".env.example",
    ):
        env_text = _read(env_example)
        assert "WEBHOOK_LOG_FINGERPRINT_SECRET=" in env_text
        assert "WEBHOOK_LOG_FINGERPRINT_SECRET=${" not in env_text
