from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
PROMOTE_SCRIPT_PATH = SCRIPTS_DIR / "promote_control_plane_release.py"
VAULT_BOOTSTRAP_SCRIPT_PATH = SCRIPTS_DIR / "bootstrap_control_plane_vault.py"

PROMOTE_SPEC = importlib.util.spec_from_file_location("promote_control_plane_release", PROMOTE_SCRIPT_PATH)
PROMOTE_MODULE = importlib.util.module_from_spec(PROMOTE_SPEC)
assert PROMOTE_SPEC and PROMOTE_SPEC.loader
PROMOTE_SPEC.loader.exec_module(PROMOTE_MODULE)

VAULT_SPEC = importlib.util.spec_from_file_location("bootstrap_control_plane_vault", VAULT_BOOTSTRAP_SCRIPT_PATH)
VAULT_MODULE = importlib.util.module_from_spec(VAULT_SPEC)
assert VAULT_SPEC and VAULT_SPEC.loader
VAULT_SPEC.loader.exec_module(VAULT_MODULE)


class PromoteControlPlaneReleaseTests(unittest.TestCase):
    def test_build_release_manifest_requires_digest_pins(self) -> None:
        with self.assertRaises(RuntimeError):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                backend_image="ghcr.io/example/backend:latest",
                worker_image="ghcr.io/example/worker@sha256:" + "a" * 64,
                helix_adapter_image="ghcr.io/example/helix-adapter@sha256:" + "b" * 64,
                source_commit="abcdef123456",
                source_run_url="https://example.invalid/run/1",
                created_at="2026-04-09T10:11:12Z",
                release_name="",
            )

    def test_script_writes_release_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "release.yml"
            subprocess.run(
                [
                    "python",
                    str(PROMOTE_SCRIPT_PATH),
                    "--environment",
                    "staging",
                    "--output",
                    str(output_path),
                    "--backend-image",
                    "ghcr.io/example/backend@sha256:" + "a" * 64,
                    "--worker-image",
                    "ghcr.io/example/task-worker@sha256:" + "b" * 64,
                    "--helix-adapter-image",
                    "ghcr.io/example/helix-adapter@sha256:" + "c" * 64,
                    "--source-commit",
                    "abcdef1234567890",
                    "--source-run-url",
                    "https://example.invalid/actions/runs/123",
                    "--created-at",
                    "2026-04-09T10:11:12Z",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["control_plane_release_source_commit"], "abcdef1234567890")
            self.assertEqual(
                payload["control_plane_release_images"]["backend"],
                "ghcr.io/example/backend@sha256:" + "a" * 64,
            )
            self.assertTrue(payload["control_plane_release_name"].startswith("control-plane-staging-"))


class BootstrapControlPlaneVaultTests(unittest.TestCase):
    def test_build_vault_payload_maps_structured_source(self) -> None:
        payload = VAULT_MODULE.build_vault_payload(
            {
                "postgres_password": "postgres-secret",
                "registry": {"username": "octocat", "password": "registry-secret"},
                "remnawave": {
                    "jwt_auth_secret": "jwt-auth",
                    "jwt_api_tokens_secret": "jwt-api",
                    "metrics_user": "metrics",
                    "metrics_pass": "metrics-pass",
                },
                "shared": {
                    "helix_internal_auth_token": "shared-token",
                    "helix_remnawave_token": "shared-remnawave",
                },
                "backend": {
                    "remnawave_token": "backend-rw",
                    "jwt_secret": "backend-jwt",
                    "totp_encryption_key": "totp-key",
                    "oauth_token_encryption_key": "oauth-key",
                },
                "worker": {"remnawave_api_token": "worker-rw"},
                "helix_adapter": {
                    "remnawave_token": "adapter-rw",
                    "manifest_signing_key": "signing-key",
                },
            }
        )

        self.assertEqual(payload["vault_control_plane_postgres_password"], "postgres-secret")
        self.assertEqual(payload["vault_control_plane_registry_username"], "octocat")
        self.assertEqual(payload["vault_control_plane_backend_jwt_secret"], "backend-jwt")
        self.assertEqual(payload["vault_control_plane_worker_telegram_bot_token"], "")
        self.assertEqual(payload["vault_control_plane_backend_env_extra"], {})

    def test_script_accepts_prefixed_json_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "vault-source.json"
            output_path = temp_path / "vault.yml"
            source_path.write_text(
                json.dumps(
                    {
                        "vault_control_plane_postgres_password": "postgres-secret",
                        "vault_control_plane_registry_username": "",
                        "vault_control_plane_registry_password": "",
                        "vault_control_plane_remnawave_jwt_auth_secret": "jwt-auth",
                        "vault_control_plane_remnawave_jwt_api_tokens_secret": "jwt-api",
                        "vault_control_plane_remnawave_metrics_user": "metrics",
                        "vault_control_plane_remnawave_metrics_pass": "metrics-pass",
                        "vault_control_plane_helix_internal_auth_token": "shared-token",
                        "vault_control_plane_helix_remnawave_token": "shared-remnawave",
                        "vault_control_plane_backend_remnawave_token": "backend-rw",
                        "vault_control_plane_backend_jwt_secret": "backend-jwt",
                        "vault_control_plane_backend_cryptobot_token": "",
                        "vault_control_plane_backend_totp_encryption_key": "totp-key",
                        "vault_control_plane_backend_oauth_token_encryption_key": "oauth-key",
                        "vault_control_plane_worker_remnawave_api_token": "worker-rw",
                        "vault_control_plane_worker_telegram_bot_token": "",
                        "vault_control_plane_worker_cryptobot_token": "",
                        "vault_control_plane_worker_admin_telegram_ids": "",
                        "vault_control_plane_helix_adapter_remnawave_token": "adapter-rw",
                        "vault_control_plane_manifest_signing_key": "signing-key",
                    }
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    "python",
                    str(VAULT_BOOTSTRAP_SCRIPT_PATH),
                    "--environment",
                    "staging",
                    "--source",
                    str(source_path),
                    "--output",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["vault_control_plane_manifest_signing_key"], "signing-key")
            self.assertEqual(payload["vault_control_plane_worker_admin_telegram_ids"], "")


if __name__ == "__main__":
    unittest.main()
