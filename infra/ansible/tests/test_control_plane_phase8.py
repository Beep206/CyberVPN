from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
PROMOTE_SCRIPT_PATH = SCRIPTS_DIR / "promote_control_plane_release.py"
VERIFY_ATTESTATIONS_SCRIPT_PATH = SCRIPTS_DIR / "verify_control_plane_attestations.py"
VAULT_BOOTSTRAP_SCRIPT_PATH = SCRIPTS_DIR / "bootstrap_control_plane_vault.py"
CONTROL_PLANE_ROLE = (
    Path(__file__).resolve().parent.parent / "roles" / "control_plane_stack"
)
ACCEPTED_RISK_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "policies"
    / "control-plane-accepted-risk.schema.json"
)

PROMOTE_SPEC = importlib.util.spec_from_file_location(
    "promote_control_plane_release", PROMOTE_SCRIPT_PATH
)
PROMOTE_MODULE = importlib.util.module_from_spec(PROMOTE_SPEC)
assert PROMOTE_SPEC and PROMOTE_SPEC.loader
PROMOTE_SPEC.loader.exec_module(PROMOTE_MODULE)

VERIFY_ATTESTATIONS_SPEC = importlib.util.spec_from_file_location(
    "verify_control_plane_attestations", VERIFY_ATTESTATIONS_SCRIPT_PATH
)
VERIFY_ATTESTATIONS_MODULE = importlib.util.module_from_spec(VERIFY_ATTESTATIONS_SPEC)
assert VERIFY_ATTESTATIONS_SPEC and VERIFY_ATTESTATIONS_SPEC.loader
VERIFY_ATTESTATIONS_SPEC.loader.exec_module(VERIFY_ATTESTATIONS_MODULE)

VAULT_SPEC = importlib.util.spec_from_file_location(
    "bootstrap_control_plane_vault", VAULT_BOOTSTRAP_SCRIPT_PATH
)
VAULT_MODULE = importlib.util.module_from_spec(VAULT_SPEC)
assert VAULT_SPEC and VAULT_SPEC.loader
VAULT_SPEC.loader.exec_module(VAULT_MODULE)

SOURCE_COMMIT = "a" * 40
SOURCE_RUN_URL = "https://github.com/Beep206/CyberVPN/actions/runs/123"
SIGNER_WORKFLOW = PROMOTE_MODULE.TRUSTED_SIGNER_WORKFLOW


def _images(*, invalid_backend: bool = False) -> dict[str, str]:
    return {
        "remnawave": "ghcr.io/beep206/cybervpn/remnawave-backend@sha256:" + "d" * 64,
        "backend": (
            "ghcr.io/beep206/cybervpn/backend:latest"
            if invalid_backend
            else "ghcr.io/beep206/cybervpn/backend@sha256:" + "a" * 64
        ),
        "worker": "ghcr.io/beep206/cybervpn/task-worker@sha256:" + "b" * 64,
        "helix_adapter": "ghcr.io/beep206/cybervpn/helix-adapter@sha256:" + "c" * 64,
        "node": "ghcr.io/beep206/cybervpn/remnawave-node@sha256:" + "e" * 64,
        "subscription_page": (
            "ghcr.io/beep206/cybervpn/remnawave-subscription-page@sha256:" + "f" * 64
        ),
        "node_ssh_proxy": (
            "ghcr.io/beep206/cybervpn/node-ssh-proxy@sha256:" + "1" * 64
        ),
    }


def _scan_facts(
    image: str,
    *,
    critical: int = 0,
    high: int = 0,
    report_sha256: str = "9" * 64,
) -> dict[str, object]:
    has_findings = critical > 0 or high > 0
    return {
        "schema_version": 2,
        "policy_id": PROMOTE_MODULE.SUPPLY_CHAIN_POLICY_ID,
        "result": "findings" if has_findings else "pass",
        "critical": critical,
        "high": high,
        "scanner": "trivy",
        "report_format": "trivy-json",
        "report_sha256": report_sha256,
        "subject": image,
    }


def _risk_decision(
    images: dict[str, str],
    findings: dict[str, tuple[int, int, str]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "schema_id": PROMOTE_MODULE.ACCEPTED_RISK_SCHEMA_ID,
        "decision_id": "OWNER-REMNAWAVE-342-001",
        "decision": "accepted_non_blocking",
        "policy_id": PROMOTE_MODULE.SUPPLY_CHAIN_POLICY_ID,
        "approved_by": "github:Beep206",
        "approved_at": "2026-09-01T06:30:00Z",
        "rationale": (
            "Owner accepted the exact signed Critical/High findings as "
            "non-blocking for this immutable release digest."
        ),
        "signer_workflow": SIGNER_WORKFLOW,
        "source_commit": SOURCE_COMMIT,
        "components": {
            component: {
                "image": images[component],
                "scanner": "trivy",
                "report_sha256": report_sha256,
                "critical": critical,
                "high": high,
            }
            for component, (critical, high, report_sha256) in findings.items()
        },
    }


def _evidence(
    images: dict[str, str],
    *,
    findings: dict[str, tuple[int, int, str]] | None = None,
    include_decision: bool = True,
) -> dict[str, object]:
    findings = findings or {}

    def claim(predicate_type: str) -> dict[str, object]:
        return {
            "verified": True,
            "verification_method": "gh-attestation-verify",
            "predicate_type": predicate_type,
            "signer_workflow": SIGNER_WORKFLOW,
            "verification_output_sha256": "8" * 64,
            "attestation_count": 1,
        }

    components: dict[str, object] = {}
    for component, image in images.items():
        critical, high, report_sha256 = findings.get(component, (0, 0, "9" * 64))
        has_findings = critical > 0 or high > 0
        scan = {
            **claim(PROMOTE_MODULE.SCAN_PREDICATE),
            **_scan_facts(
                image,
                critical=critical,
                high=high,
                report_sha256=report_sha256,
            ),
            "risk_disposition": (
                "accepted_non_blocking" if has_findings else "clean"
            ),
        }
        if has_findings:
            scan["accepted_risk_decision_id"] = "OWNER-REMNAWAVE-342-001"
        components[component] = {
            "image": image,
            "provenance": claim(PROMOTE_MODULE.PROVENANCE_PREDICATE),
            "sbom": claim(PROMOTE_MODULE.SBOM_PREDICATE),
            "vulnerability_scan": scan,
        }

    return {
        "schema_version": 2,
        "policy_id": PROMOTE_MODULE.SUPPLY_CHAIN_POLICY_ID,
        "source_commit": SOURCE_COMMIT,
        "source_run_url": SOURCE_RUN_URL,
        "source_ref": PROMOTE_MODULE.TRUSTED_SOURCE_REF,
        "signer_workflow": SIGNER_WORKFLOW,
        "accepted_risk": (
            _risk_decision(images, findings)
            if findings and include_decision
            else None
        ),
        "components": components,
    }


class PromoteControlPlaneReleaseTests(unittest.TestCase):
    def _assert_role_accepts_release_supply_chain(
        self,
        supply_chain: dict[str, object],
        images: dict[str, str],
    ) -> None:
        tasks = yaml.safe_load(
            (CONTROL_PLANE_ROLE / "tasks" / "validate.yml").read_text(
                encoding="utf-8"
            )
        )
        task = next(
            item
            for item in tasks
            if item.get("name")
            == "Control plane | Assert unified release supply-chain evidence is complete"
        )
        environment = Environment(undefined=StrictUndefined, autoescape=False)
        environment.tests["match"] = lambda value, pattern: bool(
            re.fullmatch(pattern, str(value))
        )
        environment.filters["bool"] = bool
        for component, image in images.items():
            context = {
                "item": {"key": component, "value": image},
                "control_plane_release_all_images": images,
                "control_plane_release_scan": supply_chain["components"][component][
                    "vulnerability_scan"
                ],
                "control_plane_release_accepted_risk": supply_chain[
                    "accepted_risk"
                ]
                or {},
                "control_plane_stack_release_source_commit": SOURCE_COMMIT,
                "control_plane_stack_release_source_run_url": SOURCE_RUN_URL,
                "control_plane_stack_release_supply_chain": supply_chain,
            }
            for expression in task["ansible.builtin.assert"]["that"]:
                compiled = environment.compile_expression(str(expression))
                self.assertTrue(compiled(**context), str(expression))

    def test_accepted_risk_schema_is_bound_to_runtime_policy(self) -> None:
        schema = json.loads(ACCEPTED_RISK_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$id"], PROMOTE_MODULE.ACCEPTED_RISK_SCHEMA_ID)
        self.assertEqual(
            schema["properties"]["policy_id"]["const"],
            PROMOTE_MODULE.SUPPLY_CHAIN_POLICY_ID,
        )
        self.assertEqual(
            schema["properties"]["signer_workflow"]["const"],
            SIGNER_WORKFLOW,
        )

    def test_build_release_manifest_requires_digest_pins(self) -> None:
        images = _images(invalid_backend=True)
        with self.assertRaises(RuntimeError):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=_evidence(images),
                signer_workflow=SIGNER_WORKFLOW,
            )

    def test_build_release_manifest_rejects_component_image_swap(self) -> None:
        images = _images()
        images["backend"] = images["worker"]
        with self.assertRaisesRegex(RuntimeError, "reviewed repository"):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=_evidence(images),
                signer_workflow=SIGNER_WORKFLOW,
            )

    def test_build_release_manifest_rejects_unverified_scan(self) -> None:
        images = _images()
        evidence = _evidence(images)
        evidence["components"]["node"]["vulnerability_scan"]["verified"] = False

        with self.assertRaisesRegex(RuntimeError, "not verified"):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=evidence,
                signer_workflow=SIGNER_WORKFLOW,
            )

    def test_script_writes_release_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "release.yml"
            evidence_path = Path(temp_dir) / "evidence.json"
            images = _images()
            evidence_path.write_text(json.dumps(_evidence(images)), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(PROMOTE_SCRIPT_PATH),
                    "--environment",
                    "staging",
                    "--output",
                    str(output_path),
                    "--remnawave-image",
                    images["remnawave"],
                    "--remnawave-auth-secret-sha256",
                    "e" * 64,
                    "--backend-image",
                    images["backend"],
                    "--worker-image",
                    images["worker"],
                    "--helix-adapter-image",
                    images["helix_adapter"],
                    "--node-image",
                    images["node"],
                    "--subscription-page-image",
                    images["subscription_page"],
                    "--node-ssh-proxy-image",
                    images["node_ssh_proxy"],
                    "--source-commit",
                    SOURCE_COMMIT,
                    "--source-run-url",
                    SOURCE_RUN_URL,
                    "--evidence-manifest",
                    str(evidence_path),
                    "--created-at",
                    "2026-04-09T10:11:12Z",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["control_plane_release_source_commit"], SOURCE_COMMIT
            )
            self.assertEqual(
                payload["control_plane_release_images"]["remnawave"],
                images["remnawave"],
            )
            self.assertEqual(
                payload["control_plane_remnawave_preupgrade_auth_secret_sha256"],
                "e" * 64,
            )
            self.assertEqual(
                payload["control_plane_release_images"]["backend"],
                images["backend"],
            )
            self.assertEqual(
                payload["control_plane_release_images"]["node"], images["node"]
            )
            self.assertEqual(
                payload["control_plane_release_images"]["subscription_page"],
                images["subscription_page"],
            )
            self.assertEqual(
                payload["control_plane_release_images"]["node_ssh_proxy"],
                images["node_ssh_proxy"],
            )
            self.assertRegex(
                payload["control_plane_release_supply_chain"]["evidence_sha256"],
                r"^[a-f0-9]{64}$",
            )
            self.assertEqual(
                payload["control_plane_release_supply_chain"]["policy_id"],
                "cybervpn-control-plane-supply-chain/v2",
            )
            self.assertTrue(
                payload["control_plane_release_name"].startswith(
                    "control-plane-staging-"
                )
            )

    def test_manifest_preserves_exact_owner_accepted_scan_facts(self) -> None:
        images = _images()
        findings = {"node": (3, 8, "7" * 64)}
        payload = PROMOTE_MODULE.build_release_manifest(
            environment="staging",
            remnawave_image=images["remnawave"],
            remnawave_auth_secret_sha256="e" * 64,
            backend_image=images["backend"],
            worker_image=images["worker"],
            helix_adapter_image=images["helix_adapter"],
            node_image=images["node"],
            subscription_page_image=images["subscription_page"],
            node_ssh_proxy_image=images["node_ssh_proxy"],
            source_commit=SOURCE_COMMIT,
            source_run_url=SOURCE_RUN_URL,
            created_at="2026-04-09T10:11:12Z",
            release_name="",
            evidence=_evidence(images, findings=findings),
            signer_workflow=SIGNER_WORKFLOW,
        )

        supply_chain = payload["control_plane_release_supply_chain"]
        self.assertEqual(
            supply_chain["accepted_risk"]["components"]["node"],
            {
                "image": images["node"],
                "scanner": "trivy",
                "report_sha256": "7" * 64,
                "critical": 3,
                "high": 8,
            },
        )
        self.assertEqual(
            supply_chain["components"]["node"]["vulnerability_scan"][
                "risk_disposition"
            ],
            "accepted_non_blocking",
        )
        self._assert_role_accepts_release_supply_chain(supply_chain, images)

    def test_role_accepts_clean_signed_release_without_stale_decision(self) -> None:
        images = _images()
        payload = PROMOTE_MODULE.build_release_manifest(
            environment="staging",
            remnawave_image=images["remnawave"],
            remnawave_auth_secret_sha256="e" * 64,
            backend_image=images["backend"],
            worker_image=images["worker"],
            helix_adapter_image=images["helix_adapter"],
            node_image=images["node"],
            subscription_page_image=images["subscription_page"],
            node_ssh_proxy_image=images["node_ssh_proxy"],
            source_commit=SOURCE_COMMIT,
            source_run_url=SOURCE_RUN_URL,
            created_at="2026-04-09T10:11:12Z",
            release_name="",
            evidence=_evidence(images),
            signer_workflow=SIGNER_WORKFLOW,
        )
        self._assert_role_accepts_release_supply_chain(
            payload["control_plane_release_supply_chain"],
            images,
        )

    def test_manifest_rejects_findings_without_exact_decision(self) -> None:
        images = _images()
        evidence = _evidence(
            images,
            findings={"node": (3, 8, "7" * 64)},
            include_decision=False,
        )
        with self.assertRaisesRegex(RuntimeError, "Accepted-risk decision"):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=evidence,
                signer_workflow=SIGNER_WORKFLOW,
            )

    def test_build_release_manifest_rejects_untrusted_signer_identity(self) -> None:
        images = _images()
        with self.assertRaisesRegex(RuntimeError, "fixed CyberVPN identity"):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=_evidence(images),
                signer_workflow="github.com/attacker/repo/.github/workflows/build.yml",
            )

    def test_manifest_rejects_changed_report_hash_after_acceptance(self) -> None:
        images = _images()
        evidence = _evidence(images, findings={"node": (3, 8, "7" * 64)})
        evidence["accepted_risk"]["components"]["node"]["report_sha256"] = (
            "6" * 64
        )
        with self.assertRaisesRegex(RuntimeError, "facts do not match"):
            PROMOTE_MODULE.build_release_manifest(
                environment="staging",
                remnawave_image=images["remnawave"],
                remnawave_auth_secret_sha256="e" * 64,
                backend_image=images["backend"],
                worker_image=images["worker"],
                helix_adapter_image=images["helix_adapter"],
                node_image=images["node"],
                subscription_page_image=images["subscription_page"],
                node_ssh_proxy_image=images["node_ssh_proxy"],
                source_commit=SOURCE_COMMIT,
                source_run_url=SOURCE_RUN_URL,
                created_at="2026-04-09T10:11:12Z",
                release_name="",
                evidence=evidence,
                signer_workflow=SIGNER_WORKFLOW,
            )


class BootstrapControlPlaneVaultTests(unittest.TestCase):
    def test_build_vault_payload_maps_structured_source(self) -> None:
        payload = VAULT_MODULE.build_vault_payload(
            {
                "postgres_password": "postgres-secret",
                "registry": {"username": "octocat", "password": "registry-secret"},
                "remnawave": {
                    "app_secret": "app-secret",
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
                    "telegram_bot_token": "backend-telegram-token",
                    "telegram_bot_username": "CyberVPNStageBot",
                    "telegram_bot_internal_secret": "backend-telegram-internal",
                    "internal_secret": "backend-internal",
                    "webhook_log_fingerprint_secret": "webhook-log-hmac-secret-at-least-32-chars",
                    "remnawave_stream_ip_hmac_secret": "stream-ip-hmac-secret-at-least-32-chars",
                    "remnawave_connection_drop_hmac_secret": "connection-drop-hmac-secret-at-least-32-chars",
                    "totp_encryption_key": "totp-key",
                    "oauth_token_encryption_key": "oauth-key",
                },
                "worker": {"remnawave_api_token": "worker-rw"},
                "subscription_page": {
                    "remnawave_api_token": "subscription-page-read-token"
                },
                "helix_adapter": {
                    "remnawave_token": "adapter-rw",
                    "manifest_signing_key": "signing-key",
                },
            }
        )

        self.assertEqual(
            payload["vault_control_plane_postgres_password"], "postgres-secret"
        )
        self.assertEqual(payload["vault_control_plane_registry_username"], "octocat")
        self.assertEqual(
            payload["vault_control_plane_backend_jwt_secret"], "backend-jwt"
        )
        self.assertEqual(
            payload["vault_control_plane_backend_telegram_bot_token"],
            "backend-telegram-token",
        )
        self.assertEqual(
            payload["vault_control_plane_backend_telegram_bot_username"],
            "CyberVPNStageBot",
        )
        self.assertEqual(
            payload["vault_control_plane_backend_telegram_bot_internal_secret"],
            "backend-telegram-internal",
        )
        self.assertEqual(
            payload["vault_control_plane_backend_internal_secret"], "backend-internal"
        )
        self.assertEqual(
            payload["vault_control_plane_backend_webhook_log_fingerprint_secret"],
            "webhook-log-hmac-secret-at-least-32-chars",
        )
        self.assertEqual(
            payload["vault_control_plane_backend_remnawave_stream_ip_hmac_secret"],
            "stream-ip-hmac-secret-at-least-32-chars",
        )
        self.assertEqual(
            payload[
                "vault_control_plane_backend_remnawave_connection_drop_hmac_secret"
            ],
            "connection-drop-hmac-secret-at-least-32-chars",
        )
        self.assertEqual(payload["vault_control_plane_worker_telegram_bot_token"], "")
        self.assertEqual(
            payload["vault_control_plane_subscription_page_remnawave_api_token"],
            "subscription-page-read-token",
        )
        self.assertEqual(payload["vault_control_plane_subscription_page_env_extra"], {})
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
                        "vault_control_plane_remnawave_app_secret": "app-secret",
                        "vault_control_plane_remnawave_metrics_user": "metrics",
                        "vault_control_plane_remnawave_metrics_pass": "metrics-pass",
                        "vault_control_plane_helix_internal_auth_token": "shared-token",
                        "vault_control_plane_helix_remnawave_token": "shared-remnawave",
                        "vault_control_plane_backend_remnawave_token": "backend-rw",
                        "vault_control_plane_backend_jwt_secret": "backend-jwt",
                        "vault_control_plane_backend_cryptobot_token": "",
                        "vault_control_plane_backend_telegram_bot_token": "",
                        "vault_control_plane_backend_telegram_bot_username": "",
                        "vault_control_plane_backend_telegram_bot_internal_secret": "",
                        "vault_control_plane_backend_internal_secret": "backend-internal",
                        "vault_control_plane_backend_webhook_log_fingerprint_secret": "webhook-log-hmac-secret-at-least-32-chars",
                        "vault_control_plane_backend_remnawave_stream_ip_hmac_secret": "stream-ip-hmac-secret-at-least-32-chars",
                        "vault_control_plane_backend_remnawave_connection_drop_hmac_secret": "connection-drop-hmac-secret-at-least-32-chars",
                        "vault_control_plane_backend_totp_encryption_key": "totp-key",
                        "vault_control_plane_backend_oauth_token_encryption_key": "oauth-key",
                        "vault_control_plane_worker_remnawave_api_token": "worker-rw",
                        "vault_control_plane_subscription_page_remnawave_api_token": "subscription-page-read-token",
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
                    sys.executable,
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
            self.assertEqual(
                payload["vault_control_plane_manifest_signing_key"], "signing-key"
            )
            self.assertEqual(
                payload["vault_control_plane_backend_internal_secret"],
                "backend-internal",
            )
            self.assertEqual(
                payload["vault_control_plane_backend_webhook_log_fingerprint_secret"],
                "webhook-log-hmac-secret-at-least-32-chars",
            )
            self.assertEqual(
                payload["vault_control_plane_backend_remnawave_stream_ip_hmac_secret"],
                "stream-ip-hmac-secret-at-least-32-chars",
            )

            self.assertEqual(
                payload[
                    "vault_control_plane_backend_remnawave_connection_drop_hmac_secret"
                ],
                "connection-drop-hmac-secret-at-least-32-chars",
            )
            self.assertEqual(
                payload["vault_control_plane_worker_admin_telegram_ids"], ""
            )
            self.assertEqual(
                payload["vault_control_plane_subscription_page_remnawave_api_token"],
                "subscription-page-read-token",
            )


class VerifyControlPlaneAttestationsTests(unittest.TestCase):
    @staticmethod
    def _verified_output(
        predicate_type: str,
        image: str,
        *,
        critical: int = 0,
        high: int = 0,
    ) -> str:
        if predicate_type == VERIFY_ATTESTATIONS_MODULE.PREDICATES["provenance"]:
            predicate: dict[str, object] = {
                "buildDefinition": {},
                "runDetails": {},
            }
        elif predicate_type == VERIFY_ATTESTATIONS_MODULE.PREDICATES["sbom"]:
            predicate = {
                "spdxVersion": "SPDX-2.3",
                "SPDXID": "SPDXRef-DOCUMENT",
                "packages": [],
            }
        else:
            predicate = _scan_facts(
                image,
                critical=critical,
                high=high,
            )
        subject_name, _, digest = image.rpartition("@sha256:")
        return json.dumps(
            [
                {
                    "verificationResult": {
                        "statement": {
                            "predicateType": predicate_type,
                            "subject": [
                                {
                                    "name": subject_name,
                                    "digest": {"sha256": digest},
                                }
                            ],
                            "predicate": predicate,
                        },
                    }
                }
            ]
        )

    def test_verifier_enforces_fixed_identity_for_every_component_and_claim(
        self,
    ) -> None:
        commands: list[list[str]] = []

        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            predicate = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=self._verified_output(predicate, image),
                stderr="",
            )

        VERIFY_ATTESTATIONS_MODULE.verify_attestations(
            source_commit=SOURCE_COMMIT,
            images=_images(),
            gh_bin="gh",
            runner=runner,
        )

        self.assertEqual(len(commands), 21)
        for command in commands:
            self.assertEqual(
                command[command.index("--repo") + 1],
                "Beep206/CyberVPN",
            )
            self.assertEqual(
                command[command.index("--signer-workflow") + 1],
                "github.com/Beep206/CyberVPN/.github/workflows/control-plane-images.yml",
            )
            self.assertEqual(
                command[command.index("--source-ref") + 1],
                "refs/heads/main",
            )
            self.assertIn("--deny-self-hosted-runners", command)

    def test_verifier_rejects_scan_result_that_disagrees_with_counts(self) -> None:
        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            predicate_type = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            output = json.loads(
                self._verified_output(predicate_type, image, high=1)
            )
            if predicate_type == VERIFY_ATTESTATIONS_MODULE.PREDICATES[
                "vulnerability_scan"
            ]:
                output[0]["verificationResult"]["statement"]["predicate"][
                    "result"
                ] = "pass"
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=json.dumps(output),
                stderr="",
            )

        with self.assertRaisesRegex(RuntimeError, "result/count mismatch"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=_images(),
                gh_bin="gh",
                runner=runner,
            )

    def test_verifier_accepts_exact_digest_bound_owner_decision(self) -> None:
        images = _images()
        findings = {"node": (3, 8, "9" * 64)}

        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            predicate_type = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            critical, high = (3, 8) if image == images["node"] else (0, 0)
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=self._verified_output(
                    predicate_type,
                    image,
                    critical=critical,
                    high=high,
                ),
                stderr="",
            )

        evidence = VERIFY_ATTESTATIONS_MODULE.verify_attestations(
            source_commit=SOURCE_COMMIT,
            source_run_url=SOURCE_RUN_URL,
            images=images,
            gh_bin="gh",
            accepted_risk_decision=_risk_decision(images, findings),
            runner=runner,
        )

        self.assertEqual(
            evidence["components"]["node"]["vulnerability_scan"]["critical"],
            3,
        )
        self.assertEqual(
            evidence["accepted_risk"]["decision_id"],
            "OWNER-REMNAWAVE-342-001",
        )

    def test_verifier_rejects_findings_without_owner_decision(self) -> None:
        images = _images()

        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            predicate_type = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            high = 1 if image == images["node"] else 0
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=self._verified_output(predicate_type, image, high=high),
                stderr="",
            )

        with self.assertRaisesRegex(RuntimeError, "accepted-risk decision is required"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=images,
                gh_bin="gh",
                runner=runner,
            )

    def test_verifier_rejects_malformed_verified_sbom(self) -> None:
        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            predicate_type = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            output = json.loads(self._verified_output(predicate_type, image))
            if predicate_type == VERIFY_ATTESTATIONS_MODULE.PREDICATES["sbom"]:
                output[0]["verificationResult"]["statement"]["predicate"] = {}
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=json.dumps(output),
                stderr="",
            )

        with self.assertRaisesRegex(RuntimeError, "SPDX-2.3"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=_images(),
                gh_bin="gh",
                runner=runner,
            )

    def test_verifier_rejects_attested_subject_mismatch(self) -> None:
        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            predicate_type = command[command.index("--predicate-type") + 1]
            image = command[3].removeprefix("oci://")
            output = json.loads(self._verified_output(predicate_type, image))
            output[0]["verificationResult"]["statement"]["subject"][0][
                "digest"
            ]["sha256"] = "0" * 64
            return subprocess.CompletedProcess(
                command,
                returncode=0,
                stdout=json.dumps(output),
                stderr="",
            )

        with self.assertRaisesRegex(RuntimeError, "subject mismatch"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=_images(),
                gh_bin="gh",
                runner=runner,
            )

    def test_verifier_rejects_failed_cryptographic_verification(self) -> None:
        def runner(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                command,
                returncode=1,
                stdout="[]",
                stderr="signature verification failed",
            )

        with self.assertRaisesRegex(RuntimeError, "cryptographic verification failed"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=_images(),
                gh_bin="gh",
                runner=runner,
            )

    def test_verifier_rejects_missing_release_component(self) -> None:
        images = _images()
        del images["node"]
        with self.assertRaisesRegex(RuntimeError, "exactly every"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=images,
                gh_bin="gh",
            )

    def test_verifier_rejects_component_image_swap_before_gh(self) -> None:
        images = _images()
        images["backend"] = images["worker"]
        with self.assertRaisesRegex(RuntimeError, "reviewed repository"):
            VERIFY_ATTESTATIONS_MODULE.verify_attestations(
                source_commit=SOURCE_COMMIT,
                images=images,
                gh_bin="gh",
            )


class ControlPlaneNodeSshProxyTemplateTests(unittest.TestCase):
    @staticmethod
    def _render_compose(*, enabled: bool) -> dict[str, object]:
        defaults = yaml.safe_load(
            (CONTROL_PLANE_ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")
        )
        defaults.update(
            {
                "control_plane_stack_enable_remnawave": True,
                "control_plane_stack_enable_backend": True,
                "control_plane_stack_enable_postgres": False,
                "control_plane_stack_enable_valkey": False,
                "control_plane_stack_enable_db_backup": False,
                "control_plane_stack_enable_worker": False,
                "control_plane_stack_enable_scheduler": False,
                "control_plane_stack_enable_helix_adapter": False,
                "control_plane_stack_enable_node_ssh_proxy": enabled,
                "control_plane_stack_backend_image": (
                    "ghcr.io/beep206/cybervpn/backend@sha256:" + "a" * 64
                ),
            }
        )
        environment = Environment(undefined=StrictUndefined, autoescape=False)
        environment.filters["to_json"] = json.dumps
        rendered = environment.from_string(
            (CONTROL_PLANE_ROLE / "templates" / "docker-compose.yml.j2").read_text(
                encoding="utf-8"
            )
        ).render(**defaults)
        return yaml.safe_load(rendered)

    def test_proxy_is_absent_when_browser_ssh_is_disabled(self) -> None:
        payload = self._render_compose(enabled=False)
        self.assertNotIn("remnawave-node-ssh-proxy", payload["services"])
        self.assertNotIn("control-ssh-broker", payload["networks"])

    def test_proxy_has_no_host_port_and_uses_exact_internal_peers(self) -> None:
        payload = self._render_compose(enabled=True)
        proxy = payload["services"]["remnawave-node-ssh-proxy"]
        self.assertNotIn("ports", proxy)
        self.assertTrue(proxy["read_only"])
        self.assertEqual(proxy["cap_drop"], ["ALL"])
        self.assertEqual(
            proxy["networks"]["control-ssh-broker"]["ipv4_address"],
            "172.31.254.3",
        )
        self.assertEqual(
            payload["services"]["cybervpn-backend"]["networks"]["control-ssh-broker"][
                "ipv4_address"
            ],
            "172.31.254.4",
        )
        self.assertTrue(payload["networks"]["control-ssh-broker"]["internal"])

    def test_proxy_config_overwrites_identity_and_discards_sensitive_access_logs(
        self,
    ) -> None:
        defaults = yaml.safe_load(
            (CONTROL_PLANE_ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")
        )
        environment = Environment(undefined=StrictUndefined, autoescape=False)
        rendered = environment.from_string(
            (
                CONTROL_PLANE_ROLE / "templates" / "node-ssh-proxy.Caddyfile.j2"
            ).read_text(encoding="utf-8")
        ).render(**defaults)
        self.assertIn("output discard", rendered)
        self.assertIn("header_up X-Remnawave-Real-IP {remote_host}", rendered)
        self.assertIn("/api/cybervpn/node-ssh/tickets/*", rendered)
        self.assertIn("/api/cybervpn/node-ssh/ws", rendered)
        self.assertIn("respond 404", rendered)

    def test_attestation_gate_runs_before_any_remote_state_task(self) -> None:
        main_tasks = (CONTROL_PLANE_ROLE / "tasks" / "main.yml").read_text(
            encoding="utf-8"
        )
        self.assertLess(
            main_tasks.index("verify_attestations.yml"),
            main_tasks.index("state.yml"),
        )

    def test_deployment_verifier_receives_embedded_accepted_risk_via_stdin(
        self,
    ) -> None:
        tasks = (CONTROL_PLANE_ROLE / "tasks" / "verify_attestations.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("--source-run-url", tasks)
        self.assertIn("--accepted-risk-decision", tasks)
        self.assertIn("control_plane_stack_release_supply_chain.accepted_risk", tasks)
        self.assertIn("stdin:", tasks)


if __name__ == "__main__":
    unittest.main()
