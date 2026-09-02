# ruff: noqa: S101

"""Regression tests for backend internal-secret deployment wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PRODUCTION_INVENTORY = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "inventories"
    / "production"
    / "group_vars"
    / "control_plane_production"
    / "main.yml"
)
STAGING_INVENTORY = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "inventories"
    / "staging"
    / "group_vars"
    / "control_plane_staging"
    / "main.yml"
)
PRODUCTION_VAULT_EXAMPLE = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "inventories"
    / "production"
    / "group_vars"
    / "control_plane_production"
    / "vault.yml.example"
)
STAGING_VAULT_EXAMPLE = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "inventories"
    / "staging"
    / "group_vars"
    / "control_plane_staging"
    / "vault.yml.example"
)
VAULT_SOURCE_EXAMPLE = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "examples"
    / "control-plane-vault-source.yml.example"
)
VAULT_BOOTSTRAP = (
    REPO_ROOT / "infra" / "ansible" / "scripts" / "bootstrap_control_plane_vault.py"
)
ANSIBLE_VALIDATE = (
    REPO_ROOT
    / "infra"
    / "ansible"
    / "roles"
    / "control_plane_stack"
    / "tasks"
    / "validate.yml"
)
STAGE1_COMPOSE = REPO_ROOT / "infra" / "deploy" / "stage1" / "docker-compose.stage1.yml"
LOCAL_COMPOSE = REPO_ROOT / "infra" / "docker-compose.yml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_control_plane_inventories_use_dedicated_backend_internal_secret() -> None:
    for path in (PRODUCTION_INVENTORY, STAGING_INVENTORY):
        inventory = _read(path)

        assert (
            "'BACKEND_INTERNAL_SECRET': vault_control_plane_backend_internal_secret"
            in inventory
        )
        assert (
            "'TELEGRAM_BOT_INTERNAL_SECRET': vault_control_plane_backend_telegram_bot_internal_secret"
            in inventory
        )
        assert (
            "'BACKEND_INTERNAL_SECRET': vault_control_plane_backend_telegram_bot_internal_secret"
            not in inventory
        )
        assert (
            "'BACKEND_INTERNAL_SECRET': vault_control_plane_backend_payment_settlement_worker_secret"
            not in inventory
        )
        assert (
            inventory.count(
                "'BACKEND_INTERNAL_SECRET': vault_control_plane_backend_internal_secret"
            )
            == 2
        )
        assert (
            inventory.count(
                "'TELEGRAM_BOT_INTERNAL_SECRET': vault_control_plane_backend_telegram_bot_internal_secret"
            )
            == 2
        )


def test_control_plane_vault_bootstrap_declares_backend_internal_secret() -> None:
    for path in (PRODUCTION_VAULT_EXAMPLE, STAGING_VAULT_EXAMPLE):
        vault_example = _read(path)
        assert "vault_control_plane_backend_internal_secret:" in vault_example
        assert (
            "vault_control_plane_backend_telegram_bot_internal_secret:" in vault_example
        )
        assert (
            "vault_control_plane_backend_remnawave_stream_ip_hmac_secret:"
            in vault_example
        )

    source_example = _read(VAULT_SOURCE_EXAMPLE)
    assert "internal_secret:" in source_example
    assert "telegram_bot_internal_secret:" in source_example
    assert "remnawave_stream_ip_hmac_secret:" in source_example

    bootstrap = _read(VAULT_BOOTSTRAP)
    assert (
        '"backend.internal_secret": "vault_control_plane_backend_internal_secret"'
        in bootstrap
    )
    assert '"backend.telegram_bot_internal_secret"' in bootstrap
    assert "vault_control_plane_backend_telegram_bot_internal_secret" in bootstrap
    assert (
        '"backend.remnawave_stream_ip_hmac_secret": '
        '"vault_control_plane_backend_remnawave_stream_ip_hmac_secret"'
        in bootstrap
    )


def test_control_plane_validation_requires_backend_internal_secret_audience_split() -> (
    None
):
    validate = _read(ANSIBLE_VALIDATE)

    assert "'BACKEND_INTERNAL_SECRET'" in validate
    assert (
        "control_plane_stack_backend_env.BACKEND_INTERNAL_SECRET "
        "!= control_plane_stack_backend_env.TELEGRAM_BOT_INTERNAL_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.BACKEND_INTERNAL_SECRET "
        "!= control_plane_stack_backend_env.PAYMENT_SETTLEMENT_WORKER_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.BACKEND_INTERNAL_SECRET "
        "== control_plane_stack_worker_env.BACKEND_INTERNAL_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.TELEGRAM_BOT_INTERNAL_SECRET "
        "== control_plane_stack_worker_env.TELEGRAM_BOT_INTERNAL_SECRET"
    ) in validate
    assert (
        "control_plane_stack_effective_scheduler_env.BACKEND_INTERNAL_SECRET | length >= 16"
        in validate
    )
    assert (
        "control_plane_stack_effective_scheduler_env.TELEGRAM_BOT_INTERNAL_SECRET | length >= 16"
        in validate
    )
    assert (
        "control_plane_stack_backend_env.BACKEND_INTERNAL_SECRET "
        "== control_plane_stack_effective_scheduler_env.BACKEND_INTERNAL_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.TELEGRAM_BOT_INTERNAL_SECRET "
        "== control_plane_stack_effective_scheduler_env.TELEGRAM_BOT_INTERNAL_SECRET"
    ) in validate
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_STREAM_IP_HMAC_SECRET | length >= 32"
        in validate
    )
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_STREAM_IP_HMAC_SECRET "
        "!= control_plane_stack_backend_env.BACKEND_INTERNAL_SECRET"
    ) in validate


def test_remnawave_stream_ingestion_env_is_versioned_and_bounded() -> None:
    expected = {
        "REMNAWAVE_STREAM_INGESTION_ENABLED": "true",
        "REMNAWAVE_STREAM_CONSUMER_GROUP": "cybervpn-remnawave-v1",
        "REMNAWAVE_STREAM_RECEIPT_RETENTION_DAYS": "14",
        "REMNAWAVE_USER_USAGE_RETENTION_DAYS": "180",
        "REMNAWAVE_SUBSCRIPTION_REQUEST_RETENTION_DAYS": "30",
        "REMNAWAVE_NODE_CONNECTIONS_RETENTION_DAYS": "30",
    }
    for path in (PRODUCTION_INVENTORY, STAGING_INVENTORY):
        inventory = _read(path)
        assert (
            "'REMNAWAVE_STREAM_IP_HMAC_SECRET': "
            "vault_control_plane_backend_remnawave_stream_ip_hmac_secret"
        ) in inventory
        for key, value in expected.items():
            assert f"'{key}': '{value}'" in inventory

    stage1_compose = _read(STAGE1_COMPOSE)
    assert "REMNAWAVE_STREAM_INGESTION_ENABLED: ${REMNAWAVE_STREAM_INGESTION_ENABLED:-true}" in stage1_compose
    assert "REMNAWAVE_STREAM_IP_HMAC_SECRET: ${REMNAWAVE_STREAM_IP_HMAC_SECRET:?" in stage1_compose


def test_stage1_compose_uses_backend_internal_secret_for_backend_worker_and_scheduler() -> (
    None
):
    compose = _read(STAGE1_COMPOSE)

    dedicated_secret = "BACKEND_INTERNAL_SECRET: ${BACKEND_INTERNAL_SECRET:-replace-before-live-backend-internal}"
    telegram_secret = (
        "TELEGRAM_BOT_INTERNAL_SECRET: "
        "${TELEGRAM_BOT_INTERNAL_SECRET:-replace-before-live-telegram-internal}"
    )
    assert compose.count(dedicated_secret) == 3
    assert compose.count(telegram_secret) == 3
    forbidden_backend_secret_lines = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith("BACKEND_INTERNAL_SECRET: ${")
        and (
            "TELEGRAM_BOT_INTERNAL_SECRET" in line
            or "PAYMENT_SETTLEMENT_WORKER_SECRET" in line
        )
    ]
    assert forbidden_backend_secret_lines == []


def test_local_compose_worker_and_scheduler_do_not_reuse_telegram_secret() -> None:
    compose = _read(LOCAL_COMPOSE)
    backend_internal_secret_lines = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith("- BACKEND_INTERNAL_SECRET=")
    ]
    telegram_bot_internal_secret_lines = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith("- TELEGRAM_BOT_INTERNAL_SECRET=")
    ]

    assert backend_internal_secret_lines == [
        "- BACKEND_INTERNAL_SECRET=${BACKEND_INTERNAL_SECRET:-}",
        "- BACKEND_INTERNAL_SECRET=${BACKEND_INTERNAL_SECRET:-}",
    ]
    assert telegram_bot_internal_secret_lines == [
        "- TELEGRAM_BOT_INTERNAL_SECRET=${TELEGRAM_BOT_INTERNAL_SECRET:-}",
        "- TELEGRAM_BOT_INTERNAL_SECRET=${TELEGRAM_BOT_INTERNAL_SECRET:-}",
    ]
