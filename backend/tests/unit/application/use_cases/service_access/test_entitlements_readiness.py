from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.vpn_product_readiness import (
    PRODUCT_PLAN_MISMATCH_REASON,
    TASK2_DATA_PLANE_NOT_READY_REASON,
    TASK2_READINESS_ATTESTATION_MISSING_REASON,
    TASK2_READINESS_MANIFEST_MISMATCH_REASON,
    VpnProductReadinessError,
)
from src.application.use_cases.service_access.entitlements import (
    ActivateEntitlementGrantUseCase,
    CreateEntitlementGrantUseCase,
)
from src.config.settings import settings
from tests.helpers.spb_de_readiness import enable_spb_de_readiness, manifest_pointer_json

OVERLAPPING_PLAN_CODES = "premium_smart_ru,premium_spb_de_exceptions"


def _identity(plan_code: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        customer_account_id=uuid4(),
        auth_realm_id=uuid4(),
        origin_storefront_id=uuid4(),
        service_context={"plan_code": plan_code},
    )


def _grant(identity: SimpleNamespace, *, status: str, plan_code: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        service_identity_id=identity.id,
        customer_account_id=identity.customer_account_id,
        auth_realm_id=identity.auth_realm_id,
        source_type="manual",
        source_order_id=None,
        source_renewal_order_id=None,
        source_growth_reward_allocation_id=None,
        grant_status=status,
        grant_snapshot={"plan_code": plan_code},
        effective_from=None,
        activated_at=None,
        activated_by_admin_user_id=None,
        suspended_at="unchanged",
        suspended_by_admin_user_id="unchanged",
        suspension_reason_code="unchanged",
    )


def _create_use_case(
    identity: SimpleNamespace,
    *,
    existing_manual_grant: SimpleNamespace | None = None,
) -> tuple[CreateEntitlementGrantUseCase, SimpleNamespace]:
    use_case = CreateEntitlementGrantUseCase(SimpleNamespace())
    repo = SimpleNamespace(
        get_service_identity_by_id=AsyncMock(return_value=identity),
        get_entitlement_grant_by_source_order_id=AsyncMock(return_value=None),
        get_entitlement_grant_by_source_growth_reward_allocation_id=AsyncMock(return_value=None),
        get_entitlement_grant_by_source_renewal_order_id=AsyncMock(return_value=None),
        get_entitlement_grant_by_manual_source_key=AsyncMock(return_value=existing_manual_grant),
        create_entitlement_grant=AsyncMock(side_effect=lambda model: model),
    )
    use_case._repo = repo
    return use_case, repo


def _activate_use_case(
    grant: SimpleNamespace,
    identity: SimpleNamespace,
) -> tuple[ActivateEntitlementGrantUseCase, SimpleNamespace]:
    session = SimpleNamespace(flush=AsyncMock())
    use_case = ActivateEntitlementGrantUseCase(session)
    repo = SimpleNamespace(
        get_entitlement_grant_by_id=AsyncMock(return_value=grant),
        get_service_identity_by_id=AsyncMock(return_value=identity),
    )
    use_case._repo = repo
    use_case._outbox = SimpleNamespace(append_event=AsyncMock())
    return use_case, session


@pytest.mark.asyncio
async def test_create_task2_grant_fails_before_persistence_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_spb_de_exceptions")
    use_case, repo = _create_use_case(identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-task2",
            grant_snapshot={"plan_code": "premium_spb_de_exceptions"},
        )

    assert exc_info.value.reason == TASK2_DATA_PLANE_NOT_READY_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task2_grant_fails_before_persistence_when_attestation_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", True)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation", "")
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_attestation_path", "")
    identity = _identity("premium_spb_de_exceptions")
    use_case, repo = _create_use_case(identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-task2-no-attestation",
            grant_snapshot={"plan_code": "premium_spb_de_exceptions"},
        )

    assert exc_info.value.reason == TASK2_READINESS_ATTESTATION_MISSING_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task2_grant_fails_before_persistence_when_manifest_is_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    stale_pointer = manifest_pointer_json(manifest_sha256="c" * 64)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_active_pointer", stale_pointer)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_readiness_lkg_pointer", stale_pointer)
    identity = _identity("premium_spb_de_exceptions")
    use_case, repo = _create_use_case(identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-task2-stale-manifest",
            grant_snapshot={"plan_code": "premium_spb_de_exceptions"},
        )

    assert exc_info.value.reason == TASK2_READINESS_MANIFEST_MISMATCH_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task2_grant_replay_fails_closed_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("")
    identity.service_context = {}
    existing = _grant(identity, status="pending", plan_code="premium_spb_de_exceptions")
    use_case, repo = _create_use_case(identity, existing_manual_grant=existing)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-task2-replay",
        )

    assert exc_info.value.reason == TASK2_DATA_PLANE_NOT_READY_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_sparse_task2_grant_replay_uses_service_context_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_spb_de_exceptions")
    existing = _grant(identity, status="pending", plan_code="")
    existing.grant_snapshot = {}
    use_case, repo = _create_use_case(identity, existing_manual_grant=existing)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-sparse-task2-replay",
        )

    assert exc_info.value.reason == TASK2_DATA_PLANE_NOT_READY_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_task2_replay_candidate_against_smart_ru_existing_grant_rejects_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    existing = _grant(identity, status="pending", plan_code="premium_smart_ru")
    use_case, repo = _create_use_case(identity, existing_manual_grant=existing)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-smart-task2-drift",
            grant_snapshot={"plan_code": "premium_spb_de_exceptions"},
        )

    assert exc_info.value.reason == PRODUCT_PLAN_MISMATCH_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_smart_ru_grant_replay_keeps_idempotency_when_task2_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    existing = _grant(identity, status="pending", plan_code="premium_smart_ru")
    use_case, repo = _create_use_case(identity, existing_manual_grant=existing)

    result = await use_case.execute(
        service_identity_id=identity.id,
        manual_source_key="manual-smart-replay",
        grant_snapshot={"plan_code": "premium_smart_ru"},
    )

    assert result.created is False
    assert result.entitlement_grant is existing
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_legacy_non_task2_grant_replay_keeps_idempotency_with_metadata_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("legacy-plan")
    existing = _grant(identity, status="pending", plan_code="legacy-plan")
    existing.grant_snapshot = {"plan_code": "legacy-plan", "remnawave_routing_product": "legacy-route"}
    use_case, repo = _create_use_case(identity, existing_manual_grant=existing)

    result = await use_case.execute(
        service_identity_id=identity.id,
        manual_source_key="manual-legacy-replay",
        grant_snapshot={"plan_code": "legacy-candidate"},
    )

    assert result.created is False
    assert result.entitlement_grant is existing
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_smart_ru_grant_is_unaffected_by_task2_overlap_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    use_case, repo = _create_use_case(identity)

    result = await use_case.execute(
        service_identity_id=identity.id,
        manual_source_key="manual-smart",
        grant_snapshot={"plan_code": "premium_smart_ru"},
    )

    assert result.created is True
    assert result.entitlement_grant.grant_status == "pending"
    assert result.entitlement_grant.grant_snapshot == {"plan_code": "premium_smart_ru"}
    repo.create_entitlement_grant.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_grant_rejects_product_mismatch_before_persistence_when_readiness_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_smart_ru")
    use_case, repo = _create_use_case(identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(
            service_identity_id=identity.id,
            manual_source_key="manual-mismatch",
            grant_snapshot={"plan_code": "premium_spb_de_exceptions"},
        )

    assert exc_info.value.reason == PRODUCT_PLAN_MISMATCH_REASON
    repo.create_entitlement_grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_task2_grant_fails_before_status_outbox_and_flush_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_spb_de_exceptions")
    grant = _grant(identity, status="pending", plan_code="premium_spb_de_exceptions")
    use_case, session = _activate_use_case(grant, identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(entitlement_grant_id=grant.id, activated_by_admin_user_id=uuid4())

    assert exc_info.value.reason == TASK2_DATA_PLANE_NOT_READY_REASON
    assert grant.grant_status == "pending"
    assert grant.effective_from is None
    assert grant.activated_at is None
    use_case._outbox.append_event.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_task2_grant_preserves_behavior_when_readiness_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_spb_de_exceptions")
    grant = _grant(identity, status="pending", plan_code="premium_spb_de_exceptions")
    use_case, session = _activate_use_case(grant, identity)

    result = await use_case.execute(entitlement_grant_id=grant.id, activated_by_admin_user_id=None)

    assert result is grant
    assert grant.grant_status == "active"
    assert grant.effective_from is not None
    assert grant.activated_at is not None
    use_case._outbox.append_event.assert_awaited_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_grant_rejects_product_mismatch_when_readiness_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    identity = _identity("premium_smart_ru")
    grant = _grant(identity, status="pending", plan_code="premium_spb_de_exceptions")
    use_case, session = _activate_use_case(grant, identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case.execute(entitlement_grant_id=grant.id, activated_by_admin_user_id=None)

    assert exc_info.value.reason == PRODUCT_PLAN_MISMATCH_REASON
    assert grant.grant_status == "pending"
    use_case._outbox.append_event.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_activate_smart_ru_grant_is_unaffected_by_task2_overlap_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    identity = _identity("premium_smart_ru")
    grant = _grant(identity, status="pending", plan_code="premium_smart_ru")
    use_case, session = _activate_use_case(grant, identity)

    result = await use_case.execute(entitlement_grant_id=grant.id, activated_by_admin_user_id=uuid4())

    assert result is grant
    assert grant.grant_status == "active"
    use_case._outbox.append_event.assert_awaited_once()
    session.flush.assert_awaited_once()
