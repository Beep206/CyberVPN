from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self, cast

import jwt
from jwt import InvalidKeyError, InvalidTokenError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from src.config.settings import settings

SPB_DE_EXCEPTIONS_PRODUCT_CODE = "premium_spb_de_exceptions"
SMART_RU_PRODUCT_CODE = "premium_smart_ru"
TASK2_DATA_PLANE_NOT_READY_REASON = "spb_de_exceptions_data_plane_not_ready"
TASK2_READINESS_ATTESTATION_MISSING_REASON = "spb_de_exceptions_readiness_attestation_missing"
TASK2_READINESS_PUBLIC_KEY_MISSING_REASON = "spb_de_exceptions_readiness_public_key_missing"
TASK2_READINESS_SIGNATURE_INVALID_REASON = "spb_de_exceptions_readiness_signature_invalid"
TASK2_READINESS_ATTESTATION_INVALID_REASON = "spb_de_exceptions_readiness_attestation_invalid"
TASK2_READINESS_ATTESTATION_MISMATCH_REASON = "spb_de_exceptions_readiness_attestation_mismatch"
TASK2_READINESS_ATTESTATION_STALE_REASON = "spb_de_exceptions_readiness_attestation_stale"
TASK2_READINESS_ATTESTATION_FUTURE_REASON = "spb_de_exceptions_readiness_attestation_future"
TASK2_READINESS_ATTESTATION_REVOKED_REASON = "spb_de_exceptions_readiness_attestation_revoked"
TASK2_READINESS_ATTESTATION_UNAPPROVED_REASON = "spb_de_exceptions_readiness_attestation_unapproved"
TASK2_READINESS_STATE_MISSING_REASON = "spb_de_exceptions_readiness_state_missing"
TASK2_READINESS_STATE_INVALID_REASON = "spb_de_exceptions_readiness_state_invalid"
TASK2_READINESS_STATE_CHANGED_REASON = "spb_de_exceptions_readiness_state_changed"
TASK2_READINESS_STATE_NOT_PROMOTED_REASON = "spb_de_exceptions_readiness_state_not_promoted"
TASK2_READINESS_MANIFEST_MISMATCH_REASON = "spb_de_exceptions_readiness_manifest_mismatch"
PRODUCT_PLAN_MISMATCH_REASON = "subscription_product_plan_mismatch"
SPB_DE_EXCEPTIONS_READINESS_SCHEMA = "cybervpn.vpn_product_readiness_attestation"
SPB_DE_EXCEPTIONS_READINESS_SCHEMA_VERSION = 1
SPB_DE_EXCEPTIONS_READINESS_JWT_ALGORITHM = "EdDSA"
_MAX_READINESS_ATTESTATION_BYTES = 64 * 1024
_MAX_READINESS_PUBLIC_KEY_BYTES = 16 * 1024
_MAX_READINESS_POINTER_BYTES = 4 * 1024
_MAX_READINESS_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_PRODUCTION_ATTESTATION_PATH = "/run/cybervpn/readiness/task2/attestation.jwt"
_PRODUCTION_PUBLIC_KEY_PATH = "/run/cybervpn/readiness/task2/public-key.pem"
_PRODUCTION_READINESS_STORE_PATH = "/run/cybervpn/readiness/task2"
_PRODUCTION_POINTER_PATHS = {
    "active": "/run/cybervpn/readiness/task2/active.json",
    "last-known-good": "/run/cybervpn/readiness/task2/last-known-good.json",
}


class VpnProductReadinessError(ValueError):
    """Raised when a VPN product is not safe to expose or mutate."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


def normalize_plan_code(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def configured_plan_codes(raw_codes: str) -> set[str]:
    return {code for item in raw_codes.split(",") if (code := normalize_plan_code(item))}


def _text_or_empty(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, os.PathLike):
        return os.fspath(value).strip()
    if hasattr(value, "get_secret_value"):
        secret = value.get_secret_value()
        return secret.strip() if isinstance(secret, str) else ""
    return ""


def _is_production_environment() -> bool:
    return _text_or_empty(settings.environment).lower() == "production"


def _read_config_file_bytes(
    path_value: Any,
    *,
    max_bytes: int,
    missing_reason: str,
    invalid_reason: str,
    missing_message: str,
    invalid_message: str,
) -> bytes:
    path_text = _text_or_empty(path_value)
    if not path_text:
        raise VpnProductReadinessError(missing_reason, missing_message)

    try:
        path = Path(path_text).expanduser()
        if path.is_symlink():
            raise VpnProductReadinessError(invalid_reason, invalid_message)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode):
                raise VpnProductReadinessError(invalid_reason, invalid_message)
            if file_stat.st_size > max_bytes:
                raise VpnProductReadinessError(invalid_reason, invalid_message)
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                raw = handle.read(max_bytes + 1)
        finally:
            os.close(descriptor)
        if not raw:
            raise VpnProductReadinessError(missing_reason, missing_message)
    except VpnProductReadinessError:
        raise
    except FileNotFoundError as exc:
        raise VpnProductReadinessError(missing_reason, missing_message) from exc
    except OSError as exc:
        raise VpnProductReadinessError(invalid_reason, invalid_message) from exc

    if len(raw) > max_bytes:
        raise VpnProductReadinessError(invalid_reason, invalid_message)
    return raw


def _read_config_file_text(
    path_value: Any,
    *,
    max_bytes: int,
    missing_reason: str,
    invalid_reason: str,
    missing_message: str,
    invalid_message: str,
) -> str:
    raw = _read_config_file_bytes(
        path_value,
        max_bytes=max_bytes,
        missing_reason=missing_reason,
        invalid_reason=invalid_reason,
        missing_message=missing_message,
        invalid_message=invalid_message,
    )
    try:
        return raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise VpnProductReadinessError(invalid_reason, invalid_message) from exc


def _configured_attestation_token() -> str:
    token = _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_attestation)
    if token and _is_production_environment():
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_INVALID_REASON,
            "Premium SPB/DE readiness attestation must use the read-only file in production",
        )
    if (
        _is_production_environment()
        and _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_attestation_path)
        != _PRODUCTION_ATTESTATION_PATH
    ):
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_INVALID_REASON,
            "Premium SPB/DE readiness attestation path is not trusted",
        )
    if token:
        return token
    return _read_config_file_text(
        settings.remnawave_spb_de_exceptions_readiness_attestation_path,
        max_bytes=_MAX_READINESS_ATTESTATION_BYTES,
        missing_reason=TASK2_READINESS_ATTESTATION_MISSING_REASON,
        invalid_reason=TASK2_READINESS_ATTESTATION_INVALID_REASON,
        missing_message="Premium SPB/DE readiness attestation is not configured",
        invalid_message="Premium SPB/DE readiness attestation cannot be loaded safely",
    )


def _configured_public_key() -> str:
    public_key = _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_public_key)
    if public_key and _is_production_environment():
        raise VpnProductReadinessError(
            TASK2_READINESS_SIGNATURE_INVALID_REASON,
            "Premium SPB/DE readiness verification key must use the read-only file in production",
        )
    if (
        _is_production_environment()
        and _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_public_key_path)
        != _PRODUCTION_PUBLIC_KEY_PATH
    ):
        raise VpnProductReadinessError(
            TASK2_READINESS_SIGNATURE_INVALID_REASON,
            "Premium SPB/DE readiness verification key path is not trusted",
        )
    if public_key:
        return public_key
    return _read_config_file_text(
        settings.remnawave_spb_de_exceptions_readiness_public_key_path,
        max_bytes=_MAX_READINESS_PUBLIC_KEY_BYTES,
        missing_reason=TASK2_READINESS_PUBLIC_KEY_MISSING_REASON,
        invalid_reason=TASK2_READINESS_SIGNATURE_INVALID_REASON,
        missing_message="Premium SPB/DE readiness verification key is not configured",
        invalid_message="Premium SPB/DE readiness verification key cannot be loaded safely",
    )


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


class SpbDeExceptionsReadinessAttestation(BaseModel):
    """Signed, versioned operator attestation for exposing the Task2 product."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: str = Field(alias="schema")
    version: int
    product_key: str
    policy_version: str
    issued_at: datetime
    expires_at: datetime
    policy_hash: str | None = None
    policy_evidence_id: str | None = None
    manifest_hash: str | None = None
    manifest_evidence_id: str | None = None
    runtime_hash: str | None = None
    runtime_evidence_id: str | None = None
    attestation_id: str
    approval_status: str
    approved_at: datetime
    approved_by: str
    revoked: bool
    revocation_id: str | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = None

    @field_validator("issued_at", "expires_at", "approved_at", "revoked_at")
    @classmethod
    def require_aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_required_evidence(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        for value, label in (
            (self.schema_id, "schema"),
            (self.product_key, "product_key"),
            (self.policy_version, "policy_version"),
            (self.attestation_id, "attestation_id"),
            (self.approval_status, "approval_status"),
        ):
            if not _has_text(value):
                raise ValueError(f"{label} is required")
        if not _has_text(self.approved_by):
            raise ValueError("approved_by is required")
        for left, right, label in (
            (self.policy_hash, self.policy_evidence_id, "policy"),
            (self.manifest_hash, self.manifest_evidence_id, "manifest"),
            (self.runtime_hash, self.runtime_evidence_id, "runtime"),
        ):
            if not (_has_text(left) or _has_text(right)):
                raise ValueError(f"{label} hash or evidence id is required")
        return self


class AntifilterManifestPointer(BaseModel):
    """Strict pointer emitted by the atomic Antifilter publisher."""

    model_config = ConfigDict(extra="forbid")

    version: str
    manifest_sha256: str = Field(alias="manifestSha256")

    @field_validator("version", "manifest_sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("value must be a lowercase SHA-256")
        return value


def _configured_manifest_pointer(
    *,
    pointer_value: Any,
    path_value: Any,
    pointer_name: str,
) -> AntifilterManifestPointer:
    raw = _text_or_empty(pointer_value)
    if raw and _is_production_environment():
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            f"Premium SPB/DE {pointer_name} readiness pointer must use the read-only file in production",
        )
    if _is_production_environment() and _text_or_empty(path_value) != _PRODUCTION_POINTER_PATHS[pointer_name]:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            f"Premium SPB/DE {pointer_name} readiness pointer path is not trusted",
        )
    if not raw:
        raw = _read_config_file_text(
            path_value,
            max_bytes=_MAX_READINESS_POINTER_BYTES,
            missing_reason=TASK2_READINESS_STATE_MISSING_REASON,
            invalid_reason=TASK2_READINESS_STATE_INVALID_REASON,
            missing_message=f"Premium SPB/DE {pointer_name} readiness pointer is not configured",
            invalid_message=f"Premium SPB/DE {pointer_name} readiness pointer cannot be loaded safely",
        )
    try:
        payload = json.loads(raw)
        return AntifilterManifestPointer.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            f"Premium SPB/DE {pointer_name} readiness pointer is invalid",
        ) from exc


def _attested_manifest_sha256(value: str | None) -> str:
    normalized = _text_or_empty(value).lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.removeprefix("sha256:")
    if not _SHA256_RE.fullmatch(normalized):
        raise VpnProductReadinessError(
            TASK2_READINESS_MANIFEST_MISMATCH_REASON,
            "Premium SPB/DE readiness attestation has no usable manifest hash",
        )
    return normalized


def _configured_promoted_manifest(pointer: AntifilterManifestPointer) -> bytes:
    inline_manifest = _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_manifest)
    store_value = _text_or_empty(settings.remnawave_spb_de_exceptions_readiness_store_path)
    if inline_manifest and _is_production_environment():
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            "Premium SPB/DE readiness manifest must use the read-only store in production",
        )
    if _is_production_environment() and store_value != _PRODUCTION_READINESS_STORE_PATH:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            "Premium SPB/DE readiness store path is not trusted",
        )

    if inline_manifest:
        raw = inline_manifest.encode("utf-8")
    else:
        if not store_value:
            raise VpnProductReadinessError(
                TASK2_READINESS_STATE_MISSING_REASON,
                "Premium SPB/DE readiness store is not configured",
            )
        root = Path(store_value).expanduser()
        versions = root / "versions"
        version_dir = versions / pointer.version
        manifest_path = version_dir / "manifest.json"
        try:
            for component in (root, versions, version_dir, manifest_path):
                if component.is_symlink():
                    raise VpnProductReadinessError(
                        TASK2_READINESS_STATE_INVALID_REASON,
                        "Premium SPB/DE promoted manifest path is not trusted",
                    )
            manifest_path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except VpnProductReadinessError:
            raise
        except FileNotFoundError as exc:
            raise VpnProductReadinessError(
                TASK2_READINESS_STATE_MISSING_REASON,
                "Premium SPB/DE promoted manifest is missing",
            ) from exc
        except (OSError, ValueError) as exc:
            raise VpnProductReadinessError(
                TASK2_READINESS_STATE_INVALID_REASON,
                "Premium SPB/DE promoted manifest path is not trusted",
            ) from exc
        raw = _read_config_file_bytes(
            manifest_path,
            max_bytes=_MAX_READINESS_MANIFEST_BYTES,
            missing_reason=TASK2_READINESS_STATE_MISSING_REASON,
            invalid_reason=TASK2_READINESS_STATE_INVALID_REASON,
            missing_message="Premium SPB/DE promoted manifest is missing",
            invalid_message="Premium SPB/DE promoted manifest cannot be loaded safely",
        )

    if hashlib.sha256(raw).hexdigest() != pointer.manifest_sha256:
        raise VpnProductReadinessError(
            TASK2_READINESS_MANIFEST_MISMATCH_REASON,
            "Premium SPB/DE promoted manifest checksum does not match its pointer",
        )
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            "Premium SPB/DE promoted manifest is invalid",
        ) from exc
    if not isinstance(manifest, dict) or manifest.get("version") != pointer.version:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_INVALID_REASON,
            "Premium SPB/DE promoted manifest version does not match its pointer",
        )
    return raw


def ensure_spb_de_exceptions_manifest_state(
    attestation: SpbDeExceptionsReadinessAttestation,
    *,
    active_pointer: AntifilterManifestPointer,
    lkg_pointer: AntifilterManifestPointer,
) -> None:
    """Require a fully promoted artifact that matches the signed readiness claim."""

    if active_pointer != lkg_pointer:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_NOT_PROMOTED_REASON,
            "Premium SPB/DE active artifact is not promoted to last-known-good",
        )
    if _attested_manifest_sha256(attestation.manifest_hash) != active_pointer.manifest_sha256:
        raise VpnProductReadinessError(
            TASK2_READINESS_MANIFEST_MISMATCH_REASON,
            "Premium SPB/DE readiness attestation does not match the promoted manifest",
        )


def _decode_signed_readiness_attestation(*, attestation_token: str, public_key: str) -> Mapping[str, Any]:
    try:
        payload = jwt.decode(
            attestation_token,
            public_key,
            algorithms=[SPB_DE_EXCEPTIONS_READINESS_JWT_ALGORITHM],
            options={
                "verify_aud": False,
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
            },
        )
    except (InvalidTokenError, InvalidKeyError) as exc:
        raise VpnProductReadinessError(
            TASK2_READINESS_SIGNATURE_INVALID_REASON,
            "Premium SPB/DE readiness attestation signature is invalid",
        ) from exc
    if not isinstance(payload, Mapping):
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_INVALID_REASON,
            "Premium SPB/DE readiness attestation payload is invalid",
        )
    return cast(Mapping[str, Any], payload)


def evaluate_spb_de_exceptions_readiness_attestation(
    *,
    attestation_token: str,
    public_key: str,
    expected_policy_version: str,
    revoked_attestation_ids: str = "",
    now: datetime | None = None,
) -> SpbDeExceptionsReadinessAttestation:
    """Verify and validate the signed Task2 readiness artifact."""

    if not _text_or_empty(attestation_token):
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_MISSING_REASON,
            "Premium SPB/DE readiness attestation is not configured",
        )
    if not _text_or_empty(public_key):
        raise VpnProductReadinessError(
            TASK2_READINESS_PUBLIC_KEY_MISSING_REASON,
            "Premium SPB/DE readiness verification key is not configured",
        )

    payload = _decode_signed_readiness_attestation(attestation_token=attestation_token, public_key=public_key)
    try:
        attestation = SpbDeExceptionsReadinessAttestation.model_validate(payload)
    except ValidationError as exc:
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_INVALID_REASON,
            "Premium SPB/DE readiness attestation payload is invalid",
        ) from exc

    if (
        attestation.schema_id != SPB_DE_EXCEPTIONS_READINESS_SCHEMA
        or attestation.version != SPB_DE_EXCEPTIONS_READINESS_SCHEMA_VERSION
        or attestation.product_key != SPB_DE_EXCEPTIONS_PRODUCT_CODE
        or attestation.policy_version != expected_policy_version
    ):
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_MISMATCH_REASON,
            "Premium SPB/DE readiness attestation does not match the configured product",
        )

    if attestation.approval_status != "approved":
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_UNAPPROVED_REASON,
            "Premium SPB/DE readiness attestation is not approved",
        )

    if (
        attestation.revoked
        or attestation.revocation_id
        or attestation.revoked_at
        or attestation.revocation_reason
        or attestation.attestation_id.strip().lower() in configured_plan_codes(revoked_attestation_ids)
    ):
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_REVOKED_REASON,
            "Premium SPB/DE readiness attestation is revoked",
        )

    checked_at = now or datetime.now(UTC)
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_INVALID_REASON,
            "Premium SPB/DE readiness check time is invalid",
        )
    checked_at = checked_at.astimezone(UTC)
    if attestation.issued_at.astimezone(UTC) > checked_at:
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_FUTURE_REASON,
            "Premium SPB/DE readiness attestation is not yet valid",
        )
    if attestation.expires_at.astimezone(UTC) <= checked_at:
        raise VpnProductReadinessError(
            TASK2_READINESS_ATTESTATION_STALE_REASON,
            "Premium SPB/DE readiness attestation is stale",
        )

    return attestation


def is_spb_de_exceptions_plan(plan_code: Any) -> bool:
    """Return whether the plan is the Task2 SPB default with DE exceptions product."""

    normalized_plan_code = normalize_plan_code(plan_code)
    if not normalized_plan_code:
        return False
    if normalized_plan_code == SPB_DE_EXCEPTIONS_PRODUCT_CODE:
        return True
    if normalized_plan_code == SMART_RU_PRODUCT_CODE:
        return False
    smart_ru_plan_codes = configured_plan_codes(settings.remnawave_smart_ru_plan_codes)
    spb_de_plan_codes = configured_plan_codes(settings.remnawave_spb_de_exceptions_plan_codes)
    if normalized_plan_code in smart_ru_plan_codes and normalized_plan_code in spb_de_plan_codes:
        raise VpnProductReadinessError(
            PRODUCT_PLAN_MISMATCH_REASON,
            "VPN product plan code is configured for multiple routing products",
        )
    if normalized_plan_code in smart_ru_plan_codes:
        return False
    return normalized_plan_code in spb_de_plan_codes


def ensure_spb_de_exceptions_data_plane_ready(plan_code: Any) -> bool:
    """Fail closed for Task2 unless the kill switch is enabled and an attestation verifies."""

    if not is_spb_de_exceptions_plan(plan_code):
        return False
    if not settings.remnawave_spb_de_exceptions_data_plane_ready:
        raise VpnProductReadinessError(
            TASK2_DATA_PLANE_NOT_READY_REASON,
            "Premium SPB/DE data-plane is not marked ready",
        )
    attestation = evaluate_spb_de_exceptions_readiness_attestation(
        attestation_token=_configured_attestation_token(),
        public_key=_configured_public_key(),
        expected_policy_version=settings.remnawave_spb_de_exceptions_policy_version,
        revoked_attestation_ids=settings.remnawave_spb_de_exceptions_readiness_revoked_attestation_ids,
    )
    pointer_inputs = (
        (
            settings.remnawave_spb_de_exceptions_readiness_active_pointer,
            settings.remnawave_spb_de_exceptions_readiness_active_pointer_path,
            "active",
        ),
        (
            settings.remnawave_spb_de_exceptions_readiness_lkg_pointer,
            settings.remnawave_spb_de_exceptions_readiness_lkg_pointer_path,
            "last-known-good",
        ),
    )
    first_snapshot = tuple(
        _configured_manifest_pointer(pointer_value=value, path_value=path, pointer_name=name)
        for value, path, name in pointer_inputs
    )
    confirmed_snapshot = tuple(
        _configured_manifest_pointer(pointer_value=value, path_value=path, pointer_name=name)
        for value, path, name in pointer_inputs
    )
    if first_snapshot != confirmed_snapshot:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_CHANGED_REASON,
            "Premium SPB/DE readiness state changed during verification",
        )
    active_pointer, lkg_pointer = confirmed_snapshot
    ensure_spb_de_exceptions_manifest_state(
        attestation,
        active_pointer=active_pointer,
        lkg_pointer=lkg_pointer,
    )
    _configured_promoted_manifest(active_pointer)
    final_snapshot = tuple(
        _configured_manifest_pointer(pointer_value=value, path_value=path, pointer_name=name)
        for value, path, name in pointer_inputs
    )
    if final_snapshot != confirmed_snapshot:
        raise VpnProductReadinessError(
            TASK2_READINESS_STATE_CHANGED_REASON,
            "Premium SPB/DE readiness state changed during manifest verification",
        )
    return True


def plan_code_from_mapping(mapping: Mapping[str, Any] | None) -> str:
    if not isinstance(mapping, Mapping):
        return ""
    plan_code = normalize_plan_code(mapping.get("plan_code"))
    routing_product = normalize_plan_code(mapping.get("remnawave_routing_product"))
    if plan_code and routing_product and plan_code != routing_product:
        raise VpnProductReadinessError(
            PRODUCT_PLAN_MISMATCH_REASON,
            "Subscription product metadata is inconsistent",
        )
    return plan_code or routing_product


def resolve_gateway_product_plan_code(
    *,
    grant_snapshot: Mapping[str, Any] | None,
    service_context: Mapping[str, Any] | None,
) -> str:
    """Resolve public gateway product ownership from persisted authoritative metadata."""

    grant_plan_code = plan_code_from_mapping(grant_snapshot)
    identity_plan_code = plan_code_from_mapping(service_context)
    if grant_plan_code and identity_plan_code and grant_plan_code != identity_plan_code:
        raise VpnProductReadinessError(
            PRODUCT_PLAN_MISMATCH_REASON,
            "Subscription product metadata is inconsistent",
        )
    return grant_plan_code or identity_plan_code


def ensure_entitlement_grant_data_plane_ready(
    *,
    grant_snapshot: Mapping[str, Any] | None,
    service_context: Mapping[str, Any] | None = None,
    candidate_snapshot: Mapping[str, Any] | None = None,
) -> bool:
    """Validate product consistency and gate Task2 entitlement mutations."""

    checked_plan_codes: list[str] = []
    for source in (grant_snapshot, service_context, candidate_snapshot):
        if not isinstance(source, Mapping):
            continue
        for key in ("plan_code", "remnawave_routing_product"):
            normalized = normalize_plan_code(source.get(key))
            if normalized and normalized not in checked_plan_codes:
                checked_plan_codes.append(normalized)

    if len(checked_plan_codes) > 1:
        raise VpnProductReadinessError(
            PRODUCT_PLAN_MISMATCH_REASON,
            "Subscription product metadata is inconsistent",
        )

    for plan_code in checked_plan_codes:
        if ensure_spb_de_exceptions_data_plane_ready(plan_code):
            return True
    return False
