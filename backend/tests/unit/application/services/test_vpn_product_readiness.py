from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest

import src.application.services.vpn_product_readiness as readiness_module
from src.application.services.vpn_product_readiness import (
    PRODUCT_PLAN_MISMATCH_REASON,
    SMART_RU_PRODUCT_CODE,
    SPB_DE_EXCEPTIONS_PRODUCT_CODE,
    TASK2_DATA_PLANE_NOT_READY_REASON,
    TASK2_READINESS_ATTESTATION_FUTURE_REASON,
    TASK2_READINESS_ATTESTATION_INVALID_REASON,
    TASK2_READINESS_ATTESTATION_MISMATCH_REASON,
    TASK2_READINESS_ATTESTATION_MISSING_REASON,
    TASK2_READINESS_ATTESTATION_REVOKED_REASON,
    TASK2_READINESS_ATTESTATION_STALE_REASON,
    TASK2_READINESS_ATTESTATION_UNAPPROVED_REASON,
    TASK2_READINESS_MANIFEST_MISMATCH_REASON,
    TASK2_READINESS_PUBLIC_KEY_MISSING_REASON,
    TASK2_READINESS_SIGNATURE_INVALID_REASON,
    TASK2_READINESS_STATE_CHANGED_REASON,
    TASK2_READINESS_STATE_INVALID_REASON,
    TASK2_READINESS_STATE_MISSING_REASON,
    TASK2_READINESS_STATE_NOT_PROMOTED_REASON,
    AntifilterManifestPointer,
    VpnProductReadinessError,
    ensure_entitlement_grant_data_plane_ready,
    ensure_spb_de_exceptions_data_plane_ready,
    ensure_spb_de_exceptions_manifest_state,
    evaluate_spb_de_exceptions_readiness_attestation,
    resolve_gateway_product_plan_code,
)
from src.config.settings import settings
from tests.helpers.spb_de_readiness import (
    TEST_MANIFEST_JSON,
    TEST_MANIFEST_SHA256,
    TEST_MANIFEST_VERSION,
    enable_spb_de_readiness,
    make_spb_de_readiness_attestation,
    manifest_pointer_json,
)

CHECKED_AT = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


def _configure_direct_readiness(monkeypatch: pytest.MonkeyPatch, *, token: str, public_key: str) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", token)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", public_key)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", "")


def _assert_reason(exc_info: pytest.ExceptionInfo[VpnProductReadinessError], reason: str) -> None:
    assert exc_info.value.reason == reason


def _write_manifest_store(root: Path, raw: bytes = TEST_MANIFEST_JSON.encode("utf-8")) -> Path:
    manifest_path = root / "versions" / TEST_MANIFEST_VERSION / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(raw)
    return root


def test_valid_signed_attestation_allows_task2_when_kill_switch_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)

    assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True
    attestation = evaluate_spb_de_exceptions_readiness_attestation(
        attestation_token=artifact.token,
        public_key=artifact.public_key,
        expected_policy_version="premium_spb_de_exceptions.v1",
        now=CHECKED_AT,
    )

    assert attestation.product_key == SPB_DE_EXCEPTIONS_PRODUCT_CODE
    assert attestation.policy_hash == "sha256:policy-ready"
    assert attestation.manifest_hash == f"sha256:{TEST_MANIFEST_SHA256}"
    assert attestation.runtime_evidence_id == "task2-runtime-evidence-20260711"


def test_kill_switch_false_blocks_even_with_valid_attestation(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_DATA_PLANE_NOT_READY_REASON)


def test_task2_true_without_attestation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_ATTESTATION_MISSING_REASON)


def test_task2_true_without_public_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = make_spb_de_readiness_attestation()
    _configure_direct_readiness(monkeypatch, token=artifact.token, public_key="")

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_PUBLIC_KEY_MISSING_REASON)


def test_readiness_can_use_configured_artifact_and_public_key_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    artifact = make_spb_de_readiness_attestation()
    attestation_path = tmp_path / "task2-readiness.jwt"
    public_key_path = tmp_path / "task2-readiness.pub"
    active_pointer_path = tmp_path / "active.json"
    lkg_pointer_path = tmp_path / "last-known-good.json"
    attestation_path.write_text(artifact.token, encoding="utf-8")
    public_key_path.write_text(artifact.public_key, encoding="utf-8")
    active_pointer_path.write_text(manifest_pointer_json(), encoding="utf-8")
    lkg_pointer_path.write_text(manifest_pointer_json(), encoding="utf-8")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", str(attestation_path))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", str(public_key_path))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_active_pointer_path",
        str(active_pointer_path),
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_lkg_pointer_path",
        str(lkg_pointer_path),
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", TEST_MANIFEST_JSON)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_store_path", "")

    assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True


def test_manifest_state_requires_signed_hash_to_match_fully_promoted_pointer() -> None:
    artifact = make_spb_de_readiness_attestation()
    attestation = evaluate_spb_de_exceptions_readiness_attestation(
        attestation_token=artifact.token,
        public_key=artifact.public_key,
        expected_policy_version="premium_spb_de_exceptions.v1",
        now=CHECKED_AT,
    )
    pointer = AntifilterManifestPointer.model_validate_json(manifest_pointer_json())

    ensure_spb_de_exceptions_manifest_state(
        attestation,
        active_pointer=pointer,
        lkg_pointer=pointer,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"version": "A" * 64, "manifestSha256": TEST_MANIFEST_SHA256},
        {"version": TEST_MANIFEST_VERSION, "manifestSha256": "A" * 64},
        {"version": TEST_MANIFEST_VERSION, "manifest_sha256": TEST_MANIFEST_SHA256},
        {
            "version": TEST_MANIFEST_VERSION,
            "manifestSha256": TEST_MANIFEST_SHA256,
            "unexpected": True,
        },
    ],
)
def test_manifest_pointer_rejects_non_publisher_shape(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AntifilterManifestPointer.model_validate(payload)


def test_production_rejects_inline_manifest_pointers(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(readiness_module, "_configured_attestation_token", lambda: artifact.token)
    monkeypatch.setattr(readiness_module, "_configured_public_key", lambda: artifact.public_key)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


@pytest.mark.parametrize("environment", ["Production", "PRODUCTION", " production "])
def test_production_environment_variants_reject_inline_manifest_pointers(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "environment", environment)
    monkeypatch.setattr(readiness_module, "_configured_attestation_token", lambda: artifact.token)
    monkeypatch.setattr(readiness_module, "_configured_public_key", lambda: artifact.public_key)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_production_rejects_inline_attestation(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_attestation_path",
        "/run/cybervpn/readiness/task2/attestation.jwt",
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_ATTESTATION_INVALID_REASON)


def test_production_rejects_inline_public_key(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(readiness_module, "_configured_attestation_token", lambda: artifact.token)
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_public_key_path",
        "/run/cybervpn/readiness/task2/public-key.pem",
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_SIGNATURE_INVALID_REASON)


def test_production_rejects_inline_promoted_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    pointer = AntifilterManifestPointer.model_validate_json(manifest_pointer_json())
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(readiness_module, "_configured_attestation_token", lambda: artifact.token)
    monkeypatch.setattr(readiness_module, "_configured_public_key", lambda: artifact.public_key)
    monkeypatch.setattr(readiness_module, "_configured_manifest_pointer", lambda **_kwargs: pointer)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_production_accepts_only_pinned_read_only_readiness_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    readiness_store = _write_manifest_store(tmp_path / "task2-readiness")
    pinned_values = {
        "/run/cybervpn/readiness/task2/attestation.jwt": artifact.token,
        "/run/cybervpn/readiness/task2/public-key.pem": artifact.public_key,
        "/run/cybervpn/readiness/task2/active.json": manifest_pointer_json(),
        "/run/cybervpn/readiness/task2/last-known-good.json": manifest_pointer_json(),
    }
    monkeypatch.setattr(settings, "environment", " production ")
    monkeypatch.setattr(readiness_module, "_PRODUCTION_READINESS_STORE_PATH", str(readiness_store))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_attestation_path",
        "/run/cybervpn/readiness/task2/attestation.jwt",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_public_key_path",
        "/run/cybervpn/readiness/task2/public-key.pem",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_active_pointer_path",
        "/run/cybervpn/readiness/task2/active.json",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", "")
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_lkg_pointer_path",
        "/run/cybervpn/readiness/task2/last-known-good.json",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_store_path", str(readiness_store))
    monkeypatch.setattr(
        readiness_module,
        "_read_config_file_text",
        lambda path_value, **_kwargs: pinned_values[str(path_value)],
    )

    assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True


def test_missing_promoted_manifest_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_store_path", str(tmp_path / "missing"))

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_MISSING_REASON)


def test_promoted_manifest_checksum_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    readiness_store = _write_manifest_store(
        tmp_path / "task2-readiness",
        TEST_MANIFEST_JSON.encode("utf-8") + b"\n",
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_store_path", str(readiness_store))

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_MANIFEST_MISMATCH_REASON)


def test_promoted_manifest_version_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = json.dumps(
        {"version": "c" * 64},
        separators=(",", ":"),
        sort_keys=True,
    )
    pointer = AntifilterManifestPointer(
        version=TEST_MANIFEST_VERSION,
        manifestSha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    )
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_manifest", raw)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        readiness_module._configured_promoted_manifest(pointer)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_production_rejects_manifest_pointer_outside_readiness_mount(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    pointer_path = tmp_path / "active.json"
    pointer_path.write_text(manifest_pointer_json(), encoding="utf-8")
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(readiness_module, "_configured_attestation_token", lambda: artifact.token)
    monkeypatch.setattr(readiness_module, "_configured_public_key", lambda: artifact.public_key)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer_path", str(pointer_path))

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_malformed_manifest_pointer_file_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    malformed_path = tmp_path / "active.json"
    malformed_path.write_text('{"version":"bad","manifestSha256":"bad"}', encoding="utf-8")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer_path", str(malformed_path))

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_manifest_pointer_symlink_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    target = tmp_path / "pointer-target.json"
    target.write_text(manifest_pointer_json(), encoding="utf-8")
    symlink = tmp_path / "active.json"
    try:
        symlink.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer_path", str(symlink))

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_INVALID_REASON)


def test_manifest_pointer_rotation_during_verification_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    old_pointer = AntifilterManifestPointer.model_validate_json(manifest_pointer_json())
    new_pointer = AntifilterManifestPointer.model_validate_json(
        manifest_pointer_json(version="c" * 64, manifest_sha256="c" * 64)
    )
    snapshots = iter((old_pointer, old_pointer, new_pointer, old_pointer))
    monkeypatch.setattr(
        readiness_module,
        "_configured_manifest_pointer",
        lambda **_kwargs: next(snapshots),
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_CHANGED_REASON)


def test_manifest_pointer_rotation_after_manifest_read_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    old_pointer = AntifilterManifestPointer.model_validate_json(manifest_pointer_json())
    new_pointer = AntifilterManifestPointer.model_validate_json(
        manifest_pointer_json(version="c" * 64, manifest_sha256="c" * 64)
    )
    snapshots = iter((old_pointer, old_pointer, old_pointer, old_pointer, new_pointer, new_pointer))
    monkeypatch.setattr(
        readiness_module,
        "_configured_manifest_pointer",
        lambda **_kwargs: next(snapshots),
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_STATE_CHANGED_REASON)


def test_manifest_state_rejects_unpromoted_active_pointer() -> None:
    artifact = make_spb_de_readiness_attestation()
    attestation = evaluate_spb_de_exceptions_readiness_attestation(
        attestation_token=artifact.token,
        public_key=artifact.public_key,
        expected_policy_version="premium_spb_de_exceptions.v1",
        now=CHECKED_AT,
    )
    active = AntifilterManifestPointer(
        version="c" * 64,
        manifestSha256=TEST_MANIFEST_SHA256,
    )
    lkg = AntifilterManifestPointer(
        version=TEST_MANIFEST_VERSION,
        manifestSha256=TEST_MANIFEST_SHA256,
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_manifest_state(
            attestation,
            active_pointer=active,
            lkg_pointer=lkg,
        )

    _assert_reason(exc_info, TASK2_READINESS_STATE_NOT_PROMOTED_REASON)


def test_manifest_state_rejects_stale_signed_manifest_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_active_pointer",
        manifest_pointer_json(manifest_sha256="c" * 64),
    )
    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_lkg_pointer",
        manifest_pointer_json(manifest_sha256="c" * 64),
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_MANIFEST_MISMATCH_REASON)


@pytest.mark.parametrize(
    ("active_pointer", "lkg_pointer", "expected_reason"),
    [
        ("", "", TASK2_READINESS_STATE_MISSING_REASON),
        ('{"version":"bad","manifestSha256":"bad"}', manifest_pointer_json(), TASK2_READINESS_STATE_INVALID_REASON),
        (manifest_pointer_json(), '{"version":"bad","manifestSha256":"bad"}', TASK2_READINESS_STATE_INVALID_REASON),
        (
            manifest_pointer_json(),
            manifest_pointer_json(version="c" * 64),
            TASK2_READINESS_STATE_NOT_PROMOTED_REASON,
        ),
    ],
)
def test_manifest_pointer_negative_matrix_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    active_pointer: str,
    lkg_pointer: str,
    expected_reason: str,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", active_pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", lkg_pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer_path", "")

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, expected_reason)


@pytest.mark.parametrize(
    ("payload_overrides", "expected_reason"),
    [
        ({"product_key": SMART_RU_PRODUCT_CODE}, TASK2_READINESS_ATTESTATION_MISMATCH_REASON),
        ({"schema": "cybervpn.other_schema"}, TASK2_READINESS_ATTESTATION_MISMATCH_REASON),
        ({"version": 2}, TASK2_READINESS_ATTESTATION_MISMATCH_REASON),
        ({"policy_version": "premium_spb_de_exceptions.v0"}, TASK2_READINESS_ATTESTATION_MISMATCH_REASON),
        ({"approval_status": "draft"}, TASK2_READINESS_ATTESTATION_UNAPPROVED_REASON),
        ({"revoked": True, "revocation_id": "task2-revocation-1"}, TASK2_READINESS_ATTESTATION_REVOKED_REASON),
        ({"revoked": False, "revocation_reason": "incident-hold"}, TASK2_READINESS_ATTESTATION_REVOKED_REASON),
        (
            {
                "issued_at": datetime(2099, 1, 1, tzinfo=UTC).isoformat(),
                "expires_at": datetime(2100, 1, 1, tzinfo=UTC).isoformat(),
            },
            TASK2_READINESS_ATTESTATION_FUTURE_REASON,
        ),
        ({"expires_at": datetime(2026, 1, 2, tzinfo=UTC).isoformat()}, TASK2_READINESS_ATTESTATION_STALE_REASON),
        ({"runtime_evidence_id": None, "runtime_hash": None}, TASK2_READINESS_ATTESTATION_INVALID_REASON),
        ({"attestation_id": None}, TASK2_READINESS_ATTESTATION_INVALID_REASON),
        ({"issued_at": "2026-01-01T00:00:00"}, TASK2_READINESS_ATTESTATION_INVALID_REASON),
    ],
)
def test_attestation_negative_matrix_fails_closed(
    payload_overrides: dict[str, object | None],
    expected_reason: str,
) -> None:
    artifact = make_spb_de_readiness_attestation(payload_overrides=payload_overrides)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        evaluate_spb_de_exceptions_readiness_attestation(
            attestation_token=artifact.token,
            public_key=artifact.public_key,
            expected_policy_version="premium_spb_de_exceptions.v1",
            now=CHECKED_AT,
        )

    _assert_reason(exc_info, expected_reason)


def test_bad_signature_and_unsupported_algorithm_fail_closed() -> None:
    artifact = make_spb_de_readiness_attestation()
    wrong_key = make_spb_de_readiness_attestation().public_key
    unsupported_algorithm_token = jwt.encode(artifact.payload, "test-shared-secret", algorithm="HS256")

    for token, public_key in (
        (artifact.token, wrong_key),
        (artifact.token, "not-a-public-key"),
        (unsupported_algorithm_token, artifact.public_key),
    ):
        with pytest.raises(VpnProductReadinessError) as exc_info:
            evaluate_spb_de_exceptions_readiness_attestation(
                attestation_token=token,
                public_key=public_key,
                expected_policy_version="premium_spb_de_exceptions.v1",
                now=CHECKED_AT,
            )

        _assert_reason(exc_info, TASK2_READINESS_SIGNATURE_INVALID_REASON)


def test_readiness_is_deterministic_and_does_not_cache_prior_positive_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)

    for _ in range(3):
        assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True

    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_DATA_PLANE_NOT_READY_REASON)

    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", f"{artifact.token}tampered")
    with pytest.raises(VpnProductReadinessError) as tampered_exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(tampered_exc_info, TASK2_READINESS_SIGNATURE_INVALID_REASON)


def test_configured_revocation_id_blocks_previously_valid_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = enable_spb_de_readiness(monkeypatch)
    attestation_id = str(artifact.payload["attestation_id"])

    assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True

    monkeypatch.setattr(
        settings,
        "remnawave_spb_de_exceptions_readiness_revoked_attestation_ids",
        f"other-attestation,{attestation_id.upper()}",
    )

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE)

    _assert_reason(exc_info, TASK2_READINESS_ATTESTATION_REVOKED_REASON)


def test_task2_alias_overlap_with_smart_ru_plan_codes_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    monkeypatch.setattr(settings, "remnawave_smart_ru_plan_codes", "premium_smart_ru,task2_alias")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", "task2_alias")

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_spb_de_exceptions_data_plane_ready("task2_alias")

    _assert_reason(exc_info, PRODUCT_PLAN_MISMATCH_REASON)
    assert ensure_spb_de_exceptions_data_plane_ready(SMART_RU_PRODUCT_CODE) is False


def test_gateway_product_resolution_rejects_conflicting_fields_inside_one_snapshot() -> None:
    with pytest.raises(VpnProductReadinessError) as exc_info:
        resolve_gateway_product_plan_code(
            grant_snapshot={
                "plan_code": SMART_RU_PRODUCT_CODE,
                "remnawave_routing_product": SPB_DE_EXCEPTIONS_PRODUCT_CODE,
            },
            service_context=None,
        )

    _assert_reason(exc_info, PRODUCT_PLAN_MISMATCH_REASON)


def test_smart_ru_is_not_gated_by_task2_attestation_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings, "remnawave_spb_de_exceptions_plan_codes", "premium_smart_ru,premium_spb_de_exceptions"
    )
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "")

    assert ensure_spb_de_exceptions_data_plane_ready(SMART_RU_PRODUCT_CODE) is False
    assert (
        ensure_entitlement_grant_data_plane_ready(
            grant_snapshot={"plan_code": SMART_RU_PRODUCT_CODE},
            service_context={"plan_code": SMART_RU_PRODUCT_CODE},
        )
        is False
    )


def test_product_mismatch_still_fails_before_attestation(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_spb_de_readiness(monkeypatch)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        ensure_entitlement_grant_data_plane_ready(
            grant_snapshot={"plan_code": SMART_RU_PRODUCT_CODE},
            service_context={"plan_code": SPB_DE_EXCEPTIONS_PRODUCT_CODE},
        )

    _assert_reason(exc_info, PRODUCT_PLAN_MISMATCH_REASON)
