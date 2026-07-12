from __future__ import annotations

from datetime import UTC, datetime

import jwt
import pytest

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
    TASK2_READINESS_PUBLIC_KEY_MISSING_REASON,
    TASK2_READINESS_SIGNATURE_INVALID_REASON,
    VpnProductReadinessError,
    ensure_entitlement_grant_data_plane_ready,
    ensure_spb_de_exceptions_data_plane_ready,
    evaluate_spb_de_exceptions_readiness_attestation,
    resolve_gateway_product_plan_code,
)
from src.config.settings import settings
from tests.helpers.spb_de_readiness import enable_spb_de_readiness, make_spb_de_readiness_attestation

CHECKED_AT = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)


def _configure_direct_readiness(monkeypatch: pytest.MonkeyPatch, *, token: str, public_key: str) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", token)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", public_key)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", "")


def _assert_reason(exc_info: pytest.ExceptionInfo[VpnProductReadinessError], reason: str) -> None:
    assert exc_info.value.reason == reason


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
    assert attestation.manifest_hash == "sha256:manifest-ready"
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
    attestation_path.write_text(artifact.token, encoding="utf-8")
    public_key_path.write_text(artifact.public_key, encoding="utf-8")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", str(attestation_path))
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_public_key_path", str(public_key_path))

    assert ensure_spb_de_exceptions_data_plane_ready(SPB_DE_EXCEPTIONS_PRODUCT_CODE) is True


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
