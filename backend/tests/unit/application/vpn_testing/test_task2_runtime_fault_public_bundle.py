from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.application.vpn_testing.task2_probe_plan import TASK2_ANTIFILTER_CATEGORIES
from src.application.vpn_testing.task2_runtime_fault_evidence import (
    TASK2_RUNTIME_FAULT_EVIDENCE_AUDIENCE,
    TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2,
    TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2,
    Task2EvidenceHeaderV2,
    Task2RuntimeFaultEvidenceRejected,
    Task2RuntimeFaultPayloadV2,
    backend_result_digest,
    backend_result_set_digest,
    canonical_json_bytes,
    envelope_signing_bytes,
)
from src.application.vpn_testing.task2_runtime_fault_public_bundle import (
    TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES,
    TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_SCHEMA,
    verify_task2_runtime_fault_public_bundle,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
CLI_SCRIPT = REPO_ROOT / "scripts/remnawave/verify-task2-runtime-fault-evidence-bundle.py"
NOW = datetime(2026, 7, 13, 12, 6, tzinfo=UTC)
MANIFEST_SHA256 = "c" * 64
FEED_VERSION = "0b4748d29a45"
BASELINE_ATTEMPT_ID = "1" * 32
FAULT_ATTEMPT_ID = "2" * 32
POST_RESTORE_ATTEMPT_ID = "3" * 32
KEY_ID = "task2-runtime-operator-20260713-a"
TRUSTED_OPERATOR_FINGERPRINT_FILE = "trusted-operator-public-key.sha256"
BACKEND_IDENTITY = {
    "label": "cybervpn-backend",
    "git_sha": "9" * 40,
    "image_ref": "cybervpn/backend:task2-runtime",
    "image_id": "sha256:" + "2" * 64,
    "instance": "prod-app-1",
}
AGENT_IDENTITY = {
    "label": "cybervpn-vpn-test-agent",
    "git_sha": "9" * 40,
    "image_ref": "cybervpn/vpn-test-agent:task2-runtime",
    "image_id": "sha256:" + "3" * 64,
    "instance": "spb-agent-1",
}
COMMUNITIES = {
    "rkn": ["65444:100"],
    "meta": ["65444:700"],
    "twitter_x": ["65444:710"],
    "netflix": ["65444:720"],
    "cloudfront": ["65444:730"],
    "microsoft": ["65444:740"],
    "amazon": ["65444:750"],
    "openai": ["65444:760"],
    "youtube": ["65444:770"],
    "google": ["65444:780"],
    "telegram": ["65444:790"],
    "discord": ["65444:800"],
    "custom_networks": ["65444:65444"],
}


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _result(route_key: str, *, traffic_class: str, transport: str, network: str, category: str | None) -> dict:
    expected = "DE_EXCEPTIONS_BRIDGE" if traffic_class == "matched_exception" else "DIRECT"
    return {
        "check_key": f"premium_spb_de_exceptions.selected_outbound.{route_key}",
        "check_name": route_key,
        "category": "runtime",
        "status": "pass",
        "severity": "error",
        "target": route_key,
        "safe_summary": "Synthetic selected-outbound probe passed",
        "details": {
            "route_key": route_key,
            "traffic_class": traffic_class,
            "category": category,
            "transport": transport,
            "probe_network": network,
            "membership": "member" if traffic_class == "matched_exception" else "non_member",
            "expected_outbound": expected,
            "selected_outbound": expected,
            "verdict": "pass",
            "digest": hashlib.sha256(route_key.encode()).hexdigest(),
            "manifest_sha256": MANIFEST_SHA256,
            "route_feed_version": FEED_VERSION,
            "credentials_redacted": True,
        },
        "duration_ms": 1,
    }


def _run_results() -> list[dict]:
    results = [
        _result(
            f"category-{category}",
            traffic_class="matched_exception",
            transport="raw",
            network="tcp",
            category=category,
        )
        for category in TASK2_ANTIFILTER_CATEGORIES
    ]
    for transport in ("raw", "xhttp"):
        for network in ("tcp", "udp"):
            results.append(
                _result(
                    f"matched-{transport}-{network}",
                    traffic_class="matched_exception",
                    transport=transport,
                    network=network,
                    category="custom_networks",
                )
            )
            results.append(
                _result(
                    f"default-{transport}-{network}",
                    traffic_class="unmatched_default",
                    transport=transport,
                    network=network,
                    category=None,
                )
            )
    results.append(
        {
            "check_key": "premium_spb_de_exceptions.selected_outbound.matrix",
            "check_name": "Task2 selected-outbound matrix",
            "category": "runtime",
            "status": "degraded",
            "severity": "warning",
            "target": "spb-xray",
            "safe_summary": "Selected-outbound matrix matched; bridge-down evidence is still required",
            "details": {
                "expected_count": 21,
                "actual_count": 21,
                "all_13_categories_declared": True,
                "raw_xhttp_tcp_udp_declared": True,
                "agent_id": "spb-agent-1",
                "bridge_down_evidence_claimed": False,
            },
            "duration_ms": 0,
        }
    )
    results.extend(
        [
            {
                "check_key": key,
                "check_name": key,
                "category": "runtime",
                "status": "degraded",
                "severity": "warning",
                "target": "task2",
                "safe_summary": "Signed fault evidence is still required",
                "details": {"runtime_evidence_status": "not_claimed", "credentials_redacted": True},
                "duration_ms": 0,
            }
            for key in (
                "premium_spb_de_exceptions.bridge_down_fail_closed",
                "premium_spb_de_exceptions.runtime_evidence",
                "premium_spb_de_exceptions.runtime.completeness",
            )
        ]
    )
    results.append(
        {
            "check_key": "premium_spb_de_exceptions.dns_ipv6_leak_policy",
            "check_name": "DNS and IPv6 policy",
            "category": "runtime",
            "status": "pass",
            "severity": "error",
            "target": "task2",
            "safe_summary": "Static policy is present",
            "details": {"credentials_redacted": True},
            "duration_ms": 0,
        }
    )
    return results


def _pre_fault_rows(results: list[dict]) -> list[dict]:
    rows = []
    for result in results:
        if not result["check_key"].startswith("premium_spb_de_exceptions.selected_outbound."):
            continue
        if result["check_key"].endswith(".matrix"):
            continue
        details = result["details"]
        rows.append(
            {
                **{
                    key: details[key]
                    for key in (
                        "route_key",
                        "traffic_class",
                        "category",
                        "transport",
                        "probe_network",
                        "membership",
                        "expected_outbound",
                        "selected_outbound",
                        "verdict",
                        "manifest_sha256",
                        "route_feed_version",
                    )
                },
                "backend_result_digest": backend_result_digest(result),
            }
        )
    return rows


def _capture(run_id: str, attempt_id: str, results: list[dict], started_at: datetime, finished_at: datetime) -> dict:
    return {
        "id": run_id,
        "suite_key": "premium_spb_de_exceptions_v1",
        "mode": "runtime",
        "status": "degraded",
        "runtime_mode": "proxy-only",
        "route_registry_version": "premium_spb_de_exceptions_v1",
        "started_at": _iso(started_at),
        "finished_at": _iso(finished_at),
        "summary": {
            "execution_attempt_id": attempt_id,
            "route_registry_version": "premium_spb_de_exceptions_v1",
            "task2_runtime_identity": {
                "bound": True,
                "credentials_redacted": True,
            },
        },
        "results": deepcopy(results),
    }


def _payload(
    *,
    baseline_capture: dict,
    fault_capture: dict,
    post_restore_capture: dict,
) -> dict[str, Any]:
    pre_fault = _pre_fault_rows(baseline_capture["results"])
    fault_rows = []
    restore_rows = []
    for row in pre_fault:
        matched = row["traffic_class"] == "matched_exception"
        fault_rows.append(
            {
                "route_key": row["route_key"],
                "traffic_class": row["traffic_class"],
                "selected_outbound": row["selected_outbound"],
                "probe_succeeded": not matched,
                "backend_result_digest": row["backend_result_digest"],
            }
        )
        restore_rows.append(
            {
                "route_key": row["route_key"],
                "traffic_class": row["traffic_class"],
                "selected_outbound": row["selected_outbound"],
                "probe_succeeded": True,
                "egress_region": "DE" if matched else "SPB",
                "backend_result_digest": row["backend_result_digest"],
            }
        )

    raw = {
        "schema": TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2,
        "evidence_id": "task2-evidence-20260713-a",
        "run_id": baseline_capture["id"],
        "execution_attempt_id": BASELINE_ATTEMPT_ID,
        "suite_key": "premium_spb_de_exceptions_v1",
        "mode": "runtime",
        "runtime_mode": "proxy-only",
        "route_registry_version": "premium_spb_de_exceptions_v1",
        "run_started_at": baseline_capture["started_at"],
        "run_finished_at": baseline_capture["finished_at"],
        "backend": BACKEND_IDENTITY,
        "agent": AGENT_IDENTITY,
        "operator": {
            "label": "cybervpn-task2-operator",
            "git_sha": "9" * 40,
            "image_ref": "cybervpn/operator:task2-runtime",
            "image_id": "sha256:" + "4" * 64,
            "instance": "codex-prod-operator",
        },
        "feed": {
            "active_lkg_match": True,
            "version": FEED_VERSION,
            "generated_at": _iso(NOW - timedelta(hours=1)),
            "active_pointer_sha256": "a" * 64,
            "last_known_good_pointer_sha256": "a" * 64,
            "active_manifest_sha256": MANIFEST_SHA256,
            "last_known_good_manifest_sha256": MANIFEST_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "union_sha256": "d" * 64,
            "ipv4_count": 21415,
            "ipv6_count": 0,
            "categories": [
                {
                    "category": category,
                    "communities": COMMUNITIES[category],
                    "ipv4_count": 1,
                    "ipv6_count": 0,
                    "sha256": hashlib.sha256(category.encode()).hexdigest(),
                }
                for category in TASK2_ANTIFILTER_CATEGORIES
            ],
        },
        "backend_result_set_digest": backend_result_set_digest(baseline_capture["results"]),
        "pre_fault_rows": pre_fault,
        "fault": {
            "watchdog_armed_at": _iso(NOW - timedelta(minutes=4, seconds=1)),
            "watchdog_deadline_at": _iso(NOW - timedelta(seconds=1)),
            "started_at": _iso(NOW - timedelta(minutes=4)),
            "finished_at": _iso(NOW - timedelta(minutes=3)),
            "duration_seconds": 60,
            "firewall_rules": [
                {
                    "rule_id": f"task2-de-bridge-{protocol}",
                    "rule_sha256": hashlib.sha256(
                        canonical_json_bytes(
                            {
                                "action": "drop",
                                "destination_ipv6": "2a0b:4140:ba84::2",
                                "destination_port": 9444,
                                "protocol": protocol,
                                "source_ipv6": "2a01:e5c0:1368::3",
                            }
                        )
                    ).hexdigest(),
                    "source_ipv6": "2a01:e5c0:1368::3",
                    "destination_ipv6": "2a0b:4140:ba84::2",
                    "destination_port": 9444,
                    "protocol": protocol,
                    "action": "drop",
                }
                for protocol in ("tcp", "udp")
            ],
            "tcp_drop_counter": 1963,
            "udp_drop_counter": 7,
            "watchdog_armed": True,
            "cleanup_removed": True,
            "cleanup_verified_at": _iso(NOW - timedelta(minutes=2, seconds=59)),
        },
        "fault_rows": fault_rows,
        "post_restore_rows": restore_rows,
        "policies": {
            "dns_policy_verified": True,
            "ipv6_policy_verified": True,
            "dns_evidence_sha256": "e" * 64,
            "ipv6_evidence_sha256": "f" * 64,
        },
        "baseline_capture_sha256": _sha256_bytes(_json_bytes(baseline_capture)),
        "auxiliary_runs": {
            "fault": {
                "run_id": fault_capture["id"],
                "execution_attempt_id": FAULT_ATTEMPT_ID,
                "canonical_sanitized_capture_sha256": _sha256_bytes(_json_bytes(fault_capture)),
            },
            "post_restore": {
                "run_id": post_restore_capture["id"],
                "execution_attempt_id": POST_RESTORE_ATTEMPT_ID,
                "canonical_sanitized_capture_sha256": _sha256_bytes(_json_bytes(post_restore_capture)),
            },
        },
    }
    return Task2RuntimeFaultPayloadV2.model_validate_json(_json_bytes(raw)).model_dump(
        mode="json",
        by_alias=True,
    )


def _signed_envelope(payload: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    payload_sha256 = _sha256_bytes(_json_bytes(payload))
    raw_header = {
        "schema": TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2,
        "audience": TASK2_RUNTIME_FAULT_EVIDENCE_AUDIENCE,
        "algorithm": "Ed25519",
        "key_id": KEY_ID,
        "nonce": "6" * 32,
        "issued_at": _iso(NOW),
        "not_before": _iso(NOW - timedelta(seconds=1)),
        "expires_at": _iso(NOW + timedelta(minutes=10)),
        "payload_sha256": payload_sha256,
    }
    header = Task2EvidenceHeaderV2.model_validate_json(_json_bytes(raw_header)).model_dump(
        mode="json",
        by_alias=True,
    )
    signature = private_key.sign(envelope_signing_bytes(header, payload))
    return {
        "header": header,
        "payload": payload,
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def _public_key_material(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _operator_public_key_sha256(private_key: Ed25519PrivateKey) -> str:
    raw_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _sha256_bytes(raw_key)


def _write_bundle(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir()
    artifacts = {name: {"sha256": _sha256_bytes(raw)} for name, raw in files.items()}
    manifest = {
        "schema": TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_SCHEMA,
        "artifacts": artifacts,
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    (root / "manifest.json").write_bytes(_json_bytes(manifest))


def _bundle(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    private_key = Ed25519PrivateKey.generate()
    results = _run_results()
    baseline_capture = _capture(
        str(uuid4()),
        BASELINE_ATTEMPT_ID,
        results,
        NOW - timedelta(minutes=6),
        NOW - timedelta(minutes=5),
    )
    fault_capture = _capture(
        str(uuid4()),
        FAULT_ATTEMPT_ID,
        results,
        NOW - timedelta(minutes=3, seconds=50),
        NOW - timedelta(minutes=3, seconds=10),
    )
    post_restore_capture = _capture(
        str(uuid4()),
        POST_RESTORE_ATTEMPT_ID,
        results,
        NOW - timedelta(minutes=2, seconds=50),
        NOW - timedelta(minutes=2, seconds=30),
    )
    payload = _payload(
        baseline_capture=baseline_capture,
        fault_capture=fault_capture,
        post_restore_capture=post_restore_capture,
    )
    files = {
        "operator-public-key.pem": _public_key_material(private_key),
        "signed-envelope.json": _json_bytes(_signed_envelope(payload, private_key)),
        "baseline-run.json": _json_bytes(baseline_capture),
        "fault-window-run.json": _json_bytes(fault_capture),
        "post-restore-run.json": _json_bytes(post_restore_capture),
    }
    root = tmp_path / "bundle"
    _write_bundle(root, files)
    (tmp_path / TRUSTED_OPERATOR_FINGERPRINT_FILE).write_text(
        _operator_public_key_sha256(private_key),
        encoding="ascii",
    )
    return root, {
        "baseline_capture": baseline_capture,
        "fault_capture": fault_capture,
        "post_restore_capture": post_restore_capture,
        "payload": payload,
        "private_key": private_key,
    }


def _verify_bundle(
    root: Path,
    *,
    expected_manifest_sha256: str | None = None,
) -> Any:
    trusted_fingerprint = (root.parent / TRUSTED_OPERATOR_FINGERPRINT_FILE).read_text(encoding="ascii")
    return verify_task2_runtime_fault_public_bundle(
        root,
        expected_operator_public_key_sha256=trusted_fingerprint,
        expected_manifest_sha256=expected_manifest_sha256,
    )


def _load_cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_task2_runtime_fault_evidence_bundle", CLI_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rewrite_json(path: Path, value: Any) -> None:
    path.write_bytes(_json_bytes(value))


def _rewrite_manifest(root: Path, mutate: Any) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    _rewrite_json(manifest_path, manifest)


def test_valid_public_bundle_verifies_offline_and_exposes_only_safe_summary(tmp_path: Path) -> None:
    root, context = _bundle(tmp_path)

    verified = _verify_bundle(
        root,
        expected_manifest_sha256=_sha256_bytes((root / "manifest.json").read_bytes()),
    )

    summary = verified.safe_summary()
    assert summary["status"] == "verified"
    assert summary["credentials_redacted"] is True
    assert summary["baseline"]["run_id"] == context["baseline_capture"]["id"]
    assert summary["fault"]["run_id"] == context["fault_capture"]["id"]
    assert summary["post_restore"]["run_id"] == context["post_restore_capture"]["id"]
    assert summary["selected_outbound_count"] == 21
    serialized = json.dumps(summary, sort_keys=True)
    assert "signed-envelope" not in serialized
    assert "PRIVATE KEY" not in serialized
    assert "customer@example.test" not in serialized
    assert "vless" not in serialized.lower()
    assert set(verified.artifact_sha256s) == set(TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES)


def test_invalid_out_of_band_trust_anchor_is_rejected(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="expected_operator_public_key_sha256_invalid"):
        verify_task2_runtime_fault_public_bundle(
            root,
            expected_operator_public_key_sha256="not-a-sha256",
        )


def test_out_of_band_manifest_anchor_mismatch_is_rejected(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="bundle_manifest_trust_anchor_mismatch"):
        _verify_bundle(root, expected_manifest_sha256="0" * 64)


def test_coherently_resigned_bundle_with_replacement_key_is_rejected(tmp_path: Path) -> None:
    root, context = _bundle(tmp_path)
    replacement_key = Ed25519PrivateKey.generate()
    files = {
        "operator-public-key.pem": _public_key_material(replacement_key),
        "signed-envelope.json": _json_bytes(_signed_envelope(context["payload"], replacement_key)),
        "baseline-run.json": (root / "baseline-run.json").read_bytes(),
        "fault-window-run.json": (root / "fault-window-run.json").read_bytes(),
        "post-restore-run.json": (root / "post-restore-run.json").read_bytes(),
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    _rewrite_manifest(
        root,
        lambda manifest: manifest.__setitem__(
            "artifacts",
            {name: {"sha256": _sha256_bytes(raw)} for name, raw in files.items()},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="operator_public_key_trust_anchor_mismatch"):
        _verify_bundle(root)


def test_cli_prints_only_safe_json_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, _context = _bundle(tmp_path)
    cli = _load_cli()

    exit_code = cli.main(
        [
            str(root),
            "--expected-operator-public-key-sha256",
            (tmp_path / TRUSTED_OPERATOR_FINGERPRINT_FILE).read_text(encoding="ascii"),
            "--expected-manifest-sha256",
            _sha256_bytes((root / "manifest.json").read_bytes()),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    summary = json.loads(captured.out)
    assert summary["status"] == "verified"
    assert summary["credentials_redacted"] is True
    assert str(root) not in captured.out
    assert "signed-envelope" not in captured.out
    assert "PRIVATE KEY" not in captured.out
    assert "customer@example.test" not in captured.out
    assert "vless" not in captured.out.lower()


def test_cli_requires_an_out_of_band_operator_trust_anchor(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    cli = _load_cli()

    with pytest.raises(SystemExit, match="2"):
        cli.main([str(root)])


def test_cli_help_does_not_require_production_settings() -> None:
    env = os.environ.copy()
    for key in (
        "REMNAWAVE_TOKEN",
        "JWT_SECRET",
        "CRYPTOBOT_TOKEN",
        "CYBERVPN_DEVICE_COOKIE_PEPPER",
        "TOTP_ENCRYPTION_KEY",
        "OAUTH_TOKEN_ENCRYPTION_KEY",
    ):
        env.pop(key, None)

    result = subprocess.run(  # noqa: S603 - fixed interpreter/script regression for standalone CLI import path.
        [sys.executable, str(CLI_SCRIPT), "--help"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0
    assert "bundle_dir" in result.stdout
    assert "--expected-operator-public-key-sha256" in result.stdout
    assert "validation error" not in result.stderr.lower()


def test_tampered_manifest_artifact_hash_is_rejected(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    _rewrite_manifest(
        root,
        lambda manifest: manifest["artifacts"].__setitem__("baseline-run.json", {"sha256": "0" * 64}),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="bundle_manifest_artifact_digest_mismatch"):
        _verify_bundle(root)


def test_manifest_extra_or_missing_artifact_is_rejected(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    (root / "extra.json").write_text("{}", encoding="utf-8")

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="bundle_file_set_mismatch"):
        _verify_bundle(root)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda manifest: manifest.__setitem__("schema", "cybervpn.task2.runtime-fault-evidence.public-bundle.v0"),
        lambda manifest: manifest.__setitem__("schemaVersion", 2),
        lambda manifest: manifest.pop("schema"),
    ],
)
def test_manifest_schema_must_be_strict_public_bundle_v1(tmp_path: Path, mutate: Any) -> None:
    root, _context = _bundle(tmp_path)
    _rewrite_manifest(root, mutate)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="bundle_manifest_schema_invalid"):
        _verify_bundle(root)


def test_capture_run_id_tamper_is_rejected_against_signed_payload(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    baseline = json.loads((root / "baseline-run.json").read_text(encoding="utf-8"))
    baseline["id"] = str(uuid4())
    _rewrite_json(root / "baseline-run.json", baseline)
    _rewrite_manifest(
        root,
        lambda manifest: manifest["artifacts"].__setitem__(
            "baseline-run.json",
            {"sha256": _sha256_bytes(_json_bytes(baseline))},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="baseline_capture_identity_mismatch"):
        _verify_bundle(root)


def test_capture_hash_tamper_is_rejected_against_signed_payload(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    fault = json.loads((root / "fault-window-run.json").read_text(encoding="utf-8"))
    fault["summary"]["operator_note"] = "safe-public-note"
    _rewrite_json(root / "fault-window-run.json", fault)
    _rewrite_manifest(
        root,
        lambda manifest: manifest["artifacts"].__setitem__(
            "fault-window-run.json",
            {"sha256": _sha256_bytes(_json_bytes(fault))},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="fault_capture_digest_mismatch"):
        _verify_bundle(root)


def test_baseline_result_tamper_is_rejected_by_backend_digest(tmp_path: Path) -> None:
    root, context = _bundle(tmp_path)
    baseline = deepcopy(context["baseline_capture"])
    selected = next(
        result
        for result in baseline["results"]
        if result["check_key"].startswith("premium_spb_de_exceptions.selected_outbound.")
        and not result["check_key"].endswith(".matrix")
    )
    selected["details"]["selected_outbound"] = "DIRECT"
    payload = deepcopy(context["payload"])
    payload["baseline_capture_sha256"] = _sha256_bytes(_json_bytes(baseline))
    envelope = json.loads((root / "signed-envelope.json").read_text(encoding="utf-8"))
    private_key = context["private_key"]
    envelope = _signed_envelope(payload, private_key)
    files = {
        "operator-public-key.pem": _public_key_material(private_key),
        "signed-envelope.json": _json_bytes(envelope),
        "baseline-run.json": _json_bytes(baseline),
        "fault-window-run.json": (root / "fault-window-run.json").read_bytes(),
        "post-restore-run.json": (root / "post-restore-run.json").read_bytes(),
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    _rewrite_manifest(
        root,
        lambda manifest: manifest.__setitem__(
            "artifacts",
            {name: {"sha256": _sha256_bytes(raw)} for name, raw in files.items()},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="baseline_backend_result_set_digest_mismatch"):
        _verify_bundle(root)


def test_fault_capture_fingerprint_tamper_is_rejected(tmp_path: Path) -> None:
    root, context = _bundle(tmp_path)
    fault = deepcopy(context["fault_capture"])
    selected = next(
        result
        for result in fault["results"]
        if result["check_key"].startswith("premium_spb_de_exceptions.selected_outbound.")
        and not result["check_key"].endswith(".matrix")
    )
    selected["details"]["transport"] = "xhttp" if selected["details"]["transport"] == "raw" else "raw"
    payload = deepcopy(context["payload"])
    payload["auxiliary_runs"]["fault"]["canonical_sanitized_capture_sha256"] = _sha256_bytes(_json_bytes(fault))
    private_key = context["private_key"]
    envelope = _signed_envelope(payload, private_key)
    files = {
        "operator-public-key.pem": _public_key_material(private_key),
        "signed-envelope.json": _json_bytes(envelope),
        "baseline-run.json": (root / "baseline-run.json").read_bytes(),
        "fault-window-run.json": _json_bytes(fault),
        "post-restore-run.json": (root / "post-restore-run.json").read_bytes(),
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    _rewrite_manifest(
        root,
        lambda manifest: manifest.__setitem__(
            "artifacts",
            {name: {"sha256": _sha256_bytes(raw)} for name, raw in files.items()},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="fault_selected_fingerprint_mismatch"):
        _verify_bundle(root)


def test_failed_selected_outbound_row_is_rejected_even_when_hashes_are_rebound(tmp_path: Path) -> None:
    root, context = _bundle(tmp_path)
    fault = deepcopy(context["fault_capture"])
    selected = next(
        result
        for result in fault["results"]
        if result["check_key"].startswith("premium_spb_de_exceptions.selected_outbound.")
        and not result["check_key"].endswith(".matrix")
    )
    selected["status"] = "fail"
    payload = deepcopy(context["payload"])
    payload["auxiliary_runs"]["fault"]["canonical_sanitized_capture_sha256"] = _sha256_bytes(_json_bytes(fault))
    private_key = context["private_key"]
    files = {
        "operator-public-key.pem": _public_key_material(private_key),
        "signed-envelope.json": _json_bytes(_signed_envelope(payload, private_key)),
        "baseline-run.json": (root / "baseline-run.json").read_bytes(),
        "fault-window-run.json": _json_bytes(fault),
        "post-restore-run.json": (root / "post-restore-run.json").read_bytes(),
    }
    for name, raw in files.items():
        (root / name).write_bytes(raw)
    _rewrite_manifest(
        root,
        lambda manifest: manifest.__setitem__(
            "artifacts",
            {name: {"sha256": _sha256_bytes(raw)} for name, raw in files.items()},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="capture_selected_outbound_not_pass"):
        _verify_bundle(root)


@pytest.mark.parametrize(
    ("name", "mutate", "reason"),
    [
        (
            "fault-window-run.json",
            lambda capture: capture.__setitem__("started_at", _iso(NOW - timedelta(minutes=4, seconds=1))),
            "fault_capture_outside_signed_fault_window",
        ),
        (
            "post-restore-run.json",
            lambda capture: capture.__setitem__("started_at", _iso(NOW - timedelta(minutes=2, seconds=59))),
            "post_restore_capture_before_cleanup",
        ),
        (
            "fault-window-run.json",
            lambda capture: capture.__setitem__("status", "pass"),
            "capture_run_status_not_safe_degraded",
        ),
    ],
)
def test_capture_temporal_and_safe_degraded_contract_is_enforced(
    tmp_path: Path,
    name: str,
    mutate: Any,
    reason: str,
) -> None:
    root, context = _bundle(tmp_path)
    capture_key = {
        "fault-window-run.json": "fault_capture",
        "post-restore-run.json": "post_restore_capture",
    }[name]
    capture = deepcopy(context[capture_key])
    mutate(capture)
    payload = deepcopy(context["payload"])
    if name == "fault-window-run.json":
        payload["auxiliary_runs"]["fault"]["canonical_sanitized_capture_sha256"] = _sha256_bytes(_json_bytes(capture))
    else:
        payload["auxiliary_runs"]["post_restore"]["canonical_sanitized_capture_sha256"] = _sha256_bytes(
            _json_bytes(capture)
        )
    private_key = context["private_key"]
    files = {
        "operator-public-key.pem": _public_key_material(private_key),
        "signed-envelope.json": _json_bytes(_signed_envelope(payload, private_key)),
        "baseline-run.json": (root / "baseline-run.json").read_bytes(),
        "fault-window-run.json": _json_bytes(capture)
        if name == "fault-window-run.json"
        else (root / "fault-window-run.json").read_bytes(),
        "post-restore-run.json": _json_bytes(capture)
        if name == "post-restore-run.json"
        else (root / "post-restore-run.json").read_bytes(),
    }
    for file_name, raw in files.items():
        (root / file_name).write_bytes(raw)
    _rewrite_manifest(
        root,
        lambda manifest: manifest.__setitem__(
            "artifacts",
            {file_name: {"sha256": _sha256_bytes(raw)} for file_name, raw in files.items()},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match=reason):
        _verify_bundle(root)


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("baseline-run.json", {"customer": {"email": "customer@example.test"}}),
        ("fault-window-run.json", {"subscription_url": "https://example.test/api/sub/abc"}),
        ("post-restore-run.json", {"link": "vless://public-material"}),
        ("signed-envelope.json", {"operator_note": "BEGIN PRIVATE KEY"}),
    ],
)
def test_public_bundle_rejects_sensitive_material_in_any_artifact(tmp_path: Path, name: str, payload: dict) -> None:
    root, _context = _bundle(tmp_path)
    original = json.loads((root / name).read_text(encoding="utf-8"))
    original["injected"] = payload
    _rewrite_json(root / name, original)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="sensitive_value_not_allowed"):
        _verify_bundle(root)


def test_signature_text_containing_jwt_letters_is_not_a_sensitive_value_false_positive(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    envelope_path = root / "signed-envelope.json"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    envelope["signature"] = "jwt" + envelope["signature"][3:]
    _rewrite_json(envelope_path, envelope)
    _rewrite_manifest(
        root,
        lambda manifest: manifest["artifacts"].__setitem__(
            "signed-envelope.json",
            {"sha256": _sha256_bytes(envelope_path.read_bytes())},
        ),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="invalid_signature"):
        _verify_bundle(root)


def test_public_bundle_rejects_structured_jwt_value(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    capture_path = root / "baseline-run.json"
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    capture["injected"] = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzeW50aGV0aWMifQ.synthetic-signature"  # gitleaks:allow
    _rewrite_json(capture_path, capture)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="sensitive_value_not_allowed"):
        _verify_bundle(root)


def test_duplicate_key_and_float_json_are_rejected(tmp_path: Path) -> None:
    root, _context = _bundle(tmp_path)
    (root / "baseline-run.json").write_bytes(b'{"id":"x","id":"y","value":1.25}')

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="baseline-run.json_invalid_json"):
        _verify_bundle(root)
