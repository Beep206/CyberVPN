"""Unit tests for subscription tasks."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")

from src.services.backend_api_client import (
    BackendAPIAutoRenewPermanentError,
    BackendAPIAutoRenewTransientError,
    BackendAutoRenewInvoice,
)
from src.tasks.subscriptions.auto_renew import auto_renew_subscriptions
from src.tasks.subscriptions.check_expiring import check_expiring_subscriptions
from src.tasks.subscriptions.disable_expired import disable_expired_users
from src.tasks.subscriptions.reset_traffic import reset_monthly_traffic


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task", "count_key", "reason"),
    [
        (
            check_expiring_subscriptions,
            "reminders_sent",
            "backend_remnawave_expiry_reminder_saga_required",
        ),
        (
            disable_expired_users,
            "disabled",
            "backend_remnawave_expiry_disable_saga_required",
        ),
    ],
)
async def test_legacy_subscription_jobs_are_observably_safety_disabled(task, count_key: str, reason: str) -> None:
    """Registered jobs perform zero provider mutations or notifications."""

    first = await task()
    replay = await task()

    assert first == {count_key: 0, "safety_disabled": True, "reason": reason}
    assert replay == first


@pytest.mark.asyncio
async def test_monthly_traffic_reset_is_not_applicable_under_no_reset_policy() -> None:
    """The compatibility task performs no mutation and is not safety-disabled."""

    first = await reset_monthly_traffic()
    replay = await reset_monthly_traffic()

    assert first == {
        "reset": 0,
        "not_applicable": True,
        "reason": "backend_subscription_traffic_policy_is_no_reset",
    }
    assert replay == first


def _wire_clients(mock_remnawave, backend):
    remnawave_patch = patch("src.tasks.subscriptions.auto_renew.RemnawaveClient")
    backend_patch = patch("src.tasks.subscriptions.auto_renew.BackendAPIClient")
    remnawave_cls = remnawave_patch.start()
    backend_cls = backend_patch.start()
    remnawave_cls.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
    remnawave_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    backend_cls.return_value.__aenter__ = AsyncMock(return_value=backend)
    backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return remnawave_patch, backend_patch


@pytest.mark.asyncio
async def test_auto_renew_uses_backend_owned_invoice_and_notification_receipt(mock_remnawave) -> None:
    """Provider recipient/plan fields never enter the worker delivery boundary."""

    expiry = datetime.now(UTC) + timedelta(minutes=30)
    mock_remnawave.get_users.return_value = [
        {
            "id": 41,
            "username": "provider-controlled-user",
            "telegram_id": 999999,
            "expire_at": expiry.isoformat(),
            "plan_name": "untrusted-upstream-plan",
            "plan_price": 0.01,
            "plan_currency": "XXX",
        }
    ]
    backend = AsyncMock()
    backend.filter_remnawave_auto_renew_eligible.return_value = frozenset({41})
    backend.create_remnawave_auto_renew_invoice.return_value = BackendAutoRenewInvoice(
        payment_id="550e8400-e29b-41d4-a716-446655440010",
        reused=False,
        notification_status="queued",
    )
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result == {
        "users_checked": 1,
        "invoices_created": 1,
        "invoices_reused": 0,
        "notifications_queued": 1,
        "failures": 0,
    }
    backend.filter_remnawave_auto_renew_eligible.assert_awaited_once_with([41])
    backend.create_remnawave_auto_renew_invoice.assert_awaited_once_with(
        remnawave_user_id=41,
        expected_expire_at=expiry,
    )


@pytest.mark.asyncio
async def test_auto_renew_skips_users_not_authorized_by_backend(mock_remnawave) -> None:
    expiry = datetime.now(UTC) + timedelta(minutes=30)
    mock_remnawave.get_users.return_value = [{"id": 41, "expire_at": expiry.isoformat()}]
    backend = AsyncMock()
    backend.filter_remnawave_auto_renew_eligible.return_value = frozenset()
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result["invoices_created"] == 0
    assert result["notifications_queued"] == 0
    backend.create_remnawave_auto_renew_invoice.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_renew_replay_does_not_request_another_delivery(mock_remnawave) -> None:
    expiry = datetime.now(UTC) + timedelta(minutes=30)
    mock_remnawave.get_users.return_value = [{"id": 41, "expire_at": expiry.isoformat()}]
    backend = AsyncMock()
    backend.filter_remnawave_auto_renew_eligible.return_value = frozenset({41})
    backend.create_remnawave_auto_renew_invoice.return_value = BackendAutoRenewInvoice(
        payment_id="550e8400-e29b-41d4-a716-446655440011",
        reused=True,
        notification_status="already_queued",
    )
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result["invoices_created"] == 0
    assert result["invoices_reused"] == 1
    assert result["notifications_queued"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "backend_error",
    [
        BackendAPIAutoRenewPermanentError("rejected"),
        BackendAPIAutoRenewTransientError("retry"),
    ],
)
async def test_auto_renew_records_backend_failure_without_worker_notification(
    mock_remnawave,
    backend_error: Exception,
) -> None:
    expiry = datetime.now(UTC) + timedelta(minutes=30)
    mock_remnawave.get_users.return_value = [{"id": 41, "expire_at": expiry.isoformat()}]
    backend = AsyncMock()
    backend.filter_remnawave_auto_renew_eligible.return_value = frozenset({41})
    backend.create_remnawave_auto_renew_invoice.side_effect = backend_error
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result["failures"] == 1
    assert result["notifications_queued"] == 0


@pytest.mark.asyncio
async def test_auto_renew_rejects_indefinitely_expired_candidates_before_backend(mock_remnawave) -> None:
    expiry = datetime.now(UTC) - timedelta(hours=2, seconds=1)
    mock_remnawave.get_users.return_value = [{"id": 41, "expire_at": expiry.isoformat()}]
    backend = AsyncMock()
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result["users_checked"] == 1
    backend.filter_remnawave_auto_renew_eligible.assert_not_awaited()
    backend.create_remnawave_auto_renew_invoice.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_renew_batches_backend_eligibility_at_contract_limit(mock_remnawave) -> None:
    expiry = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
    mock_remnawave.get_users.return_value = [{"id": user_id, "expire_at": expiry} for user_id in range(1, 1002)]
    backend = AsyncMock()
    backend.filter_remnawave_auto_renew_eligible.side_effect = [frozenset(), frozenset()]
    patches = _wire_clients(mock_remnawave, backend)
    try:
        result = await auto_renew_subscriptions()
    finally:
        for active_patch in patches:
            active_patch.stop()

    assert result["users_checked"] == 1001
    assert [len(call.args[0]) for call in backend.filter_remnawave_auto_renew_eligible.await_args_list] == [1000, 1]
    backend.create_remnawave_auto_renew_invoice.assert_not_awaited()
