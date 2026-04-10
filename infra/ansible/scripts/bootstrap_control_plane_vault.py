from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

import yaml


REQUIRED_SOURCE_MAPPING = {
    "postgres_password": "vault_control_plane_postgres_password",
    "remnawave.jwt_auth_secret": "vault_control_plane_remnawave_jwt_auth_secret",
    "remnawave.jwt_api_tokens_secret": "vault_control_plane_remnawave_jwt_api_tokens_secret",
    "remnawave.metrics_pass": "vault_control_plane_remnawave_metrics_pass",
    "shared.helix_internal_auth_token": "vault_control_plane_helix_internal_auth_token",
    "shared.helix_remnawave_token": "vault_control_plane_helix_remnawave_token",
    "backend.remnawave_token": "vault_control_plane_backend_remnawave_token",
    "backend.jwt_secret": "vault_control_plane_backend_jwt_secret",
    "backend.totp_encryption_key": "vault_control_plane_backend_totp_encryption_key",
    "backend.oauth_token_encryption_key": "vault_control_plane_backend_oauth_token_encryption_key",
    "worker.remnawave_api_token": "vault_control_plane_worker_remnawave_api_token",
    "helix_adapter.remnawave_token": "vault_control_plane_helix_adapter_remnawave_token",
    "helix_adapter.manifest_signing_key": "vault_control_plane_manifest_signing_key",
}

OPTIONAL_SOURCE_MAPPING = {
    "registry.username": ("vault_control_plane_registry_username", ""),
    "registry.password": ("vault_control_plane_registry_password", ""),
    "remnawave.metrics_user": ("vault_control_plane_remnawave_metrics_user", "metrics"),
    "backend.cryptobot_token": ("vault_control_plane_backend_cryptobot_token", ""),
    "worker.telegram_bot_token": ("vault_control_plane_worker_telegram_bot_token", ""),
    "worker.cryptobot_token": ("vault_control_plane_worker_cryptobot_token", ""),
    "worker.admin_telegram_ids": ("vault_control_plane_worker_admin_telegram_ids", ""),
    "extras.remnawave": ("vault_control_plane_remnawave_env_extra", {}),
    "extras.backend": ("vault_control_plane_backend_env_extra", {}),
    "extras.worker": ("vault_control_plane_worker_env_extra", {}),
    "extras.helix_adapter": ("vault_control_plane_helix_adapter_env_extra", {}),
}


def get_nested_value(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def parse_env_file(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if not key or not _:
            raise RuntimeError(f"Invalid env line in {path}: {raw_line}")
        payload[key.strip()] = value.strip()
    return payload


def load_source_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    elif suffix == ".env":
        payload = parse_env_file(path)
    else:
        raise RuntimeError(f"Unsupported source file format: {path}")

    if not isinstance(payload, dict):
        raise RuntimeError(f"Secrets source must be a mapping object: {path}")
    return payload


def build_vault_payload(source_payload: dict[str, Any]) -> dict[str, Any]:
    vault_payload: dict[str, Any] = {
        key: value
        for key, value in source_payload.items()
        if key.startswith("vault_control_plane_")
    }

    missing_paths: list[str] = []
    for source_key, vault_key in REQUIRED_SOURCE_MAPPING.items():
        if vault_key in vault_payload:
            continue
        try:
            vault_payload[vault_key] = get_nested_value(source_payload, source_key)
        except KeyError:
            missing_paths.append(source_key)

    if missing_paths:
        missing = ", ".join(sorted(missing_paths))
        raise RuntimeError(f"Missing required secret paths: {missing}")

    for source_key, (vault_key, default_value) in OPTIONAL_SOURCE_MAPPING.items():
        if vault_key in vault_payload:
            continue
        try:
            vault_payload[vault_key] = get_nested_value(source_payload, source_key)
        except KeyError:
            vault_payload[vault_key] = default_value

    return vault_payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=True, allow_unicode=False),
        encoding="utf-8",
    )


def encrypt_file(path: Path, vault_password_file: str, vault_id: str) -> None:
    command = ["ansible-vault", "encrypt", str(path)]
    if vault_password_file:
        command.extend(["--vault-password-file", vault_password_file])
    if vault_id:
        command.extend(["--vault-id", vault_id])
    subprocess.run(command, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a control-plane Ansible vault file from structured source data.",
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=("staging", "production"),
        help="Inventory environment to update.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to a YAML, JSON, or .env source file.",
    )
    parser.add_argument(
        "--inventory-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "inventories",
        help="Path to the ansible inventories root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional explicit output path. Defaults to the group_vars vault.yml for the environment.",
    )
    parser.add_argument(
        "--encrypt",
        action="store_true",
        help="Encrypt the rendered file with ansible-vault after writing it.",
    )
    parser.add_argument(
        "--vault-password-file",
        default="",
        help="Optional ansible-vault password file path when --encrypt is used.",
    )
    parser.add_argument(
        "--vault-id",
        default="",
        help="Optional ansible-vault --vault-id value when --encrypt is used.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = args.output or (
        args.inventory_root
        / args.environment
        / "group_vars"
        / f"control_plane_{args.environment}"
        / "vault.yml"
    )

    payload = build_vault_payload(load_source_file(args.source))
    write_yaml(output_path, payload)
    if args.encrypt:
        encrypt_file(
            path=output_path,
            vault_password_file=args.vault_password_file,
            vault_id=args.vault_id,
        )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
