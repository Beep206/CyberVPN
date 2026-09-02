# ruff: noqa: S101

"""Deployment contract for the stable connection-drop receipt HMAC key."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INFRA_ROOT = REPO_ROOT / "infra"
ANSIBLE_ROOT = INFRA_ROOT / "ansible"
STAGE1_COMPOSE = INFRA_ROOT / "deploy" / "stage1" / "docker-compose.stage1.yml"
STAGE1_DEPLOY = REPO_ROOT / "scripts" / "deploy" / "stage1-gitlab-deploy.sh"
ANSIBLE_VALIDATE = (
    ANSIBLE_ROOT / "roles" / "control_plane_stack" / "tasks" / "validate.yml"
)
VAULT_SOURCE = ANSIBLE_ROOT / "examples" / "control-plane-vault-source.yml.example"
VAULT_BOOTSTRAP = ANSIBLE_ROOT / "scripts" / "bootstrap_control_plane_vault.py"
ANSIBLE_README = ANSIBLE_ROOT / "README.md"
INFRA_README = INFRA_ROOT / "README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def test_stage1_wires_receipt_key_only_to_backend() -> None:
    env_example = _read(INFRA_ROOT / ".env.example")
    assert env_example.count("REMNAWAVE_CONNECTION_DROP_HMAC_SECRET=") == 1
    assert "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET=${" not in env_example

    compose = _read(STAGE1_COMPOSE)
    backend = _between(compose, "  cybervpn-backend:\n", "  cybervpn-worker:\n")
    worker = _between(compose, "  cybervpn-worker:\n", "  cybervpn-scheduler:\n")
    scheduler = _between(compose, "  cybervpn-scheduler:\n", "  cybervpn-remnawave:\n")
    expected = (
        "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET: "
        "${REMNAWAVE_CONNECTION_DROP_HMAC_SECRET:?set a dedicated stable "
        "32-plus-character Remnawave connection-drop HMAC secret}"
    )
    assert expected in backend
    assert "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET" not in worker
    assert "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET" not in scheduler
    injected_lines = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith("REMNAWAVE_CONNECTION_DROP_HMAC_SECRET:")
    ]
    assert injected_lines == [expected]


def test_ansible_inventories_and_vaults_wire_receipt_key_only_to_backend() -> None:
    expected = (
        "'REMNAWAVE_CONNECTION_DROP_HMAC_SECRET': "
        "vault_control_plane_backend_remnawave_connection_drop_hmac_secret"
    )
    for environment in ("staging", "production"):
        group_vars = (
            ANSIBLE_ROOT
            / "inventories"
            / environment
            / "group_vars"
            / f"control_plane_{environment}"
        )
        inventory = _read(group_vars / "main.yml")
        backend = _between(
            inventory,
            "control_plane_stack_backend_env:",
            "control_plane_stack_worker_env:",
        )
        worker = _between(
            inventory,
            "control_plane_stack_worker_env:",
            "control_plane_stack_scheduler_env:",
        )
        assert expected in backend
        assert "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET" not in worker
        assert inventory.count(expected) == 1

        vault = _read(group_vars / "vault.yml.example")
        assert (
            vault.count(
                "vault_control_plane_backend_remnawave_connection_drop_hmac_secret:"
            )
            == 1
        )


def test_vault_source_and_bootstrap_require_dedicated_receipt_key() -> None:
    source = _read(VAULT_SOURCE)
    bootstrap = _read(VAULT_BOOTSTRAP)

    assert source.count("remnawave_connection_drop_hmac_secret:") == 1
    assert (
        '"backend.remnawave_connection_drop_hmac_secret": '
        '"vault_control_plane_backend_remnawave_connection_drop_hmac_secret"'
        in bootstrap
    )


def test_ansible_rejects_missing_weak_or_reused_receipt_key() -> None:
    validate = _read(ANSIBLE_VALIDATE)
    required = _between(
        validate,
        "Control plane | Assert backend config is complete",
        "Control plane | Assert webhook log fingerprint key is dedicated",
    )
    receipt_guard = _between(
        validate,
        "Control plane | Assert connection-drop receipt HMAC key is dedicated",
        "Control plane | Assert Remnawave Node SSH policy is fail-closed",
    )

    assert "'REMNAWAVE_CONNECTION_DROP_HMAC_SECRET'" in required
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET "
        "| length >= 32" in receipt_guard
    )
    assert "remnawave_connection_drop_secret_placeholder_pattern" in receipt_guard
    for other in (
        "JWT_SECRET",
        "REMNAWAVE_TOKEN",
        "REMNAWAVE_WEBHOOK_SECRET",
        "WEBHOOK_LOG_FINGERPRINT_SECRET",
        "REMNAWAVE_STREAM_IP_HMAC_SECRET",
        "REMNAWAVE_NODE_SSH_BROKER_SECRET",
        "CRYPTOBOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_BOT_INTERNAL_SECRET",
        "BACKEND_INTERNAL_SECRET",
        "PAYMENT_SETTLEMENT_WORKER_SECRET",
        "TOTP_ENCRYPTION_KEY",
        "OAUTH_TOKEN_ENCRYPTION_KEY",
        "HELIX_ADAPTER_TOKEN",
    ):
        assert (
            "control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET "
            f"!= control_plane_stack_backend_env.{other}"
        ) in receipt_guard
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET "
        "!= control_plane_stack_remnawave_env.APP_SECRET" in receipt_guard
    )
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET "
        "!= control_plane_postgres_password" in receipt_guard
    )
    assert "outcome_unknown" in receipt_guard
    assert "no_log: true" in receipt_guard

    assert (
        "control_plane_stack_backend_env.WEBHOOK_LOG_FINGERPRINT_SECRET "
        "!= control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET"
        in validate
    )
    assert (
        "control_plane_stack_backend_env.REMNAWAVE_STREAM_IP_HMAC_SECRET "
        "!= control_plane_stack_backend_env.REMNAWAVE_CONNECTION_DROP_HMAC_SECRET"
        in validate
    )


def test_stage1_preflight_requires_existing_stable_receipt_key() -> None:
    deploy = _read(STAGE1_DEPLOY)
    guard = _between(
        deploy,
        "require_remnawave_connection_drop_hmac_secret() {",
        "\n}",
    )

    assert "${#receipt_secret}" in guard
    assert "-lt 32" in guard
    assert "must not use a placeholder value" in guard
    assert '"$receipt_secret" = "$backend_secret"' in guard
    assert '"$receipt_secret" = "$stream_secret"' in guard
    assert '"$receipt_secret" = "$fingerprint_secret"' in guard
    assert (
        "ensure_remote_env_secret .env REMNAWAVE_CONNECTION_DROP_HMAC_SECRET"
        not in deploy
    )
    assert deploy.count("require_remnawave_connection_drop_hmac_secret") == 2


def test_operator_docs_define_stability_and_worker_isolation() -> None:
    docs = _read(ANSIBLE_README) + _read(INFRA_README)
    assert "backend.remnawave_connection_drop_hmac_secret" in docs
    assert "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET" in docs
    assert "outcome_unknown" in docs
    assert "do not rotate" in docs.lower()
    assert "worker" in docs.lower()
