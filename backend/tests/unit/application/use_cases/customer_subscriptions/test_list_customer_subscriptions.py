from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.customer_subscriptions.list_customer_subscriptions import (
    ListCustomerSubscriptionsUseCase,
)


class _ServiceAccess:
    def __init__(self, identity) -> None:
        self.identity = identity

    async def get_service_identity_by_id(self, _identity_id):
        return self.identity


class _Entitlements:
    def normalize_grant_snapshot(self, *, grant_snapshot, expires_at):
        return {
            **grant_snapshot,
            "expires_at": expires_at.isoformat() if expires_at is not None else None,
            "effective_entitlements": {},
            "invite_bundle": {},
            "addons": [],
        }

    @staticmethod
    def _to_utc_datetime(value):
        return value


def _use_case(identity) -> ListCustomerSubscriptionsUseCase:
    use_case = object.__new__(ListCustomerSubscriptionsUseCase)
    use_case._service_access = _ServiceAccess(identity)
    use_case._entitlements = _Entitlements()
    return use_case


def _grant(*, now: datetime):
    return SimpleNamespace(
        id=uuid4(),
        service_identity_id=uuid4(),
        grant_status="active",
        grant_snapshot={"plan_code": "premium_smart_ru", "display_name": "Smart RU"},
        expires_at=now + timedelta(days=30),
        source_type="manual",
        source_order_id=None,
        created_at=now,
    )


@pytest.mark.asyncio
async def test_active_numeric_only_service_identity_can_deliver_config() -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        subscription_key="unused",
        identity_status="active",
        provider_name="remnawave",
        provider_numeric_subject_id=4201,
        provider_subject_ref=None,
    )

    summary = await _use_case(identity)._summary_from_grant(_grant(now=now), now=now)

    assert summary.can_deliver_config is True


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_numeric_id", [None, 0, -1, True, "4201"])
async def test_legacy_only_or_inexact_service_identity_cannot_deliver_config(invalid_numeric_id) -> None:
    now = datetime(2026, 8, 31, tzinfo=UTC)
    identity = SimpleNamespace(
        id=uuid4(),
        identity_scope="subscription",
        subscription_key="unused",
        identity_status="active",
        provider_name="remnawave",
        provider_numeric_subject_id=invalid_numeric_id,
        provider_subject_ref=str(uuid4()),
    )

    summary = await _use_case(identity)._summary_from_grant(_grant(now=now), now=now)

    assert summary.can_deliver_config is False
