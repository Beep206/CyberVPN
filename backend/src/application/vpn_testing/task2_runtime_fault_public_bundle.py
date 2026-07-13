"""Offline verifier for public Task2 runtime fault evidence bundles."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from src.application.vpn_testing.task2_runtime_fault_evidence import (
    Task2RuntimeFaultEvidenceRejected,
    Task2RuntimeFaultPayloadV2,
    VerifiedTask2RuntimeFaultEvidence,
    backend_result_digest,
    backend_result_set_digest,
    canonical_json_bytes,
    verify_published_task2_runtime_fault_evidence,
)

TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_SCHEMA: Final = "cybervpn.task2.runtime-fault-evidence.public-bundle.v1"
TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_MANIFEST: Final = "manifest.json"
TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES: Final = (
    "operator-public-key.pem",
    "signed-envelope.json",
    "baseline-run.json",
    "fault-window-run.json",
    "post-restore-run.json",
)

_MAX_MANIFEST_BYTES: Final = 16 * 1024
_MAX_PUBLIC_KEY_BYTES: Final = 4 * 1024
_MAX_SIGNED_ENVELOPE_BYTES: Final = 65_536
_MAX_CAPTURE_BYTES: Final = 1024 * 1024
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_ATTEMPT_ID = re.compile(r"^[0-9a-f]{32}$")
_EMAIL_RE = re.compile(rb"(?i)[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,63}")
_JWT_TOKEN_RE = re.compile(
    rb"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])"
)
_SENSITIVE_BYTE_MARKERS: Final = (
    b"PRIVATE KEY",
    b"vless://",
    b'"vless"',
    b"'vless'",
    b"/api/sub",
    b"subscription",
    b"subscriber",
    b"customer_email",
    b"email_address",
    b"password",
    b"passwd",
    b"secret",
    b"cookie",
    b"refresh_token",
    b"access_token",
    b"bearer ",
)
_SELECTED_OUTBOUND_PREFIX: Final = "premium_spb_de_exceptions.selected_outbound."
_SAFE_DEGRADED_STATUSES: Final = {
    "run": "degraded",
    "premium_spb_de_exceptions.selected_outbound.matrix": "degraded",
    "premium_spb_de_exceptions.bridge_down_fail_closed": "degraded",
    "premium_spb_de_exceptions.runtime_evidence": "degraded",
    "premium_spb_de_exceptions.runtime.completeness": "degraded",
}
_FINGERPRINT_FIELDS: Final = (
    "route_key",
    "traffic_class",
    "category",
    "transport",
    "probe_network",
    "membership",
    "expected_outbound",
    "selected_outbound",
)


@dataclass(frozen=True)
class VerifiedTask2RuntimeFaultPublicBundle:
    """Safe public summary of a verified Task2 runtime fault evidence bundle."""

    verified_evidence: VerifiedTask2RuntimeFaultEvidence
    manifest_sha256: str
    artifact_sha256s: Mapping[str, str]
    baseline_run_id: str
    baseline_execution_attempt_id: str
    fault_run_id: str
    fault_execution_attempt_id: str
    post_restore_run_id: str
    post_restore_execution_attempt_id: str
    selected_outbound_count: int
    statuses: Mapping[str, str]

    def safe_summary(self) -> dict[str, Any]:
        payload = self.verified_evidence.envelope.payload
        if not isinstance(payload, Task2RuntimeFaultPayloadV2):
            raise Task2RuntimeFaultEvidenceRejected("published_evidence_requires_v2")
        return {
            "schema": TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_SCHEMA,
            "status": "verified",
            "manifest_sha256": self.manifest_sha256,
            "signed_envelope_sha256": self.verified_evidence.envelope_sha256,
            "payload_sha256": self.verified_evidence.payload_sha256,
            "operator_public_key_sha256": self.verified_evidence.operator_public_key_sha256,
            "baseline": {
                "run_id": self.baseline_run_id,
                "execution_attempt_id": self.baseline_execution_attempt_id,
                "canonical_sanitized_capture_sha256": payload.baseline_capture_sha256,
            },
            "fault": {
                "run_id": self.fault_run_id,
                "execution_attempt_id": self.fault_execution_attempt_id,
                "canonical_sanitized_capture_sha256": (payload.auxiliary_runs.fault.canonical_sanitized_capture_sha256),
            },
            "post_restore": {
                "run_id": self.post_restore_run_id,
                "execution_attempt_id": self.post_restore_execution_attempt_id,
                "canonical_sanitized_capture_sha256": (
                    payload.auxiliary_runs.post_restore.canonical_sanitized_capture_sha256
                ),
            },
            "selected_outbound_count": self.selected_outbound_count,
            "statuses": dict(self.statuses),
            "credentials_redacted": True,
        }


@dataclass(frozen=True)
class _BundleArtifact:
    name: str
    raw: bytes
    sha256: str


@dataclass(frozen=True)
class _RunCapture:
    name: str
    data: Mapping[str, Any]
    canonical_sha256: str
    run: Mapping[str, Any]
    results: Sequence[Mapping[str, Any]]
    run_id: str
    execution_attempt_id: str
    status: str
    started_at: datetime
    finished_at: datetime


def verify_task2_runtime_fault_public_bundle(
    bundle_dir: str | Path,
    *,
    expected_operator_public_key_sha256: str,
    expected_manifest_sha256: str | None = None,
) -> VerifiedTask2RuntimeFaultPublicBundle:
    """Verify a public Task2 evidence bundle without network or production dependencies."""

    _validate_expected_sha256(
        expected_operator_public_key_sha256,
        reason="expected_operator_public_key_sha256_invalid",
    )
    if expected_manifest_sha256 is not None:
        _validate_expected_sha256(expected_manifest_sha256, reason="expected_manifest_sha256_invalid")
    root = _trusted_bundle_root(Path(bundle_dir))
    _require_exact_bundle_entries(root)
    manifest_artifact = _read_artifact(root, TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_MANIFEST, _MAX_MANIFEST_BYTES)
    manifest = _load_json_object(manifest_artifact.raw, label="bundle manifest")
    manifest_sha256 = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    if expected_manifest_sha256 is not None and not hmac.compare_digest(
        manifest_sha256,
        expected_manifest_sha256,
    ):
        raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_trust_anchor_mismatch")
    manifest_hashes = _manifest_hashes(manifest)

    public_key = _read_artifact(root, "operator-public-key.pem", _MAX_PUBLIC_KEY_BYTES)
    signed_envelope = _read_artifact(root, "signed-envelope.json", _MAX_SIGNED_ENVELOPE_BYTES)
    verified_evidence = verify_published_task2_runtime_fault_evidence(
        signed_envelope.raw,
        public_key_material=public_key.raw,
    )
    if verified_evidence.operator_public_key_sha256 is None or not hmac.compare_digest(
        verified_evidence.operator_public_key_sha256,
        expected_operator_public_key_sha256,
    ):
        raise Task2RuntimeFaultEvidenceRejected("operator_public_key_trust_anchor_mismatch")
    payload = verified_evidence.envelope.payload
    if not isinstance(payload, Task2RuntimeFaultPayloadV2):
        raise Task2RuntimeFaultEvidenceRejected("published_evidence_requires_v2")

    baseline = _load_capture(root, "baseline-run.json")
    fault = _load_capture(root, "fault-window-run.json")
    post_restore = _load_capture(root, "post-restore-run.json")
    artifact_sha256s = {
        "operator-public-key.pem": public_key.sha256,
        "signed-envelope.json": verified_evidence.envelope_sha256,
        "baseline-run.json": baseline.canonical_sha256,
        "fault-window-run.json": fault.canonical_sha256,
        "post-restore-run.json": post_restore.canonical_sha256,
    }
    for name, actual_sha256 in artifact_sha256s.items():
        if manifest_hashes[name] != actual_sha256:
            raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_artifact_digest_mismatch")

    _validate_capture_bindings(payload, baseline, fault, post_restore)
    _validate_baseline_backend_results(payload, baseline)
    selected_count = _validate_capture_fingerprints(payload, baseline, fault, post_restore)
    statuses = _validate_safe_degraded_statuses(baseline, fault, post_restore)
    _validate_capture_timestamps(payload, fault, post_restore)

    return VerifiedTask2RuntimeFaultPublicBundle(
        verified_evidence=verified_evidence,
        manifest_sha256=manifest_sha256,
        artifact_sha256s=artifact_sha256s,
        baseline_run_id=baseline.run_id,
        baseline_execution_attempt_id=baseline.execution_attempt_id,
        fault_run_id=fault.run_id,
        fault_execution_attempt_id=fault.execution_attempt_id,
        post_restore_run_id=post_restore.run_id,
        post_restore_execution_attempt_id=post_restore.execution_attempt_id,
        selected_outbound_count=selected_count,
        statuses=statuses,
    )


def _validate_expected_sha256(value: str, *, reason: str) -> None:
    if not _HEX_SHA256.fullmatch(value):
        raise Task2RuntimeFaultEvidenceRejected(reason)


def _trusted_bundle_root(path: Path) -> Path:
    try:
        if path.is_symlink():
            raise Task2RuntimeFaultEvidenceRejected("bundle_path_untrusted")
        resolved = path.expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise Task2RuntimeFaultEvidenceRejected("bundle_path_not_directory")
    except Task2RuntimeFaultEvidenceRejected:
        raise
    except OSError as exc:
        raise Task2RuntimeFaultEvidenceRejected("bundle_path_unavailable") from exc
    return resolved


def _require_exact_bundle_entries(root: Path) -> None:
    expected = {TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_MANIFEST, *TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES}
    try:
        entries = {item.name for item in root.iterdir()}
    except OSError as exc:
        raise Task2RuntimeFaultEvidenceRejected("bundle_path_unavailable") from exc
    if entries != expected:
        raise Task2RuntimeFaultEvidenceRejected("bundle_file_set_mismatch")
    for item in root.iterdir():
        try:
            item.relative_to(root)
            metadata = item.lstat()
        except (OSError, ValueError) as exc:
            raise Task2RuntimeFaultEvidenceRejected("bundle_path_untrusted") from exc
        if item.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise Task2RuntimeFaultEvidenceRejected("bundle_file_untrusted")


def _read_artifact(root: Path, name: str, max_bytes: int) -> _BundleArtifact:
    if name != Path(name).name:
        raise Task2RuntimeFaultEvidenceRejected("bundle_artifact_path_untrusted")
    path = root / name
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        metadata = resolved.stat()
    except (OSError, ValueError) as exc:
        raise Task2RuntimeFaultEvidenceRejected("bundle_artifact_unavailable") from exc
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size <= 0 or metadata.st_size > max_bytes:
        raise Task2RuntimeFaultEvidenceRejected("bundle_artifact_size_invalid")
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise Task2RuntimeFaultEvidenceRejected("bundle_artifact_unavailable") from exc
    _reject_sensitive_bytes(raw)
    return _BundleArtifact(name=name, raw=raw, sha256=hashlib.sha256(raw).hexdigest())


def _load_capture(root: Path, name: str) -> _RunCapture:
    artifact = _read_artifact(root, name, _MAX_CAPTURE_BYTES)
    data = _load_json_object(artifact.raw, label=name)
    canonical_sha256 = hashlib.sha256(canonical_json_bytes(data)).hexdigest()
    run = _extract_run(data)
    results = _extract_results(run)
    return _RunCapture(
        name=name,
        data=data,
        canonical_sha256=canonical_sha256,
        run=run,
        results=results,
        run_id=_capture_run_id(run),
        execution_attempt_id=_capture_execution_attempt_id(run),
        status=_string(run.get("status")),
        started_at=_capture_timestamp(run, "started_at"),
        finished_at=_capture_timestamp(run, "finished_at"),
    )


def _manifest_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    schema = manifest.get("schema")
    schema_version = manifest.get("schemaVersion")
    if schema != TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_SCHEMA or schema_version not in {None, 1}:
        raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_schema_invalid")
    raw_artifacts = manifest.get("artifacts")
    if raw_artifacts is None:
        raw_artifacts = manifest.get("files")
    if not isinstance(raw_artifacts, Mapping) or set(raw_artifacts) != set(TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES):
        raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_artifact_set_mismatch")
    hashes: dict[str, str] = {}
    for name in TASK2_RUNTIME_FAULT_PUBLIC_BUNDLE_FILES:
        value = raw_artifacts[name]
        if isinstance(value, str):
            sha256 = value
        elif isinstance(value, Mapping):
            declared_path = value.get("path")
            if declared_path is not None and declared_path != name:
                raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_artifact_path_mismatch")
            sha256 = value.get("sha256")
        else:
            raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_artifact_digest_invalid")
        if not isinstance(sha256, str) or not _HEX_SHA256.fullmatch(sha256):
            raise Task2RuntimeFaultEvidenceRejected("bundle_manifest_artifact_digest_invalid")
        hashes[name] = sha256
    return hashes


def _load_json_object(raw: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        decoded = raw.decode("utf-8")
        parsed = json.loads(
            decoded,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise Task2RuntimeFaultEvidenceRejected(f"{label}_invalid_json") from exc
    if not isinstance(parsed, Mapping):
        raise Task2RuntimeFaultEvidenceRejected(f"{label}_json_not_object")
    _reject_float_values(parsed)
    return parsed


def _reject_float(_value: str) -> None:
    raise ValueError("floats_not_allowed")


def _reject_constant(value: str) -> None:
    raise ValueError(f"json_constant_not_allowed:{value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_float_values(value: Any) -> None:
    if isinstance(value, float):
        raise Task2RuntimeFaultEvidenceRejected("floats_not_allowed")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_float_values(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_float_values(nested)


def _reject_sensitive_bytes(raw: bytes) -> None:
    lowered = raw.lower()
    if _EMAIL_RE.search(raw) or _JWT_TOKEN_RE.search(raw):
        raise Task2RuntimeFaultEvidenceRejected("bundle_sensitive_value_not_allowed")
    for marker in _SENSITIVE_BYTE_MARKERS:
        if marker.lower() in lowered:
            raise Task2RuntimeFaultEvidenceRejected("bundle_sensitive_value_not_allowed")


def _extract_run(data: Mapping[str, Any]) -> Mapping[str, Any]:
    candidate = data.get("run")
    if isinstance(candidate, Mapping):
        return candidate
    candidate = data.get("capture")
    if isinstance(candidate, Mapping) and isinstance(candidate.get("run"), Mapping):
        return candidate["run"]
    return data


def _extract_results(run: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    results = run.get("results")
    if not isinstance(results, list) or not results:
        raise Task2RuntimeFaultEvidenceRejected("capture_results_missing")
    normalized: list[Mapping[str, Any]] = []
    for result in results:
        if not isinstance(result, Mapping):
            raise Task2RuntimeFaultEvidenceRejected("capture_result_invalid")
        normalized.append(result)
    return normalized


def _capture_run_id(run: Mapping[str, Any]) -> str:
    run_id = _string(run.get("id") or run.get("run_id"))
    if not 32 <= len(run_id) <= 36:
        raise Task2RuntimeFaultEvidenceRejected("capture_run_id_invalid")
    return run_id


def _capture_execution_attempt_id(run: Mapping[str, Any]) -> str:
    summary = run.get("summary")
    summary = summary if isinstance(summary, Mapping) else {}
    attempt_id = _string(summary.get("execution_attempt_id") or run.get("execution_attempt_id"))
    if not _EXECUTION_ATTEMPT_ID.fullmatch(attempt_id):
        raise Task2RuntimeFaultEvidenceRejected("capture_execution_attempt_id_invalid")
    return attempt_id


def _capture_timestamp(run: Mapping[str, Any], field: str) -> datetime:
    value = _string(run.get(field))
    if not value:
        raise Task2RuntimeFaultEvidenceRejected("capture_timestamp_missing")
    try:
        normalized = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Task2RuntimeFaultEvidenceRejected("capture_timestamp_invalid") from exc
    if normalized.tzinfo is None or normalized.utcoffset() is None:
        raise Task2RuntimeFaultEvidenceRejected("capture_timestamp_invalid")
    return normalized.astimezone(UTC)


def _validate_capture_bindings(
    payload: Task2RuntimeFaultPayloadV2,
    baseline: _RunCapture,
    fault: _RunCapture,
    post_restore: _RunCapture,
) -> None:
    if baseline.run_id != payload.run_id or baseline.execution_attempt_id != payload.execution_attempt_id:
        raise Task2RuntimeFaultEvidenceRejected("baseline_capture_identity_mismatch")
    if baseline.canonical_sha256 != payload.baseline_capture_sha256:
        raise Task2RuntimeFaultEvidenceRejected("baseline_capture_digest_mismatch")
    if (
        fault.run_id != payload.auxiliary_runs.fault.run_id
        or fault.execution_attempt_id != payload.auxiliary_runs.fault.execution_attempt_id
    ):
        raise Task2RuntimeFaultEvidenceRejected("fault_capture_identity_mismatch")
    if fault.canonical_sha256 != payload.auxiliary_runs.fault.canonical_sanitized_capture_sha256:
        raise Task2RuntimeFaultEvidenceRejected("fault_capture_digest_mismatch")
    if (
        post_restore.run_id != payload.auxiliary_runs.post_restore.run_id
        or post_restore.execution_attempt_id != payload.auxiliary_runs.post_restore.execution_attempt_id
    ):
        raise Task2RuntimeFaultEvidenceRejected("post_restore_capture_identity_mismatch")
    if post_restore.canonical_sha256 != payload.auxiliary_runs.post_restore.canonical_sanitized_capture_sha256:
        raise Task2RuntimeFaultEvidenceRejected("post_restore_capture_digest_mismatch")


def _validate_baseline_backend_results(payload: Task2RuntimeFaultPayloadV2, baseline: _RunCapture) -> None:
    if payload.backend_result_set_digest != backend_result_set_digest(baseline.results):
        raise Task2RuntimeFaultEvidenceRejected("baseline_backend_result_set_digest_mismatch")
    by_route: dict[str, Mapping[str, Any]] = {}
    for result in _selected_outbound_results(baseline):
        details = _details(result)
        route_key = _string(details.get("route_key"))
        if route_key in by_route:
            raise Task2RuntimeFaultEvidenceRejected("baseline_selected_route_duplicate")
        by_route[route_key] = result
    for row in payload.pre_fault_rows:
        result = by_route.get(row.route_key)
        if result is None:
            raise Task2RuntimeFaultEvidenceRejected("baseline_selected_row_missing")
        if row.backend_result_digest != backend_result_digest(result):
            raise Task2RuntimeFaultEvidenceRejected("baseline_selected_row_digest_mismatch")
        details = _details(result)
        for field in _FINGERPRINT_FIELDS:
            expected = _string(details.get(field)) if field != "category" else _optional_string(details.get(field))
            actual = getattr(row, field)
            if actual != expected:
                raise Task2RuntimeFaultEvidenceRejected("baseline_selected_row_classification_mismatch")


def _validate_capture_fingerprints(
    payload: Task2RuntimeFaultPayloadV2,
    baseline: _RunCapture,
    fault: _RunCapture,
    post_restore: _RunCapture,
) -> int:
    signed_fingerprints = {
        row.route_key: (
            row.route_key,
            row.traffic_class,
            row.category,
            row.transport,
            row.probe_network,
            row.membership,
            row.expected_outbound,
            row.selected_outbound,
        )
        for row in payload.pre_fault_rows
    }
    if len(signed_fingerprints) != 21:
        raise Task2RuntimeFaultEvidenceRejected("signed_selected_fingerprint_count_mismatch")
    baseline_fingerprints = _capture_fingerprints(baseline)
    if baseline_fingerprints != signed_fingerprints:
        raise Task2RuntimeFaultEvidenceRejected("baseline_selected_fingerprint_mismatch")
    if _capture_fingerprints(fault) != signed_fingerprints:
        raise Task2RuntimeFaultEvidenceRejected("fault_selected_fingerprint_mismatch")
    if _capture_fingerprints(post_restore) != signed_fingerprints:
        raise Task2RuntimeFaultEvidenceRejected("post_restore_selected_fingerprint_mismatch")
    return len(signed_fingerprints)


def _capture_fingerprints(capture: _RunCapture) -> dict[str, tuple[str, str, str | None, str, str, str, str, str]]:
    fingerprints: dict[str, tuple[str, str, str | None, str, str, str, str, str]] = {}
    for result in _selected_outbound_results(capture):
        if _string(result.get("status")) != "pass":
            raise Task2RuntimeFaultEvidenceRejected("capture_selected_outbound_not_pass")
        details = _details(result)
        if _string(details.get("verdict")) != "pass":
            raise Task2RuntimeFaultEvidenceRejected("capture_selected_outbound_not_pass")
        route_key = _string(details.get("route_key"))
        if route_key in fingerprints:
            raise Task2RuntimeFaultEvidenceRejected("capture_selected_route_duplicate")
        fingerprints[route_key] = (
            route_key,
            _string(details.get("traffic_class")),
            _optional_string(details.get("category")),
            _string(details.get("transport")),
            _string(details.get("probe_network")),
            _string(details.get("membership")),
            _string(details.get("expected_outbound")),
            _string(details.get("selected_outbound")),
        )
    if len(fingerprints) != 21:
        raise Task2RuntimeFaultEvidenceRejected("capture_selected_fingerprint_count_mismatch")
    return fingerprints


def _selected_outbound_results(capture: _RunCapture) -> list[Mapping[str, Any]]:
    return [
        result
        for result in capture.results
        if _string(result.get("check_key")).startswith(_SELECTED_OUTBOUND_PREFIX)
        and not _string(result.get("check_key")).endswith(".matrix")
    ]


def _validate_safe_degraded_statuses(
    baseline: _RunCapture,
    fault: _RunCapture,
    post_restore: _RunCapture,
) -> Mapping[str, str]:
    statuses: dict[str, str] = {}
    for capture in (baseline, fault, post_restore):
        if capture.status != _SAFE_DEGRADED_STATUSES["run"]:
            raise Task2RuntimeFaultEvidenceRejected("capture_run_status_not_safe_degraded")
        statuses[f"{capture.name}:run"] = capture.status
        by_key = {_string(result.get("check_key")): result for result in capture.results}
        for check_key, expected_status in _SAFE_DEGRADED_STATUSES.items():
            if check_key == "run":
                continue
            result = by_key.get(check_key)
            if result is None:
                raise Task2RuntimeFaultEvidenceRejected("capture_safe_degraded_check_missing")
            actual = _string(result.get("status"))
            if actual != expected_status:
                raise Task2RuntimeFaultEvidenceRejected("capture_safe_degraded_status_mismatch")
            statuses[f"{capture.name}:{check_key}"] = actual
    return statuses


def _validate_capture_timestamps(
    payload: Task2RuntimeFaultPayloadV2,
    fault: _RunCapture,
    post_restore: _RunCapture,
) -> None:
    if fault.started_at < payload.fault.started_at or fault.finished_at > payload.fault.finished_at:
        raise Task2RuntimeFaultEvidenceRejected("fault_capture_outside_signed_fault_window")
    if fault.finished_at < fault.started_at:
        raise Task2RuntimeFaultEvidenceRejected("fault_capture_timestamp_order_invalid")
    if post_restore.started_at <= payload.fault.cleanup_verified_at:
        raise Task2RuntimeFaultEvidenceRejected("post_restore_capture_before_cleanup")
    if post_restore.finished_at < post_restore.started_at:
        raise Task2RuntimeFaultEvidenceRejected("post_restore_capture_timestamp_order_invalid")


def _details(result: Mapping[str, Any]) -> Mapping[str, Any]:
    details = result.get("details")
    if not isinstance(details, Mapping):
        raise Task2RuntimeFaultEvidenceRejected("capture_result_details_invalid")
    return details


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, str) else ""
