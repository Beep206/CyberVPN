from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_snapshot(path: Path) -> None:
    snapshot = {
        "metadata": {
            "snapshot_id": "phase5-synthetic-001",
            "source": "phase5-evidence-fixture",
            "replay_generated_at": "2026-04-18T20:00:00+00:00",
        },
        "service_identities": [
            {
                "id": "svc-1",
                "service_key": "svc-remnawave-001",
                "customer_account_id": "customer-1",
                "auth_realm_id": "realm-1",
                "provider_name": "remnawave",
                "provider_subject_ref": "legacy-subject-001",
                "service_context": {
                    "bridge_origin": "phase5_legacy_migration",
                    "legacy_subscription_url_present": True,
                },
            }
        ],
        "entitlement_grants": [
            {
                "id": "grant-1",
                "service_identity_id": "svc-1",
                "customer_account_id": "customer-1",
                "auth_realm_id": "realm-1",
                "source_type": "order",
                "grant_status": "active",
                "grant_snapshot": {
                    "status": "active",
                    "plan_code": "starter",
                },
            },
            {
                "id": "grant-2",
                "service_identity_id": "svc-1",
                "customer_account_id": "customer-1",
                "auth_realm_id": "realm-1",
                "source_type": "manual",
                "grant_status": "active",
                "grant_snapshot": {
                    "status": "active",
                    "plan_code": "starter",
                },
            },
        ],
        "provisioning_profiles": [
            {
                "id": "profile-1",
                "service_identity_id": "svc-1",
                "profile_key": "desktop_manifest-default",
                "target_channel": "desktop",
                "delivery_method": "manifest",
                "profile_status": "active",
                "provider_name": "remnawave",
                "provisioning_payload": {"format": "json"},
            }
        ],
        "device_credentials": [
            {
                "id": "credential-1",
                "service_identity_id": "svc-1",
                "auth_realm_id": "realm-1",
                "provisioning_profile_id": "profile-1",
                "credential_type": "desktop_client",
                "credential_status": "active",
                "subject_key": "desktop-primary",
                "provider_name": "remnawave",
                "credential_context": {},
            }
        ],
        "access_delivery_channels": [
            {
                "id": "channel-1",
                "service_identity_id": "svc-1",
                "auth_realm_id": "realm-1",
                "provisioning_profile_id": "profile-1",
                "device_credential_id": "credential-1",
                "channel_type": "desktop_manifest",
                "channel_status": "active",
                "channel_subject_ref": "desktop-primary",
                "provider_name": "remnawave",
                "delivery_context": {},
                "delivery_payload": {"profile_format": "json"},
            },
            {
                "id": "channel-2",
                "service_identity_id": "svc-1",
                "auth_realm_id": "realm-1",
                "provisioning_profile_id": "profile-missing",
                "device_credential_id": "credential-missing",
                "channel_type": "telegram_bot",
                "channel_status": "active",
                "channel_subject_ref": "telegram:user-42",
                "provider_name": "remnawave",
                "delivery_context": {},
                "delivery_payload": {},
            },
        ],
        "channel_expectations": [
            {
                "parity_key": "desktop-manifest",
                "customer_account_id": "customer-1",
                "auth_realm_id": "realm-1",
                "provider_name": "remnawave",
                "channel_type": "desktop_manifest",
                "credential_type": "desktop_client",
                "credential_subject_key": "desktop-primary",
                "expected_entitlement_status": "active",
                "requires_service_identity": True,
                "requires_provisioning_profile": True,
                "requires_device_credential": True,
                "requires_access_delivery_channel": True,
                "expected_channel_status": "active",
                "expected_delivery_payload_keys": ["manifest_url"],
            },
            {
                "parity_key": "subscription-link",
                "customer_account_id": "customer-1",
                "auth_realm_id": "realm-1",
                "provider_name": "remnawave",
                "channel_type": "subscription_url",
                "expected_entitlement_status": "active",
                "requires_service_identity": True,
                "requires_provisioning_profile": True,
                "requires_access_delivery_channel": True,
                "expected_delivery_payload_keys": ["subscription_url"],
            },
        ],
    }
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


def test_phase5_service_access_replay_builder_and_summary_are_deterministic(tmp_path: Path) -> None:
    repo_root = _repo_root()
    builder = repo_root / "backend/scripts/build_phase5_service_access_replay_pack.py"
    summary_script = repo_root / "backend/scripts/print_phase5_service_access_replay_summary.py"
    snapshot_path = tmp_path / "snapshot.json"
    output_a = tmp_path / "report-a.json"
    output_b = tmp_path / "report-b.json"

    _write_snapshot(snapshot_path)

    for output_path in (output_a, output_b):
        subprocess.run(  # noqa: S603
            [sys.executable, str(builder), "--input", str(snapshot_path), "--output", str(output_path)],
            check=True,
            cwd=repo_root,
        )

    first = output_a.read_text(encoding="utf-8")
    second = output_b.read_text(encoding="utf-8")
    assert first == second

    report = json.loads(first)
    assert report["metadata"]["report_version"] == "phase5-service-access-replay-v1"
    assert report["metadata"]["generated_at"] == "2026-04-18T20:00:00+00:00"
    assert report["reconciliation"]["status"] == "red"
    assert report["input_summary"]["service_identities"] == 1
    assert report["input_summary"]["channel_expectations"] == 2
    assert report["service_identity_views"][0]["bridge_provenance"]["legacy_subscription_url_present"] is True
    assert report["service_identity_views"][0]["entitlement_counts"]["active"] == 2
    assert report["channel_parity_views"][0]["parity_key"] == "desktop-manifest"
    assert report["channel_parity_views"][0]["mismatch_codes"] == ["parity_delivery_payload_key_missing"]
    assert set(report["channel_parity_views"][1]["mismatch_codes"]) == {
        "parity_missing_provisioning_profile",
        "parity_missing_access_delivery_channel",
    }
    assert report["reconciliation"]["mismatch_counts"]["multiple_active_entitlement_grants_for_scope"] == 1
    assert report["reconciliation"]["mismatch_counts"]["access_delivery_channel_missing_provisioning_profile"] == 1
    assert report["reconciliation"]["mismatch_counts"]["access_delivery_channel_missing_device_credential"] == 1
    assert report["reconciliation"]["mismatch_counts"]["parity_delivery_payload_key_missing"] == 1
    assert report["reconciliation"]["mismatch_counts"]["parity_missing_access_delivery_channel"] == 1
    assert report["reconciliation"]["mismatch_counts"]["parity_missing_provisioning_profile"] == 1

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(summary_script), "--input", str(output_a)],
        check=True,
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout
    assert "status: red" in stdout
    assert "service identities: 1" in stdout
    assert "parity desktop-manifest:" in stdout
    assert "mismatches=parity_delivery_payload_key_missing" in stdout
    assert "multiple_active_entitlement_grants_for_scope: 1" in stdout


def test_phase5_service_access_replay_doc_covers_parity_vocabulary() -> None:
    repo_root = _repo_root()
    content = (repo_root / "docs/testing/partner-platform-phase5-service-access-replay-pack.md").read_text(
        encoding="utf-8"
    )

    for required_term in (
        "replay_generated_at",
        "service_identity_views",
        "channel_parity_views",
        "multiple_active_entitlement_grants_for_scope",
        "access_delivery_channel_missing_provisioning_profile",
        "parity_missing_provisioning_profile",
        "parity_missing_access_delivery_channel",
        "parity_delivery_payload_key_missing",
        "identical input snapshots with fixed `replay_generated_at` produce identical packs",
    ):
        assert required_term in content
