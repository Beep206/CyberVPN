"""Strict Ed25519 evidence verifier for Task2 runtime fault runs."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import ipaddress
import json
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from src.application.vpn_testing.task2_probe_plan import TASK2_ANTIFILTER_CATEGORIES

TASK2_RUNTIME_FAULT_EVIDENCE_ARTIFACT_TYPE: Final = "task2_runtime_fault_evidence"
TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA: Final = "cybervpn.task2.runtime-fault-evidence.envelope.v1"
TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA: Final = "cybervpn.task2.runtime-fault-evidence.payload.v1"
TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2: Final = "cybervpn.task2.runtime-fault-evidence.envelope.v2"
TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2: Final = "cybervpn.task2.runtime-fault-evidence.payload.v2"
TASK2_RUNTIME_FAULT_EVIDENCE_AUDIENCE: Final = "cybervpn.backend.vpn-tester.task2.runtime-fault-evidence"
TASK2_RUNTIME_FAULT_EVIDENCE_DOMAIN_SEPARATOR: Final = b"CYBERVPN TASK2 RUNTIME FAULT EVIDENCE ED25519 V1\n"
TASK2_RUNTIME_FAULT_EVIDENCE_DOMAIN_SEPARATOR_V2: Final = b"CYBERVPN TASK2 RUNTIME FAULT EVIDENCE ED25519 V2\n"
TASK2_RUNTIME_FAULT_EVIDENCE_PUBLIC_MAX_BODY_BYTES: Final = 65_536
TASK2_SUITE_KEY: Final = "premium_spb_de_exceptions_v1"
TASK2_RUNTIME_MODE: Final = "runtime"
TASK2_FAULT_SOURCE_IPV6: Final = "2a01:e5c0:1368::3"
TASK2_FAULT_DESTINATION_IPV6: Final = "2a0b:4140:ba84::2"
TASK2_FAULT_DESTINATION_PORT: Final = 9444
TASK2_PROMOTABLE_CHECK_KEYS: Final = frozenset(
    {
        "premium_spb_de_exceptions.bridge_down_fail_closed",
        "premium_spb_de_exceptions.runtime_evidence",
        "premium_spb_de_exceptions.selected_outbound.matrix",
        "premium_spb_de_exceptions.runtime.completeness",
    }
)

_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,159}$")
_SENSITIVE_MARKERS = (
    "vless://",
    "ss://",
    "trojan://",
    "/api/sub",
    "subscription",
    "password",
    "passwd",
    "secret",
    "cookie",
    "refresh_token",
    "access_token",
    "jwt",
    "bearer ",
)


class Task2RuntimeFaultEvidenceRejected(ValueError):
    """Evidence is syntactically valid enough to reject with a stable reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Task2RuntimeFaultEvidenceConflict(ValueError):
    """Evidence retry conflicts with an already persisted attempt artifact."""

    def __init__(self, reason: str = "conflicting_task2_runtime_fault_evidence") -> None:
        super().__init__(reason)
        self.reason = reason


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Task2EvidenceHeader(_StrictModel):
    schema_name: Literal["cybervpn.task2.runtime-fault-evidence.envelope.v1"] = Field(alias="schema")
    audience: Literal["cybervpn.backend.vpn-tester.task2.runtime-fault-evidence"]
    algorithm: Literal["Ed25519"]
    key_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_.:-]{7,79}$")
    nonce: str = Field(..., pattern=r"^[0-9a-f]{32,64}$")
    issued_at: datetime
    not_before: datetime
    expires_at: datetime
    payload_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @field_validator("issued_at", "not_before", "expires_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_must_be_aware")
        return value.astimezone(UTC)


class Task2EvidenceHeaderV2(Task2EvidenceHeader):
    schema_name: Literal["cybervpn.task2.runtime-fault-evidence.envelope.v2"] = Field(alias="schema")


class Task2RuntimeIdentity(_StrictModel):
    label: str = Field(..., min_length=1, max_length=160)
    git_sha: str = Field(..., pattern=r"^[0-9a-f]{7,64}$")
    image_ref: str = Field(..., min_length=1, max_length=200)
    image_id: str = Field(..., min_length=1, max_length=160)
    instance: str = Field(..., min_length=1, max_length=160)

    @field_validator("label", "image_ref", "image_id", "instance")
    @classmethod
    def safe_identity_label(cls, value: str) -> str:
        if not _SAFE_LABEL.fullmatch(value):
            raise ValueError("unsafe_identity_label")
        return value


class Task2FeedCategory(_StrictModel):
    category: str = Field(..., min_length=1, max_length=80)
    communities: list[str] = Field(..., min_length=1, max_length=8)
    ipv4_count: int = Field(..., ge=0, le=10_000_000)
    ipv6_count: int = Field(..., ge=0, le=10_000_000)
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class Task2FeedEvidence(_StrictModel):
    active_lkg_match: bool
    version: str = Field(..., min_length=1, max_length=128)
    generated_at: datetime
    active_pointer_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    last_known_good_pointer_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    active_manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    last_known_good_manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    union_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    ipv4_count: int = Field(..., ge=1, le=10_000_000)
    ipv6_count: int = Field(..., ge=0, le=10_000_000)
    categories: list[Task2FeedCategory] = Field(..., min_length=13, max_length=13)

    @field_validator("generated_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_must_be_aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def require_exact_categories(self) -> Task2FeedEvidence:
        categories = [item.category for item in self.categories]
        if set(categories) != set(TASK2_ANTIFILTER_CATEGORIES) or len(categories) != len(set(categories)):
            raise ValueError("task2_feed_categories_mismatch")
        if not self.active_lkg_match:
            raise ValueError("task2_feed_active_lkg_mismatch")
        if self.active_pointer_sha256 != self.last_known_good_pointer_sha256:
            raise ValueError("task2_feed_pointer_mismatch")
        if not (self.active_manifest_sha256 == self.last_known_good_manifest_sha256 == self.manifest_sha256):
            raise ValueError("task2_feed_manifest_mismatch")
        return self


class Task2SelectedOutboundRow(_StrictModel):
    route_key: str = Field(..., min_length=1, max_length=160)
    traffic_class: Literal["matched_exception", "unmatched_default"]
    category: str | None = Field(default=None, max_length=80)
    transport: Literal["raw", "xhttp"]
    probe_network: Literal["tcp", "udp"]
    membership: Literal["member", "non_member"]
    expected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT"]
    selected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT"]
    verdict: Literal["pass"]
    manifest_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    route_feed_version: str = Field(..., min_length=1, max_length=128)
    backend_result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class Task2FaultRow(_StrictModel):
    route_key: str = Field(..., min_length=1, max_length=160)
    traffic_class: Literal["matched_exception", "unmatched_default"]
    selected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT"]
    probe_succeeded: bool
    backend_result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class Task2RestoreRow(_StrictModel):
    route_key: str = Field(..., min_length=1, max_length=160)
    traffic_class: Literal["matched_exception", "unmatched_default"]
    selected_outbound: Literal["DE_EXCEPTIONS_BRIDGE", "DIRECT"]
    probe_succeeded: bool
    egress_region: Literal["DE", "SPB"]
    backend_result_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class Task2FirewallRuleEvidence(_StrictModel):
    rule_id: str = Field(..., min_length=1, max_length=160)
    rule_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    source_ipv6: str = Field(..., min_length=2, max_length=80)
    destination_ipv6: str = Field(..., min_length=2, max_length=80)
    destination_port: Literal[9444]
    protocol: Literal["tcp", "udp"]
    action: Literal["drop"]

    @field_validator("rule_id")
    @classmethod
    def safe_rule_id(cls, value: str) -> str:
        if not _SAFE_LABEL.fullmatch(value):
            raise ValueError("unsafe_firewall_rule_id")
        return value

    @field_validator("source_ipv6", "destination_ipv6")
    @classmethod
    def canonical_ipv6(cls, value: str) -> str:
        try:
            address = ipaddress.IPv6Address(value)
        except ipaddress.AddressValueError as exc:
            raise ValueError("invalid_fault_rule_ipv6") from exc
        if str(address) != value.lower():
            raise ValueError("noncanonical_fault_rule_ipv6")
        return str(address)


class Task2FaultWindowEvidence(_StrictModel):
    watchdog_armed_at: datetime
    watchdog_deadline_at: datetime
    started_at: datetime
    finished_at: datetime
    duration_seconds: int = Field(..., ge=1, le=3600)
    firewall_rules: list[Task2FirewallRuleEvidence] = Field(..., min_length=2, max_length=2)
    tcp_drop_counter: int = Field(..., gt=0, le=1_000_000_000)
    udp_drop_counter: int = Field(..., gt=0, le=1_000_000_000)
    watchdog_armed: bool
    cleanup_removed: bool
    cleanup_verified_at: datetime

    @field_validator(
        "watchdog_armed_at",
        "watchdog_deadline_at",
        "started_at",
        "finished_at",
        "cleanup_verified_at",
    )
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_must_be_aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_window(self) -> Task2FaultWindowEvidence:
        actual = (self.finished_at - self.started_at).total_seconds()
        if actual <= 0 or not (self.duration_seconds - 1 < actual <= self.duration_seconds):
            raise ValueError("fault_window_duration_mismatch")
        if not self.watchdog_armed or not self.cleanup_removed:
            raise ValueError("fault_cleanup_not_verified")
        if self.watchdog_armed_at > self.started_at:
            raise ValueError("fault_watchdog_armed_too_late")
        if self.watchdog_deadline_at < self.finished_at:
            raise ValueError("fault_watchdog_deadline_too_early")
        if self.cleanup_verified_at < self.finished_at:
            raise ValueError("fault_cleanup_before_window_finished")
        if self.cleanup_verified_at > self.watchdog_deadline_at:
            raise ValueError("fault_cleanup_after_watchdog_deadline")
        if {item.protocol for item in self.firewall_rules} != {"tcp", "udp"}:
            raise ValueError("fault_firewall_protocol_matrix_missing")
        tuples = {(item.source_ipv6, item.destination_ipv6, item.destination_port) for item in self.firewall_rules}
        if tuples != {(TASK2_FAULT_SOURCE_IPV6, TASK2_FAULT_DESTINATION_IPV6, TASK2_FAULT_DESTINATION_PORT)}:
            raise ValueError("fault_firewall_tuple_mismatch")
        for item in self.firewall_rules:
            digest_input = {
                "action": item.action,
                "destination_ipv6": item.destination_ipv6,
                "destination_port": item.destination_port,
                "protocol": item.protocol,
                "source_ipv6": item.source_ipv6,
            }
            if item.rule_sha256 != hashlib.sha256(canonical_json_bytes(digest_input)).hexdigest():
                raise ValueError("fault_firewall_rule_digest_mismatch")
        return self


class Task2PolicyEvidence(_StrictModel):
    dns_policy_verified: bool
    ipv6_policy_verified: bool
    dns_evidence_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    ipv6_evidence_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def require_policy_pass(self) -> Task2PolicyEvidence:
        if not self.dns_policy_verified or not self.ipv6_policy_verified:
            raise ValueError("task2_policy_evidence_missing")
        return self


class Task2RuntimeFaultPayload(_StrictModel):
    schema_name: Literal["cybervpn.task2.runtime-fault-evidence.payload.v1"] = Field(alias="schema")
    evidence_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_.:-]{7,79}$")
    run_id: str = Field(..., min_length=32, max_length=36)
    execution_attempt_id: str = Field(..., pattern=r"^[0-9a-f]{32}$")
    suite_key: Literal["premium_spb_de_exceptions_v1"]
    mode: Literal["runtime"]
    runtime_mode: str = Field(..., min_length=1, max_length=80)
    route_registry_version: str = Field(..., min_length=1, max_length=128)
    run_started_at: datetime
    run_finished_at: datetime
    backend: Task2RuntimeIdentity
    agent: Task2RuntimeIdentity
    operator: Task2RuntimeIdentity
    feed: Task2FeedEvidence
    backend_result_set_digest: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    pre_fault_rows: list[Task2SelectedOutboundRow] = Field(..., min_length=21, max_length=21)
    fault: Task2FaultWindowEvidence
    fault_rows: list[Task2FaultRow] = Field(..., min_length=21, max_length=21)
    post_restore_rows: list[Task2RestoreRow] = Field(..., min_length=21, max_length=21)
    policies: Task2PolicyEvidence

    @field_validator("run_started_at", "run_finished_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp_must_be_aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_rows(self) -> Task2RuntimeFaultPayload:
        if self.run_finished_at < self.run_started_at:
            raise ValueError("run_finished_before_started")
        _validate_task2_row_sets(self.pre_fault_rows, self.fault_rows, self.post_restore_rows)
        if any(row.manifest_sha256 != self.feed.manifest_sha256 for row in self.pre_fault_rows):
            raise ValueError("selected_row_manifest_mismatch")
        if any(row.route_feed_version != self.feed.version for row in self.pre_fault_rows):
            raise ValueError("selected_row_feed_version_mismatch")
        return self


class Task2AuxiliaryRunBinding(_StrictModel):
    run_id: str = Field(..., min_length=32, max_length=36)
    execution_attempt_id: str = Field(..., pattern=r"^[0-9a-f]{32}$")
    canonical_sanitized_capture_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class Task2AuxiliaryRuns(_StrictModel):
    fault: Task2AuxiliaryRunBinding
    post_restore: Task2AuxiliaryRunBinding


class Task2RuntimeFaultPayloadV2(Task2RuntimeFaultPayload):
    schema_name: Literal["cybervpn.task2.runtime-fault-evidence.payload.v2"] = Field(alias="schema")
    baseline_capture_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    auxiliary_runs: Task2AuxiliaryRuns

    @model_validator(mode="after")
    def validate_auxiliary_runs(self) -> Task2RuntimeFaultPayloadV2:
        fault = self.auxiliary_runs.fault
        post_restore = self.auxiliary_runs.post_restore
        if fault.run_id == self.run_id or post_restore.run_id == self.run_id:
            raise ValueError("auxiliary_run_reuses_primary_run")
        if fault.run_id == post_restore.run_id:
            raise ValueError("auxiliary_run_ids_not_distinct")
        if fault.execution_attempt_id == self.execution_attempt_id:
            raise ValueError("fault_auxiliary_attempt_reuses_primary_attempt")
        if post_restore.execution_attempt_id == self.execution_attempt_id:
            raise ValueError("post_restore_auxiliary_attempt_reuses_primary_attempt")
        if fault.execution_attempt_id == post_restore.execution_attempt_id:
            raise ValueError("auxiliary_execution_attempt_ids_not_distinct")
        return self


class Task2RuntimeFaultEnvelope(_StrictModel):
    header: Task2EvidenceHeader
    payload: Task2RuntimeFaultPayload
    signature: str = Field(..., pattern=r"^[A-Za-z0-9_-]{86}$")


class Task2RuntimeFaultEnvelopeV2(_StrictModel):
    header: Task2EvidenceHeaderV2
    payload: Task2RuntimeFaultPayloadV2
    signature: str = Field(..., pattern=r"^[A-Za-z0-9_-]{86}$")


Task2EvidenceHeaderAny = Task2EvidenceHeader | Task2EvidenceHeaderV2
Task2RuntimeFaultPayloadAny = Task2RuntimeFaultPayload | Task2RuntimeFaultPayloadV2
Task2RuntimeFaultEnvelopeAny = Task2RuntimeFaultEnvelope | Task2RuntimeFaultEnvelopeV2


@dataclass(frozen=True)
class VerifiedTask2RuntimeFaultEvidence:
    envelope: Task2RuntimeFaultEnvelopeAny
    payload_sha256: str
    envelope_sha256: str
    operator_public_key_sha256: str | None = None

    @property
    def evidence_id(self) -> str:
        return self.envelope.payload.evidence_id

    @property
    def execution_attempt_id(self) -> str:
        return self.envelope.payload.execution_attempt_id

    @property
    def nonce(self) -> str:
        return self.envelope.header.nonce

    @property
    def baseline_capture_sha256(self) -> str | None:
        payload = self.envelope.payload
        if isinstance(payload, Task2RuntimeFaultPayloadV2):
            return payload.baseline_capture_sha256
        return None

    def artifact(self) -> dict[str, Any]:
        payload = self.envelope.payload
        return {
            "artifact_key": task2_runtime_fault_artifact_key(payload.execution_attempt_id),
            "artifact_type": TASK2_RUNTIME_FAULT_EVIDENCE_ARTIFACT_TYPE,
            "sha256": self.envelope_sha256,
            "preview": {
                "summary": {
                    "schema": payload.schema_name,
                    "evidence_id": payload.evidence_id,
                    "execution_attempt_id": payload.execution_attempt_id,
                    "nonce": self.envelope.header.nonce,
                    "key_id": self.envelope.header.key_id,
                    "payload_sha256": self.payload_sha256,
                    "canonical_sha256": self.envelope_sha256,
                    "fault_duration_seconds": payload.fault.duration_seconds,
                    "tcp_drop_counter": payload.fault.tcp_drop_counter,
                    "udp_drop_counter": payload.fault.udp_drop_counter,
                    "pre_fault_rows": len(payload.pre_fault_rows),
                    "fault_rows": len(payload.fault_rows),
                    "post_restore_rows": len(payload.post_restore_rows),
                    "credentials_redacted": True,
                },
            },
            "storage_uri": None,
            "expires_at": None,
        }


def task2_runtime_fault_artifact_key(execution_attempt_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", execution_attempt_id):
        raise Task2RuntimeFaultEvidenceRejected("invalid_execution_attempt_id")
    return f"task2-runtime-fault:{execution_attempt_id}"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def envelope_signing_bytes(header: Mapping[str, Any], payload: Mapping[str, Any]) -> bytes:
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    unsigned = canonical_json_bytes({"header": header, "payload": payload})
    return _domain_separator_for_header(header) + payload_sha256.encode("ascii") + b"\n" + unsigned


def _domain_separator_for_header(header: Mapping[str, Any]) -> bytes:
    schema_name = str(header.get("schema") or "")
    if schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA:
        return TASK2_RUNTIME_FAULT_EVIDENCE_DOMAIN_SEPARATOR
    if schema_name == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2:
        return TASK2_RUNTIME_FAULT_EVIDENCE_DOMAIN_SEPARATOR_V2
    raise Task2RuntimeFaultEvidenceRejected("invalid_evidence_schema")


def backend_result_digest(result: Any) -> str:
    raw_details = _value(result, "details")
    details = dict(raw_details) if isinstance(raw_details, Mapping) else {}
    payload = {
        "check_key": _value(result, "check_key"),
        "status": _value(result, "status"),
        "target": _value(result, "target"),
        "details": {
            key: details.get(key)
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
                "digest",
                "manifest_sha256",
                "route_feed_version",
            )
        },
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _backend_result_row_key(row: dict[str, str]) -> str:
    return row["check_key"]


def backend_result_set_digest(results: Sequence[Any]) -> str:
    rows: list[dict[str, str]] = []
    matrix: dict[str, Any] | None = None
    for result in results:
        check_key = str(_value(result, "check_key") or "")
        if check_key.startswith("premium_spb_de_exceptions.selected_outbound."):
            if check_key.endswith(".matrix"):
                raw_details = _value(result, "details")
                details = dict(raw_details) if isinstance(raw_details, Mapping) else {}
                matrix = {
                    "check_key": check_key,
                    "details": {
                        key: details.get(key)
                        for key in (
                            "expected_count",
                            "actual_count",
                            "all_13_categories_declared",
                            "raw_xhttp_tcp_udp_declared",
                            "agent_id",
                        )
                    },
                }
            else:
                rows.append({"check_key": check_key, "digest": backend_result_digest(result)})
    rows.sort(key=_backend_result_row_key)
    digest_input = {"matrix": matrix, "rows": rows}
    return hashlib.sha256(canonical_json_bytes(digest_input)).hexdigest()


def task2_runtime_identity_digest(identity: Mapping[str, Any] | Task2RuntimeIdentity) -> str:
    if isinstance(identity, Task2RuntimeIdentity):
        normalized = identity.model_dump(mode="json")
    else:
        normalized = Task2RuntimeIdentity.model_validate(identity).model_dump(mode="json")
    return hashlib.sha256(canonical_json_bytes(normalized)).hexdigest()


def parse_task2_runtime_fault_envelope(
    raw_body: bytes,
    *,
    max_body_bytes: int,
) -> tuple[Task2RuntimeFaultEnvelopeAny, str]:
    return _parse_task2_runtime_fault_envelope(
        raw_body,
        max_body_bytes=max_body_bytes,
        require_canonical=False,
    )


def _parse_task2_runtime_fault_envelope(
    raw_body: bytes,
    *,
    max_body_bytes: int,
    require_canonical: bool,
) -> tuple[Task2RuntimeFaultEnvelopeAny, str]:
    if len(raw_body) > max_body_bytes:
        raise Task2RuntimeFaultEvidenceRejected("body_too_large")
    try:
        decoded = raw_body.decode("utf-8")
        raw = json.loads(
            decoded,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise Task2RuntimeFaultEvidenceRejected("invalid_json") from exc
    if not isinstance(raw, Mapping):
        raise Task2RuntimeFaultEvidenceRejected("invalid_evidence_schema")
    _reject_float_values(raw)
    _reject_sensitive_strings(raw)
    canonical_body = canonical_json_bytes(raw)
    try:
        envelope = _validate_task2_runtime_fault_envelope(canonical_body, raw)
    except ValidationError as exc:
        raise Task2RuntimeFaultEvidenceRejected("invalid_evidence_schema") from exc
    normalized_envelope = envelope.model_dump(mode="json", by_alias=True)
    normalized_body = canonical_json_bytes(normalized_envelope)
    if require_canonical and raw_body != normalized_body:
        raise Task2RuntimeFaultEvidenceRejected("noncanonical_json")
    envelope_sha256 = hashlib.sha256(normalized_body).hexdigest()
    return envelope, envelope_sha256


def _validate_task2_runtime_fault_envelope(
    canonical_body: bytes,
    raw: Mapping[str, Any],
) -> Task2RuntimeFaultEnvelopeAny:
    header = raw.get("header")
    payload = raw.get("payload")
    if not isinstance(header, Mapping) or not isinstance(payload, Mapping):
        raise Task2RuntimeFaultEvidenceRejected("invalid_evidence_schema")
    header_schema = str(header.get("schema") or "")
    payload_schema = str(payload.get("schema") or "")
    if (
        header_schema == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA
        and payload_schema == TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA
    ):
        return Task2RuntimeFaultEnvelope.model_validate_json(canonical_body)
    if (
        header_schema == TASK2_RUNTIME_FAULT_EVIDENCE_SCHEMA_V2
        and payload_schema == TASK2_RUNTIME_FAULT_EVIDENCE_PAYLOAD_SCHEMA_V2
    ):
        return Task2RuntimeFaultEnvelopeV2.model_validate_json(canonical_body)
    raise Task2RuntimeFaultEvidenceRejected("invalid_evidence_schema")


def verify_task2_runtime_fault_evidence(
    raw_body: bytes,
    *,
    run: Any,
    route_entries: Sequence[Any],
    settings_obj: Any,
    now: datetime | None = None,
) -> VerifiedTask2RuntimeFaultEvidence:
    if not settings_obj.vpn_tester_task2_operator_evidence_enabled:
        raise Task2RuntimeFaultEvidenceRejected("operator_evidence_disabled")
    envelope, envelope_sha256 = parse_task2_runtime_fault_envelope(
        raw_body,
        max_body_bytes=int(settings_obj.vpn_tester_task2_operator_evidence_max_body_bytes),
    )

    _validate_header(envelope.header, settings_obj, now=now)
    payload_dict = envelope.payload.model_dump(mode="json", by_alias=True)
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload_dict)).hexdigest()
    if envelope.header.payload_sha256 != payload_sha256:
        raise Task2RuntimeFaultEvidenceRejected("payload_digest_mismatch")
    operator_public_key_sha256 = _verify_signature(envelope, payload_dict, settings_obj)

    _validate_against_run(envelope.payload, run, settings_obj)
    _validate_temporal_coherence(envelope, settings_obj)
    _validate_against_backend_results(envelope.payload, list(getattr(run, "results", []) or []), route_entries)

    return VerifiedTask2RuntimeFaultEvidence(
        envelope=envelope,
        payload_sha256=payload_sha256,
        envelope_sha256=envelope_sha256,
        operator_public_key_sha256=operator_public_key_sha256,
    )


def verify_published_task2_runtime_fault_evidence(
    raw_body: bytes,
    *,
    public_key_material: bytes,
) -> VerifiedTask2RuntimeFaultEvidence:
    envelope, envelope_sha256 = _parse_task2_runtime_fault_envelope(
        raw_body,
        max_body_bytes=TASK2_RUNTIME_FAULT_EVIDENCE_PUBLIC_MAX_BODY_BYTES,
        require_canonical=True,
    )
    if not isinstance(envelope, Task2RuntimeFaultEnvelopeV2):
        raise Task2RuntimeFaultEvidenceRejected("published_evidence_requires_v2")
    payload_dict = envelope.payload.model_dump(mode="json", by_alias=True)
    payload_sha256 = hashlib.sha256(canonical_json_bytes(payload_dict)).hexdigest()
    if envelope.header.payload_sha256 != payload_sha256:
        raise Task2RuntimeFaultEvidenceRejected("payload_digest_mismatch")
    public_key = _load_ed25519_public_key(public_key_material)
    operator_public_key_sha256 = _verify_signature_with_public_key(envelope, payload_dict, public_key)
    _validate_public_v2_auxiliary_bindings(envelope.payload)
    _validate_public_row_structure(envelope.payload)
    return VerifiedTask2RuntimeFaultEvidence(
        envelope=envelope,
        payload_sha256=payload_sha256,
        envelope_sha256=envelope_sha256,
        operator_public_key_sha256=operator_public_key_sha256,
    )


def promote_task2_runtime_fault_results(
    run: Any,
    verified: VerifiedTask2RuntimeFaultEvidence,
) -> list[dict[str, Any]]:
    payload = verified.envelope.payload
    promoted: list[dict[str, Any]] = []
    for result in list(getattr(run, "results", []) or []):
        item = _result_to_dict(result)
        check_key = item["check_key"]
        if check_key in TASK2_PROMOTABLE_CHECK_KEYS:
            item["status"] = "pass"
            item["severity"] = "error"
            item["safe_summary"] = "Signed Task2 runtime fault evidence passed for the current execution attempt"
            item["details"] = {
                **dict(item.get("details") or {}),
                "runtime_evidence_status": "signed_pass",
                "bridge_down_evidence_claimed": True,
                "execution_attempt_id": payload.execution_attempt_id,
                "evidence_id": payload.evidence_id,
                "payload_sha256": verified.payload_sha256,
                "backend_result_set_digest": payload.backend_result_set_digest,
                "tcp_drop_counter": payload.fault.tcp_drop_counter,
                "udp_drop_counter": payload.fault.udp_drop_counter,
                "fault_duration_seconds": payload.fault.duration_seconds,
                "cleanup_removed": payload.fault.cleanup_removed,
                "credentials_redacted": True,
            }
        elif check_key == "premium_spb_de_exceptions.dns_ipv6_leak_policy":
            item["details"] = {
                **dict(item.get("details") or {}),
                "dns_policy_runtime_evidence": payload.policies.dns_evidence_sha256,
                "ipv6_policy_runtime_evidence": payload.policies.ipv6_evidence_sha256,
                "runtime_evidence_status": "signed_pass",
                "credentials_redacted": True,
            }
        promoted.append(item)
    return promoted


def _validate_header(header: Task2EvidenceHeader, settings_obj: Any, *, now: datetime | None) -> None:
    if not hmac_compare(header.key_id, str(settings_obj.vpn_tester_task2_operator_evidence_key_id).strip()):
        raise Task2RuntimeFaultEvidenceRejected("key_id_mismatch")
    revoked = {
        item.strip()
        for item in str(settings_obj.vpn_tester_task2_operator_evidence_revoked_key_ids or "").split(",")
        if item.strip()
    }
    if header.key_id in revoked:
        raise Task2RuntimeFaultEvidenceRejected("key_revoked")
    clock = (now or datetime.now(UTC)).astimezone(UTC)
    skew = int(settings_obj.vpn_tester_task2_operator_evidence_max_skew_seconds)
    max_validity = int(settings_obj.vpn_tester_task2_operator_evidence_max_validity_seconds)
    if header.not_before > header.issued_at or header.issued_at >= header.expires_at:
        raise Task2RuntimeFaultEvidenceRejected("evidence_validity_invalid")
    if header.issued_at.timestamp() - clock.timestamp() > skew:
        raise Task2RuntimeFaultEvidenceRejected("evidence_issued_in_future")
    if header.not_before.timestamp() - clock.timestamp() > skew:
        raise Task2RuntimeFaultEvidenceRejected("evidence_not_yet_valid")
    if clock.timestamp() - header.expires_at.timestamp() > skew:
        raise Task2RuntimeFaultEvidenceRejected("evidence_expired")
    if int((header.expires_at - header.not_before).total_seconds()) > max_validity:
        raise Task2RuntimeFaultEvidenceRejected("evidence_validity_too_long")


def _verify_signature(
    envelope: Task2RuntimeFaultEnvelopeAny,
    payload_dict: Mapping[str, Any],
    settings_obj: Any,
) -> str:
    public_key = _load_operator_public_key(settings_obj)
    return _verify_signature_with_public_key(envelope, payload_dict, public_key)


def _verify_signature_with_public_key(
    envelope: Task2RuntimeFaultEnvelopeAny,
    payload_dict: Mapping[str, Any],
    public_key: Ed25519PublicKey,
) -> str:
    try:
        signature = _decode_base64url(envelope.signature)
    except (binascii.Error, ValueError) as exc:
        raise Task2RuntimeFaultEvidenceRejected("invalid_signature_encoding") from exc
    if len(signature) != 64:
        raise Task2RuntimeFaultEvidenceRejected("invalid_signature_length")
    canonical_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(canonical_signature, envelope.signature):
        raise Task2RuntimeFaultEvidenceRejected("noncanonical_signature_encoding")
    header_dict = envelope.header.model_dump(mode="json", by_alias=True)
    try:
        public_key.verify(signature, envelope_signing_bytes(header_dict, payload_dict))
    except InvalidSignature as exc:
        raise Task2RuntimeFaultEvidenceRejected("invalid_signature") from exc
    return _ed25519_public_key_sha256(public_key)


def _load_operator_public_key(settings_obj: Any) -> Ed25519PublicKey:
    path_value = str(settings_obj.vpn_tester_task2_operator_evidence_public_key_path).strip()
    if not path_value:
        raise Task2RuntimeFaultEvidenceRejected("operator_public_key_missing")
    path = Path(path_value)
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_size <= 0 or metadata.st_size > 4096:
            raise Task2RuntimeFaultEvidenceRejected("operator_public_key_untrusted")
        public_key = _load_ed25519_public_key(path.read_bytes())
    except Task2RuntimeFaultEvidenceRejected:
        raise
    except OSError as exc:
        raise Task2RuntimeFaultEvidenceRejected("operator_public_key_missing") from exc
    readiness_materials: list[bytes] = []
    readiness_path = str(settings_obj.remnawave_spb_de_exceptions_readiness_public_key_path or "").strip()
    if readiness_path:
        try:
            readiness_materials.append(Path(readiness_path).read_bytes())
        except OSError as exc:
            raise Task2RuntimeFaultEvidenceRejected("readiness_public_key_unavailable") from exc
    readiness_inline = str(settings_obj.remnawave_spb_de_exceptions_readiness_public_key or "").strip()
    if readiness_inline:
        readiness_materials.append(readiness_inline.encode("utf-8"))
    if not readiness_materials:
        raise Task2RuntimeFaultEvidenceRejected("readiness_public_key_missing")
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    for material in readiness_materials:
        try:
            readiness_key = _load_ed25519_public_key(material)
        except Task2RuntimeFaultEvidenceRejected as exc:
            raise Task2RuntimeFaultEvidenceRejected("readiness_public_key_invalid") from exc
        if public_raw == readiness_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ):
            raise Task2RuntimeFaultEvidenceRejected("readiness_key_reuse")
    return public_key


def _load_ed25519_public_key(material: bytes) -> Ed25519PublicKey:
    if b"PRIVATE KEY" in material.upper():
        raise Task2RuntimeFaultEvidenceRejected("operator_public_key_private_pem")
    try:
        key = serialization.load_pem_public_key(material)
    except ValueError as exc:
        raise Task2RuntimeFaultEvidenceRejected("invalid_operator_public_key") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise Task2RuntimeFaultEvidenceRejected("operator_public_key_not_ed25519")
    return key


def _ed25519_public_key_sha256(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()


def _validate_public_v2_auxiliary_bindings(payload: Task2RuntimeFaultPayloadV2) -> None:
    if not payload.baseline_capture_sha256:
        raise Task2RuntimeFaultEvidenceRejected("baseline_capture_digest_missing")
    fault = payload.auxiliary_runs.fault
    post_restore = payload.auxiliary_runs.post_restore
    if not fault.canonical_sanitized_capture_sha256 or not post_restore.canonical_sanitized_capture_sha256:
        raise Task2RuntimeFaultEvidenceRejected("auxiliary_capture_digest_missing")


def _validate_public_row_structure(payload: Task2RuntimeFaultPayloadV2) -> None:
    if len(payload.pre_fault_rows) != 21 or len(payload.fault_rows) != 21 or len(payload.post_restore_rows) != 21:
        raise Task2RuntimeFaultEvidenceRejected("task2_row_count_mismatch")
    try:
        _validate_task2_row_sets(payload.pre_fault_rows, payload.fault_rows, payload.post_restore_rows)
    except ValueError as exc:
        raise Task2RuntimeFaultEvidenceRejected(str(exc)) from exc
    if {row.transport for row in payload.pre_fault_rows} != {"raw", "xhttp"}:
        raise Task2RuntimeFaultEvidenceRejected("transport_matrix_missing")
    if {row.probe_network for row in payload.pre_fault_rows} != {"tcp", "udp"}:
        raise Task2RuntimeFaultEvidenceRejected("network_matrix_missing")
    if sum(1 for row in payload.pre_fault_rows if row.traffic_class == "matched_exception") != 17:
        raise Task2RuntimeFaultEvidenceRejected("matched_row_count_mismatch")
    if sum(1 for row in payload.pre_fault_rows if row.traffic_class == "unmatched_default") != 4:
        raise Task2RuntimeFaultEvidenceRejected("unmatched_row_count_mismatch")


def _validate_against_run(payload: Task2RuntimeFaultPayload, run: Any, settings_obj: Any) -> None:
    if str(payload.run_id) != str(getattr(run, "id", "")):
        raise Task2RuntimeFaultEvidenceRejected("run_id_mismatch")
    if str(getattr(run, "suite_key", "")) != TASK2_SUITE_KEY or str(getattr(run, "mode", "")) != TASK2_RUNTIME_MODE:
        raise Task2RuntimeFaultEvidenceRejected("run_scope_mismatch")
    if str(getattr(run, "status", "")) not in {"pass", "degraded", "fail"}:
        raise Task2RuntimeFaultEvidenceRejected("run_not_finished")
    summary = dict(getattr(run, "summary", None) or {})
    if payload.execution_attempt_id != str(summary.get("execution_attempt_id") or ""):
        raise Task2RuntimeFaultEvidenceRejected("execution_attempt_mismatch")
    runtime_identity = summary.get("task2_runtime_identity")
    if not isinstance(runtime_identity, Mapping) or runtime_identity.get("bound") is not True:
        raise Task2RuntimeFaultEvidenceRejected("runtime_identity_not_bound")
    expected_backend_digest = str(runtime_identity.get("backend_sha256") or "")
    expected_agent_digest = str(runtime_identity.get("agent_sha256") or "")
    if not hmac_compare(expected_backend_digest, task2_runtime_identity_digest(payload.backend)):
        raise Task2RuntimeFaultEvidenceRejected("backend_runtime_identity_mismatch")
    if not hmac_compare(expected_agent_digest, task2_runtime_identity_digest(payload.agent)):
        raise Task2RuntimeFaultEvidenceRejected("agent_runtime_identity_mismatch")
    route_registry_version = str(
        summary.get("route_registry_version") or getattr(run, "route_registry_version", "") or ""
    )
    if payload.route_registry_version != route_registry_version:
        raise Task2RuntimeFaultEvidenceRejected("route_registry_mismatch")
    if payload.runtime_mode != str(getattr(run, "runtime_mode", None) or "runtime"):
        raise Task2RuntimeFaultEvidenceRejected("runtime_mode_mismatch")
    started_at = getattr(run, "started_at", None)
    finished_at = getattr(run, "finished_at", None)
    if started_at and _seconds(payload.run_started_at) != _seconds(run.started_at):
        raise Task2RuntimeFaultEvidenceRejected("run_started_at_mismatch")
    if finished_at and _seconds(payload.run_finished_at) != _seconds(run.finished_at):
        raise Task2RuntimeFaultEvidenceRejected("run_finished_at_mismatch")
    if payload.fault.duration_seconds > int(settings_obj.vpn_tester_task2_operator_evidence_max_fault_seconds):
        raise Task2RuntimeFaultEvidenceRejected("fault_window_too_long")
    watchdog_window = (payload.fault.watchdog_deadline_at - payload.fault.started_at).total_seconds()
    if watchdog_window > int(settings_obj.vpn_tester_task2_operator_evidence_max_fault_seconds):
        raise Task2RuntimeFaultEvidenceRejected("fault_watchdog_window_too_long")


def _validate_temporal_coherence(
    envelope: Task2RuntimeFaultEnvelope,
    settings_obj: Any,
) -> None:
    header = envelope.header
    payload = envelope.payload
    fault = payload.fault
    if payload.feed.generated_at > payload.run_finished_at:
        raise Task2RuntimeFaultEvidenceRejected("feed_generated_after_run")
    if fault.watchdog_armed_at < payload.run_finished_at:
        raise Task2RuntimeFaultEvidenceRejected("fault_watchdog_armed_before_run_finished")
    if fault.started_at < payload.run_finished_at:
        raise Task2RuntimeFaultEvidenceRejected("fault_started_before_run_finished")
    if header.issued_at < fault.cleanup_verified_at:
        raise Task2RuntimeFaultEvidenceRejected("evidence_issued_before_fault_cleanup")
    evidence_age = (header.issued_at - payload.run_finished_at).total_seconds()
    if evidence_age < 0:
        raise Task2RuntimeFaultEvidenceRejected("evidence_issued_before_run_finished")
    if evidence_age > int(settings_obj.vpn_tester_task2_operator_evidence_max_validity_seconds):
        raise Task2RuntimeFaultEvidenceRejected("run_evidence_too_old")


def _validate_against_backend_results(
    payload: Task2RuntimeFaultPayload,
    results: list[Any],
    route_entries: Sequence[Any],
) -> None:
    promotable: dict[str, Any] = {}
    for result in results:
        check_key = str(_value(result, "check_key") or "")
        if check_key in TASK2_PROMOTABLE_CHECK_KEYS:
            if check_key in promotable:
                raise Task2RuntimeFaultEvidenceRejected("duplicate_promotable_result")
            promotable[check_key] = result
    if set(promotable) != set(TASK2_PROMOTABLE_CHECK_KEYS):
        raise Task2RuntimeFaultEvidenceRejected("promotable_result_set_mismatch")
    if any(str(_value(result, "status") or "") not in {"degraded", "pass"} for result in promotable.values()):
        raise Task2RuntimeFaultEvidenceRejected("promotable_result_not_safe")

    selected = [
        result
        for result in results
        if str(_value(result, "check_key") or "").startswith("premium_spb_de_exceptions.selected_outbound.")
        and not str(_value(result, "check_key") or "").endswith(".matrix")
    ]
    if len(selected) != 21 or any(str(_value(row, "status") or "") != "pass" for row in selected):
        raise Task2RuntimeFaultEvidenceRejected("backend_selected_rows_not_pass")
    if payload.backend_result_set_digest != backend_result_set_digest(results):
        raise Task2RuntimeFaultEvidenceRejected("backend_result_set_digest_mismatch")
    by_route: dict[str, Any] = {}
    for result in selected:
        details = dict(_value(result, "details") or {})
        by_route[str(details.get("route_key") or "")] = result

    seen_pre = set()
    for row in payload.pre_fault_rows:
        result = by_route.get(row.route_key)
        if result is None or row.backend_result_digest != backend_result_digest(result):
            raise Task2RuntimeFaultEvidenceRejected("selected_row_digest_mismatch")
        details = dict(_value(result, "details") or {})
        for field in (
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
        ):
            expected = details.get(field)
            actual = getattr(row, field)
            if actual != expected and not (field == "category" and actual is None and expected in {"", None}):
                raise Task2RuntimeFaultEvidenceRejected("selected_row_mismatch")
        seen_pre.add(row.route_key)
    if seen_pre != set(by_route):
        raise Task2RuntimeFaultEvidenceRejected("selected_row_set_mismatch")
    if {row.transport for row in payload.pre_fault_rows} != {"raw", "xhttp"}:
        raise Task2RuntimeFaultEvidenceRejected("transport_matrix_missing")
    if {row.probe_network for row in payload.pre_fault_rows} != {"tcp", "udp"}:
        raise Task2RuntimeFaultEvidenceRejected("network_matrix_missing")
    if sum(1 for row in payload.pre_fault_rows if row.traffic_class == "matched_exception") != 17:
        raise Task2RuntimeFaultEvidenceRejected("matched_row_count_mismatch")
    if sum(1 for row in payload.pre_fault_rows if row.traffic_class == "unmatched_default") != 4:
        raise Task2RuntimeFaultEvidenceRejected("unmatched_row_count_mismatch")
    if any(row.manifest_sha256 != payload.feed.manifest_sha256 for row in payload.pre_fault_rows):
        raise Task2RuntimeFaultEvidenceRejected("selected_row_manifest_mismatch")
    if any(row.route_feed_version != payload.feed.version for row in payload.pre_fault_rows):
        raise Task2RuntimeFaultEvidenceRejected("selected_row_feed_version_mismatch")
    _validate_category_communities(payload, route_entries)


def _validate_task2_row_sets(
    pre_rows: Sequence[Task2SelectedOutboundRow],
    fault_rows: Sequence[Task2FaultRow],
    restore_rows: Sequence[Task2RestoreRow],
) -> None:
    pre_by_route = {row.route_key: row for row in pre_rows}
    if len(pre_by_route) != 21:
        raise ValueError("duplicate_pre_fault_rows")
    fault_route_keys = {row.route_key for row in fault_rows}
    restore_route_keys = {row.route_key for row in restore_rows}
    if fault_route_keys != set(pre_by_route) or len(fault_route_keys) != 21:
        raise ValueError("fault_row_set_mismatch")
    if restore_route_keys != set(pre_by_route) or len(restore_route_keys) != 21:
        raise ValueError("restore_row_set_mismatch")
    for pre_row in pre_rows:
        if pre_row.traffic_class == "matched_exception" and pre_row.selected_outbound != "DE_EXCEPTIONS_BRIDGE":
            raise ValueError("matched_pre_fault_direct")
        if pre_row.traffic_class == "unmatched_default" and pre_row.selected_outbound != "DIRECT":
            raise ValueError("unmatched_pre_fault_not_direct")
    for fault_row in fault_rows:
        pre = pre_by_route[fault_row.route_key]
        if fault_row.backend_result_digest != pre.backend_result_digest or fault_row.traffic_class != pre.traffic_class:
            raise ValueError("fault_row_backend_mismatch")
        if fault_row.traffic_class == "matched_exception" and (
            fault_row.selected_outbound != "DE_EXCEPTIONS_BRIDGE" or fault_row.probe_succeeded
        ):
            raise ValueError("matched_fault_not_fail_closed")
        if fault_row.traffic_class == "unmatched_default" and (
            fault_row.selected_outbound != "DIRECT" or not fault_row.probe_succeeded
        ):
            raise ValueError("unmatched_fault_failed")
    for restore_row in restore_rows:
        pre = pre_by_route[restore_row.route_key]
        if (
            restore_row.backend_result_digest != pre.backend_result_digest
            or restore_row.traffic_class != pre.traffic_class
        ):
            raise ValueError("restore_row_backend_mismatch")
        if not restore_row.probe_succeeded:
            raise ValueError("restore_probe_failed")
        if restore_row.traffic_class == "matched_exception" and (
            restore_row.selected_outbound != "DE_EXCEPTIONS_BRIDGE" or restore_row.egress_region != "DE"
        ):
            raise ValueError("matched_restore_egress_mismatch")
        if restore_row.traffic_class == "unmatched_default" and (
            restore_row.selected_outbound != "DIRECT" or restore_row.egress_region != "SPB"
        ):
            raise ValueError("unmatched_restore_egress_mismatch")


def _validate_category_communities(payload: Task2RuntimeFaultPayload, route_entries: Sequence[Any]) -> None:
    expected: dict[str, list[str]] = {}
    for entry in route_entries:
        metadata = dict(getattr(entry, "metadata_json", None) or {})
        category = str(metadata.get("category") or "")
        communities = metadata.get("communities")
        if category in TASK2_ANTIFILTER_CATEGORIES and isinstance(communities, list):
            normalized = [str(item) for item in communities]
            if category in expected and expected[category] != normalized:
                raise Task2RuntimeFaultEvidenceRejected("route_registry_category_communities_conflict")
            expected[category] = normalized
    if set(expected) != set(TASK2_ANTIFILTER_CATEGORIES):
        raise Task2RuntimeFaultEvidenceRejected("route_registry_category_communities_missing")
    for item in payload.feed.categories:
        if item.communities != expected[item.category]:
            raise Task2RuntimeFaultEvidenceRejected("category_communities_mismatch")


def _result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "check_key": str(_value(result, "check_key") or ""),
        "check_name": str(_value(result, "check_name") or ""),
        "category": str(_value(result, "category") or ""),
        "status": str(_value(result, "status") or ""),
        "severity": str(_value(result, "severity") or ""),
        "target": str(_value(result, "target") or ""),
        "safe_summary": str(_value(result, "safe_summary") or ""),
        "details": dict(_value(result, "details") or {}),
        "duration_ms": int(_value(result, "duration_ms") or 0),
    }


def _value(result: Any, field: str) -> Any:
    if isinstance(result, Mapping):
        return result.get(field)
    return getattr(result, field, None)


def _seconds(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp())


def _decode_base64url(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]{86}", value):
        raise ValueError("invalid_base64url_signature")
    padding = "=" * (-len(value) % 4)
    return base64.b64decode((value + padding).encode("ascii"), altchars=b"-_", validate=True)


def _reject_float(value: str) -> None:
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


def _reject_sensitive_strings(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.lower()
        if "://" in lowered or any(marker in lowered for marker in _SENSITIVE_MARKERS):
            raise Task2RuntimeFaultEvidenceRejected("sensitive_value_not_allowed")
    elif isinstance(value, Mapping):
        for nested in value.values():
            _reject_sensitive_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_sensitive_strings(nested)


def hmac_compare(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(left, right)
