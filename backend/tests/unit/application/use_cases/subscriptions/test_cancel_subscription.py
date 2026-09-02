from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.subscriptions.cancel_subscription import (
    CancelSubscriptionUseCase,
    SubscriptionCancellationIdentityConflictError,
    SubscriptionCancellationNotFoundError,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_subscription_mutates_only_exact_numeric_identity() -> None:
    revoked_at = datetime(2026, 8, 30, 10, 0, tzinfo=UTC)
    user_gateway = AsyncMock()
    subscription_client = AsyncMock()
    user_gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=42, sub_revoked_at=None)
    user_gateway.revoke_subscription.return_value = SimpleNamespace(
        remnawave_id=42,
        sub_revoked_at=revoked_at,
    )
    user_ref = RemnawaveUserRef(id=42)

    result = await CancelSubscriptionUseCase(user_gateway, subscription_client).execute(user_ref)

    assert result == revoked_at
    user_gateway.get_by_ref.assert_awaited_once_with(user_ref)
    user_gateway.revoke_subscription.assert_awaited_once_with(user_ref)
    subscription_client.invalidate.assert_awaited_once_with(user_ref)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_subscription_is_idempotent_when_already_revoked() -> None:
    revoked_at = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    user_gateway = AsyncMock()
    subscription_client = AsyncMock()
    user_gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=42, sub_revoked_at=revoked_at)
    user_ref = RemnawaveUserRef(id=42)
    use_case = CancelSubscriptionUseCase(user_gateway, subscription_client)

    first = await use_case.execute(user_ref)
    second = await use_case.execute(user_ref)

    assert first == second == revoked_at
    assert user_gateway.get_by_ref.await_count == 2
    user_gateway.revoke_subscription.assert_not_awaited()
    assert subscription_client.invalidate.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_subscription_rejects_upstream_identity_mismatch_without_mutation() -> None:
    user_gateway = AsyncMock()
    subscription_client = AsyncMock()
    user_gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=99, sub_revoked_at=None)

    with pytest.raises(SubscriptionCancellationIdentityConflictError):
        await CancelSubscriptionUseCase(user_gateway, subscription_client).execute(RemnawaveUserRef(id=42))

    user_gateway.revoke_subscription.assert_not_awaited()
    subscription_client.invalidate.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_subscription_reports_missing_reconciled_user() -> None:
    user_gateway = AsyncMock()
    subscription_client = AsyncMock()
    user_gateway.get_by_ref.return_value = None

    with pytest.raises(SubscriptionCancellationNotFoundError):
        await CancelSubscriptionUseCase(user_gateway, subscription_client).execute(RemnawaveUserRef(id=42))

    user_gateway.revoke_subscription.assert_not_awaited()
    subscription_client.invalidate.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_subscription_never_fabricates_revocation_time() -> None:
    user_gateway = AsyncMock()
    subscription_client = AsyncMock()
    user_gateway.get_by_ref.return_value = SimpleNamespace(remnawave_id=42, sub_revoked_at=None)
    user_gateway.revoke_subscription.return_value = SimpleNamespace(
        remnawave_id=42,
        sub_revoked_at=None,
    )

    with pytest.raises(SubscriptionCancellationIdentityConflictError, match="not confirmed"):
        await CancelSubscriptionUseCase(user_gateway, subscription_client).execute(RemnawaveUserRef(id=42))

    subscription_client.invalidate.assert_not_awaited()
