from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import src.application.use_cases.payments.post_payment as post_payment_module
from src.application.services.vpn_product_readiness import (
    PRODUCT_PLAN_MISMATCH_REASON,
    TASK2_DATA_PLANE_NOT_READY_REASON,
    VpnProductReadinessError,
)
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.config.settings import settings
from tests.helpers.spb_de_readiness import enable_spb_de_readiness

OVERLAPPING_PLAN_CODES = "premium_smart_ru,premium_spb_de_exceptions"


class _SelectedSubscriptionRepo:
    def __init__(self, session: SimpleNamespace) -> None:
        self._session = session

    async def get_entitlement_grant_by_id(self, grant_id):
        assert grant_id == self._session.grant.id
        return self._session.grant

    async def get_service_identity_by_id(self, service_identity_id):
        assert service_identity_id == self._session.service_identity.id
        return self._session.service_identity


def _use_case(monkeypatch: pytest.MonkeyPatch, *, grant: SimpleNamespace, service_identity: SimpleNamespace):
    monkeypatch.setattr(post_payment_module, "ServiceAccessRepository", _SelectedSubscriptionRepo)
    session = SimpleNamespace(flush=AsyncMock(), grant=grant, service_identity=service_identity)
    use_case = PostPaymentProcessingUseCase.__new__(PostPaymentProcessingUseCase)
    use_case._session = session
    return use_case, session


def _grant(*, customer_id, plan_code: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        service_identity_id=uuid4(),
        customer_account_id=customer_id,
        grant_snapshot={"plan_code": plan_code},
        expires_at=None,
        grant_status="pending",
        source_snapshot={"existing": "kept"},
    )


def _payment(*, customer_id, grant_id, plan_code: str, subscription_days: int = 30) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        user_uuid=customer_id,
        entitlements_snapshot={"plan_code": plan_code},
        subscription_days=subscription_days,
        created_at=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        metadata_={
            "checkout_mode": "selected_subscription_upgrade",
            "target_subscription_key": f"grant:{grant_id}",
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_plan_code", "incoming_plan_code", "identity_plan_code", "expected_reason"),
    [
        (
            "premium_spb_de_exceptions",
            "premium_spb_de_exceptions",
            "premium_spb_de_exceptions",
            TASK2_DATA_PLANE_NOT_READY_REASON,
        ),
        (
            "premium_smart_ru",
            "premium_spb_de_exceptions",
            "premium_smart_ru",
            PRODUCT_PLAN_MISMATCH_REASON,
        ),
        (
            "premium_smart_ru",
            "premium_smart_ru",
            "premium_spb_de_exceptions",
            PRODUCT_PLAN_MISMATCH_REASON,
        ),
    ],
)
async def test_selected_subscription_task2_write_fails_before_grant_mutation_and_flush_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
    existing_plan_code: str,
    incoming_plan_code: str,
    identity_plan_code: str,
    expected_reason: str,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    customer_id = uuid4()
    grant = _grant(customer_id=customer_id, plan_code=existing_plan_code)
    service_identity = SimpleNamespace(id=grant.service_identity_id, service_context={"plan_code": identity_plan_code})
    payment = _payment(customer_id=customer_id, grant_id=grant.id, plan_code=incoming_plan_code)
    original_snapshot = dict(grant.grant_snapshot)
    original_source_snapshot = dict(grant.source_snapshot)
    use_case, session = _use_case(monkeypatch, grant=grant, service_identity=service_identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case._apply_selected_subscription_write(
            payment=payment,
            checkout_mode="selected_subscription_upgrade",
            target_subscription_key=f"grant:{grant.id}",
        )

    assert exc_info.value.reason == expected_reason
    assert grant.grant_snapshot == original_snapshot
    assert grant.expires_at is None
    assert grant.grant_status == "pending"
    assert grant.source_snapshot == original_source_snapshot
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_task2_write_preserves_behavior_when_readiness_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    customer_id = uuid4()
    grant = _grant(customer_id=customer_id, plan_code="premium_spb_de_exceptions")
    service_identity = SimpleNamespace(
        id=grant.service_identity_id,
        service_context={"plan_code": "premium_spb_de_exceptions"},
    )
    payment = _payment(customer_id=customer_id, grant_id=grant.id, plan_code="premium_spb_de_exceptions")
    use_case, session = _use_case(monkeypatch, grant=grant, service_identity=service_identity)

    result = await use_case._apply_selected_subscription_write(
        payment=payment,
        checkout_mode="selected_subscription_upgrade",
        target_subscription_key=f"grant:{grant.id}",
    )

    assert result == {"selected_subscription_updated": True}
    assert grant.grant_snapshot == {"plan_code": "premium_spb_de_exceptions"}
    assert grant.expires_at == payment.created_at + timedelta(days=30)
    assert grant.grant_status == "active"
    assert grant.source_snapshot["existing"] == "kept"
    assert grant.source_snapshot["selected_subscription_events"][0]["payment_id"] == str(payment.id)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_selected_subscription_rejects_cross_product_write_when_readiness_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enable_spb_de_readiness(monkeypatch)
    customer_id = uuid4()
    grant = _grant(customer_id=customer_id, plan_code="premium_smart_ru")
    service_identity = SimpleNamespace(id=grant.service_identity_id, service_context={"plan_code": "premium_smart_ru"})
    payment = _payment(customer_id=customer_id, grant_id=grant.id, plan_code="premium_spb_de_exceptions")
    original_snapshot = dict(grant.grant_snapshot)
    use_case, session = _use_case(monkeypatch, grant=grant, service_identity=service_identity)

    with pytest.raises(VpnProductReadinessError) as exc_info:
        await use_case._apply_selected_subscription_write(
            payment=payment,
            checkout_mode="selected_subscription_upgrade",
            target_subscription_key=f"grant:{grant.id}",
        )

    assert exc_info.value.reason == PRODUCT_PLAN_MISMATCH_REASON
    assert grant.grant_snapshot == original_snapshot
    assert grant.grant_status == "pending"
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_selected_subscription_smart_ru_write_is_unaffected_by_task2_overlap_when_readiness_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_plan_codes", OVERLAPPING_PLAN_CODES)
    monkeypatch.setattr(settings, "remnawave_spb_de_exceptions_data_plane_ready", False)
    customer_id = uuid4()
    grant = _grant(customer_id=customer_id, plan_code="premium_smart_ru")
    service_identity = SimpleNamespace(id=grant.service_identity_id, service_context={"plan_code": "premium_smart_ru"})
    payment = _payment(customer_id=customer_id, grant_id=grant.id, plan_code="premium_smart_ru")
    use_case, session = _use_case(monkeypatch, grant=grant, service_identity=service_identity)

    result = await use_case._apply_selected_subscription_write(
        payment=payment,
        checkout_mode="selected_subscription_addons",
        target_subscription_key=f"grant:{grant.id}",
    )

    assert result == {"selected_subscription_updated": True}
    assert grant.grant_snapshot == {"plan_code": "premium_smart_ru"}
    assert grant.grant_status == "active"
    session.flush.assert_awaited_once()
