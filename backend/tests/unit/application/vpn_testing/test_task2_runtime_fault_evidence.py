from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from src.application.vpn_testing.task2_probe_plan import TASK2_ANTIFILTER_CATEGORIES
from src.application.vpn_testing.task2_runtime_fault_evidence import (
    TASK2_RUNTIME_FAULT_EVIDENCE_AUDIENCE,
    TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA,
    TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2,
    TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA,
    TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2,
    Task2EvidenceHeader,
    Task2EvidenceHeaderV2,
    Task2RuntimeFaultEvidenceRejected,
    Task2RuntimeFaultPayload,
    Task2RuntimeFaultPayloadV2,
    backend_result_digest,
    backend_result_set_digest,
    canonical_json_bytes,
    envelope_signing_bytes,
    promote_task2_runtime_fault_results,
    task2_runtime_identity_digest,
    verify_published_task2_runtime_fault_evidence,
    verify_task2_runtime_fault_evidence,
)

NOW = datetime(2026, 7, 13, 12, 6, tzinfo=UTC)
MANIFEST_SHA256 = "c" * 64
FEED_VERSION = "0b4748d29a45"
ATTEMPT_ID = "1" * 32
KEY_ID = "task2-runtime-operator-20260713-a"
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
    results.extend(
        [
            {
                "check_key": key,
                "check_name": key,
                "category": "runtime",
                "status": "degraded",
                "severity": "error",
                "target": "task2",
                "safe_summary": "Signed fault evidence is still required",
                "details": {"runtime_evidence_status": "not_claimed"},
                "duration_ms": 0,
            }
            for key in (
                "premium_spb_de_exceptions.selected_outbound.matrix",
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
            "details": {},
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


def _payload(run: SimpleNamespace) -> dict[str, Any]:
    pre_fault = _pre_fault_rows(run.results)
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
        "schema": TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA,
        "evidence_id": "task2-evidence-20260713-a",
        "run_id": str(run.id),
        "execution_attempt_id": ATTEMPT_ID,
        "suite_key": "premium_spb_de_exceptions_v1",
        "mode": "runtime",
        "runtime_mode": "proxy-only",
        "route_registry_version": "premium_spb_de_exceptions_v1",
        "run_started_at": _iso(run.started_at),
        "run_finished_at": _iso(run.finished_at),
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
        "backend_result_set_digest": backend_result_set_digest(run.results),
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
    }
    return Task2RuntimeFaultPayload.model_validate_json(canonical_json_bytes(raw)).model_dump(
        mode="json",
        by_alias=True,
    )


def _payload_v2(run: SimpleNamespace) -> dict[str, Any]:
    raw = {
        **_payload(run),
        "schema": TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2,
        "baseline_capture_sha256": "0" * 64,
        "auxiliary_runs": {
            "fault": {
                "run_id": str(uuid4()),
                "execution_attempt_id": "2" * 32,
                "canonical_sanitized_capture_sha256": "a" * 64,
            },
            "post_restore": {
                "run_id": str(uuid4()),
                "execution_attempt_id": "3" * 32,
                "canonical_sanitized_capture_sha256": "b" * 64,
            },
        },
    }
    return Task2RuntimeFaultPayloadV2.model_validate_json(canonical_json_bytes(raw)).model_dump(
        mode="json",
        by_alias=True,
    )


def _signed_envelope(run: SimpleNamespace, private_key: Ed25519PrivateKey) -> dict[str, Any]:
    payload = _payload(run)
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    raw_header = {
        "schema": TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA,
        "audience": TASK2_RUNTIME_FAULT_EVIDENCE_AUDIENCE,
        "algorithm": "Ed25519",
        "key_id": KEY_ID,
        "nonce": "5" * 32,
        "issued_at": _iso(NOW),
        "not_before": _iso(NOW - timedelta(seconds=1)),
        "expires_at": _iso(NOW + timedelta(minutes=10)),
        "payload_sha256": payload_sha256,
    }
    header = Task2EvidenceHeader.model_validate_json(canonical_json_bytes(raw_header)).model_dump(
        mode="json",
        by_alias=True,
    )
    signature = private_key.sign(envelope_signing_bytes(header, payload))
    return {
        "header": header,
        "payload": payload,
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def _signed_envelope_v2(run: SimpleNamespace, private_key: Ed25519PrivateKey) -> dict[str, Any]:
    payload = _payload_v2(run)
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
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
    header = Task2EvidenceHeaderV2.model_validate_json(canonical_json_bytes(raw_header)).model_dump(
        mode="json",
        by_alias=True,
    )
    signature = private_key.sign(envelope_signing_bytes(header, payload))
    return {
        "header": header,
        "payload": payload,
        "signature": base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii"),
    }


def _resign(envelope: dict[str, Any], private_key: Ed25519PrivateKey) -> None:
    payload = Task2RuntimeFaultPayload.model_validate_json(canonical_json_bytes(envelope["payload"])).model_dump(
        mode="json",
        by_alias=True,
    )
    header = dict(envelope["header"])
    header["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    normalized_header = Task2EvidenceHeader.model_validate_json(canonical_json_bytes(header)).model_dump(
        mode="json",
        by_alias=True,
    )
    signature = private_key.sign(envelope_signing_bytes(normalized_header, payload))
    envelope["header"] = normalized_header
    envelope["payload"] = payload
    envelope["signature"] = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


def _public_key_material(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _operator_public_key_sha256(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def evidence_context(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_path = tmp_path / "operator-public.pem"
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    readiness_key = Ed25519PrivateKey.generate().public_key()
    readiness_path = tmp_path / "readiness-public.pem"
    readiness_path.write_bytes(
        readiness_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    results = _run_results()
    run = SimpleNamespace(
        id=uuid4(),
        suite_key="premium_spb_de_exceptions_v1",
        mode="runtime",
        status="degraded",
        runtime_mode="proxy-only",
        route_registry_version="premium_spb_de_exceptions_v1",
        started_at=NOW - timedelta(minutes=6),
        finished_at=NOW - timedelta(minutes=5),
        summary={
            "execution_attempt_id": ATTEMPT_ID,
            "route_registry_version": "premium_spb_de_exceptions_v1",
            "task2_runtime_identity": {
                "bound": True,
                "backend_sha256": task2_runtime_identity_digest(BACKEND_IDENTITY),
                "agent_sha256": task2_runtime_identity_digest(AGENT_IDENTITY),
                "credentials_redacted": True,
            },
        },
        results=results,
    )
    settings = SimpleNamespace(
        vpn_tester_task2_operator_evidence_enabled=True,
        vpn_tester_task2_operator_evidence_max_body_bytes=65536,
        vpn_tester_task2_operator_evidence_key_id=KEY_ID,
        vpn_tester_task2_operator_evidence_revoked_key_ids="",
        vpn_tester_task2_operator_evidence_max_skew_seconds=60,
        vpn_tester_task2_operator_evidence_max_validity_seconds=900,
        vpn_tester_task2_operator_evidence_max_fault_seconds=240,
        vpn_tester_task2_operator_evidence_public_key_path=str(public_path),
        remnawave_spb_de_exceptions_readiness_public_key_path=str(readiness_path),
        remnawave_spb_de_exceptions_readiness_public_key="",
    )
    route_entries = [
        SimpleNamespace(metadata_json={"category": category, "communities": COMMUNITIES[category]})
        for category in TASK2_ANTIFILTER_CATEGORIES
    ]
    return run, settings, route_entries, private_key


def _verify(context, envelope: dict[str, Any]):
    run, settings, route_entries, _private_key = context
    return verify_task2_runtime_fault_evidence(
        canonical_json_bytes(envelope),
        run=run,
        route_entries=route_entries,
        settings_obj=settings,
        now=NOW,
    )


def test_valid_signed_fault_evidence_promotes_only_current_attempt(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    verified = _verify(evidence_context, _signed_envelope(run, private_key))

    assert verified.envelope.header.schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA
    assert verified.envelope.payload.schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA
    assert verified.execution_attempt_id == ATTEMPT_ID
    assert verified.artifact()["artifact_key"] == f"task2-runtime-fault:{ATTEMPT_ID}"
    assert "envelope" not in verified.artifact()["preview"]
    assert verified.artifact()["preview"]["summary"]["credentials_redacted"] is True
    promoted = promote_task2_runtime_fault_results(run, verified)
    assert backend_result_set_digest(promoted) == verified.envelope.payload.backend_result_set_digest
    promoted_by_key = {item["check_key"]: item for item in promoted}
    for check_key in (
        "premium_spb_de_exceptions.selected_outbound.matrix",
        "premium_spb_de_exceptions.bridge_down_fail_closed",
        "premium_spb_de_exceptions.runtime_evidence",
        "premium_spb_de_exceptions.runtime.completeness",
    ):
        assert promoted_by_key[check_key]["status"] == "pass"
        assert promoted_by_key[check_key]["details"]["execution_attempt_id"] == ATTEMPT_ID


def test_valid_v2_signed_fault_evidence_verifies_online_and_offline(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope_v2(run, private_key)

    online = _verify(evidence_context, envelope)
    published = verify_published_task2_runtime_fault_evidence(
        canonical_json_bytes(envelope),
        public_key_material=_public_key_material(private_key),
    )

    expected_public_key_sha256 = _operator_public_key_sha256(private_key)
    assert online.envelope.header.schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2
    assert online.envelope.payload.schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2
    assert online.payload_sha256 == published.payload_sha256
    assert online.envelope_sha256 == published.envelope_sha256
    assert published.operator_public_key_sha256 == expected_public_key_sha256
    assert published.baseline_capture_sha256 == "0" * 64
    assert published.envelope.payload.auxiliary_runs.fault.execution_attempt_id == "2" * 32
    assert published.envelope.payload.auxiliary_runs.post_restore.execution_attempt_id == "3" * 32


def test_published_v1_evidence_is_rejected_for_ac_close_publication(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="published_evidence_requires_v2"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(envelope),
            public_key_material=_public_key_material(private_key),
        )


def test_v2_auxiliary_run_id_tamper_is_rejected_by_payload_hash(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope_v2(run, private_key)
    envelope["payload"]["auxiliary_runs"]["fault"]["run_id"] = str(uuid4())

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="payload_digest_mismatch"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(envelope),
            public_key_material=_public_key_material(private_key),
        )


def test_v2_auxiliary_capture_hash_tamper_is_rejected_by_payload_hash(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope_v2(run, private_key)
    envelope["payload"]["auxiliary_runs"]["fault"]["canonical_sanitized_capture_sha256"] = "c" * 64

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="payload_digest_mismatch"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(envelope),
            public_key_material=_public_key_material(private_key),
        )


def test_v2_baseline_capture_hash_tamper_is_rejected_by_payload_hash(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope_v2(run, private_key)
    envelope["payload"]["baseline_capture_sha256"] = "d" * 64

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="payload_digest_mismatch"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(envelope),
            public_key_material=_public_key_material(private_key),
        )


def test_published_v2_public_key_mismatch_is_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    wrong_private_key = Ed25519PrivateKey.generate()

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="invalid_signature"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(_signed_envelope_v2(run, private_key)),
            public_key_material=_public_key_material(wrong_private_key),
        )


def test_published_v2_noncanonical_json_is_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    pretty_body = json.dumps(_signed_envelope_v2(run, private_key), indent=2, sort_keys=True).encode()

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="noncanonical_json"):
        verify_published_task2_runtime_fault_evidence(
            pretty_body,
            public_key_material=_public_key_material(private_key),
        )


def test_published_v2_duplicate_json_keys_are_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    body = canonical_json_bytes(_signed_envelope_v2(run, private_key))
    body = body.replace(b'{"header":', b'{"header":{},"header":', 1)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="invalid_json"):
        verify_published_task2_runtime_fault_evidence(
            body,
            public_key_material=_public_key_material(private_key),
        )


def test_published_v2_sensitive_strings_are_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope_v2(run, private_key)
    envelope["payload"]["operator"]["instance"] = "bearer token"

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="sensitive_value_not_allowed"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(envelope),
            public_key_material=_public_key_material(private_key),
        )


def test_published_v2_private_key_pem_is_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    private_key_material = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="operator_public_key_private_pem"):
        verify_published_task2_runtime_fault_evidence(
            canonical_json_bytes(_signed_envelope_v2(run, private_key)),
            public_key_material=private_key_material,
        )


def test_signature_tampering_is_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    envelope["payload"]["fault"]["tcp_drop_counter"] += 1

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="payload_digest_mismatch"):
        _verify(evidence_context, envelope)


def test_execution_attempt_replay_is_rejected(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    run.summary["execution_attempt_id"] = "6" * 32

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="execution_attempt_mismatch"):
        _verify(evidence_context, envelope)


@pytest.mark.parametrize(
    ("identity", "field", "replacement", "reason"),
    [
        ("backend", "git_sha", "8" * 40, "backend_runtime_identity_mismatch"),
        ("backend", "image_ref", "cybervpn/backend:stale", "backend_runtime_identity_mismatch"),
        ("backend", "image_id", "sha256:" + "8" * 64, "backend_runtime_identity_mismatch"),
        ("backend", "instance", "wrong-prod-instance", "backend_runtime_identity_mismatch"),
        ("agent", "git_sha", "7" * 40, "agent_runtime_identity_mismatch"),
        ("agent", "image_ref", "cybervpn/vpn-test-agent:stale", "agent_runtime_identity_mismatch"),
        ("agent", "image_id", "sha256:" + "7" * 64, "agent_runtime_identity_mismatch"),
        ("agent", "instance", "wrong-agent", "agent_runtime_identity_mismatch"),
    ],
)
def test_signed_runtime_identity_must_match_execution_snapshot(
    evidence_context,
    identity: str,
    field: str,
    replacement: str,
    reason: str,
) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    envelope["payload"][identity][field] = replacement
    _resign(envelope, private_key)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match=reason):
        _verify(evidence_context, envelope)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda signature: signature + "=",
        lambda signature: "+" + signature[1:],
        lambda signature: signature + " ",
        lambda signature: signature + "A",
    ],
)
def test_noncanonical_signature_text_is_rejected(evidence_context, mutate) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    envelope["signature"] = mutate(envelope["signature"])

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="invalid_evidence_schema"):
        _verify(evidence_context, envelope)


def test_signed_evidence_cannot_promote_an_existing_failed_check(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    failed = next(
        result for result in run.results if result["check_key"] == "premium_spb_de_exceptions.bridge_down_fail_closed"
    )
    failed["status"] = "fail"

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="promotable_result_not_safe"):
        _verify(evidence_context, _signed_envelope(run, private_key))


def test_stale_run_cannot_be_promoted_by_a_fresh_signature(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    run.started_at = NOW - timedelta(minutes=31)
    run.finished_at = NOW - timedelta(minutes=30)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="run_evidence_too_old"):
        _verify(evidence_context, _signed_envelope(run, private_key))


def test_matched_fault_direct_fallback_is_rejected_by_strict_schema(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    matched = next(row for row in envelope["payload"]["fault_rows"] if row["traffic_class"] == "matched_exception")
    matched["selected_outbound"] = "DIRECT"

    with pytest.raises(ValidationError, match="matched_fault_not_fail_closed"):
        Task2RuntimeFaultPayload.model_validate_json(canonical_json_bytes(envelope["payload"]))


def test_cleanup_after_watchdog_deadline_is_rejected_by_strict_schema(evidence_context) -> None:
    run, _settings, _route_entries, private_key = evidence_context
    envelope = _signed_envelope(run, private_key)
    envelope["payload"]["fault"]["cleanup_verified_at"] = _iso(NOW)

    with pytest.raises(ValidationError, match="fault_cleanup_after_watchdog_deadline"):
        Task2RuntimeFaultPayload.model_validate_json(canonical_json_bytes(envelope["payload"]))


def test_duplicate_json_keys_are_rejected_before_signature_verification(evidence_context) -> None:
    run, settings, route_entries, private_key = evidence_context
    body = canonical_json_bytes(_signed_envelope(run, private_key))
    body = body.replace(b'{"header":', b'{"header":{},"header":', 1)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="invalid_json"):
        verify_task2_runtime_fault_evidence(
            body,
            run=run,
            route_entries=route_entries,
            settings_obj=settings,
            now=NOW,
        )


def test_readiness_key_reuse_is_rejected(evidence_context, tmp_path) -> None:
    run, settings, _route_entries, private_key = evidence_context
    readiness_path = tmp_path / "readiness-public.pem"
    readiness_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    settings.remnawave_spb_de_exceptions_readiness_public_key_path = str(readiness_path)

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="readiness_key_reuse"):
        _verify(evidence_context, _signed_envelope(run, private_key))


def test_conflicting_category_community_is_rejected(evidence_context) -> None:
    run, _settings, route_entries, private_key = evidence_context
    route_entries[0].metadata_json["communities"] = ["65444:999"]

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="category_communities_mismatch"):
        _verify(evidence_context, _signed_envelope(run, private_key))
