"""Unit tests for payment tasks."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Set required environment variables before importing modules
os.environ.setdefault("REMNAWAVE_API_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test-bot")
os.environ.setdefault("CRYPTOBOT_TOKEN", "test-crypto")
os.environ.setdefault("METRICS_PROTECT", "false")

from src.tasks.payments.process_completion import process_payment_completion
from src.tasks.payments.provisioning_retries import process_stage1_provisioning_retries
from src.tasks.payments.reconcile_stage1 import reconcile_stage1_payments
from src.tasks.payments.reconcile_telegram_stars import reconcile_telegram_stars_refunds
from src.tasks.payments.retry_webhooks import retry_failed_webhooks
from src.tasks.payments.verify_pending import verify_pending_payments


def _scalar_result(value: int) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _metric_value(metric, **labels) -> float:
    return metric.labels(**labels)._value.get()


@pytest.mark.asyncio
async def test_verify_pending_checks_invoices(
    mock_db_session, mock_cryptobot, mock_remnawave, mock_telegram, mock_redis
):
    """Test verify pending checks invoices via CryptoBot API."""
    payment1 = MagicMock()
    payment1.id = uuid4()
    payment1.external_id = "123"
    payment1.status = "pending"
    payment1.provider = "cryptobot"
    payment1.created_at = datetime.now(UTC)

    payment2 = MagicMock()
    payment2.id = uuid4()
    payment2.external_id = "456"
    payment2.status = "pending"
    payment2.provider = "cryptobot"
    payment2.created_at = datetime.now(UTC)

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [payment1, payment2]
    mock_db_session.execute = AsyncMock(side_effect=[pending_result, _scalar_result(2), _scalar_result(0)])

    mock_cryptobot.get_invoices.return_value = [
        {"invoice_id": 123, "status": "active"},
        {"invoice_id": 456, "status": "active"},
    ]

    with (
        patch("src.tasks.payments.verify_pending.get_session_factory") as mock_factory,
        patch("src.tasks.payments.verify_pending.CryptoBotClient") as mock_cb,
        patch("src.tasks.payments.verify_pending.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.verify_pending.TelegramClient") as mock_tg,
        patch("src.tasks.payments.verify_pending.get_redis_client") as mock_redis_fn,
        patch("src.tasks.payments.verify_pending.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_cb.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis_fn.return_value = mock_redis

        mock_task.kiq = AsyncMock()

        result = await verify_pending_payments()

        assert result["checked"] == 2
        mock_cryptobot.get_invoices.assert_called_once_with(invoice_ids=[123, 456])


@pytest.mark.asyncio
async def test_verify_pending_triggers_completion(
    mock_db_session, mock_cryptobot, mock_remnawave, mock_telegram, mock_redis
):
    """Test verify pending triggers completion for paid invoices."""
    payment = MagicMock()
    payment.id = uuid4()
    payment.external_id = "123"
    payment.status = "pending"
    payment.provider = "cryptobot"
    payment.user_uuid = "user-123"
    payment.created_at = datetime.now(UTC)

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [payment]
    mock_db_session.execute = AsyncMock(side_effect=[pending_result, _scalar_result(1), _scalar_result(0)])

    mock_cryptobot.get_invoices.return_value = [
        {"invoice_id": 123, "status": "paid"},
    ]

    with (
        patch("src.tasks.payments.verify_pending.get_session_factory") as mock_factory,
        patch("src.tasks.payments.verify_pending.CryptoBotClient") as mock_cb,
        patch("src.tasks.payments.verify_pending.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.verify_pending.TelegramClient") as mock_tg,
        patch("src.tasks.payments.verify_pending.get_redis_client") as mock_redis_fn,
        patch("src.tasks.payments.verify_pending.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_cb.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis_fn.return_value = mock_redis

        mock_task.kiq = AsyncMock()

        result = await verify_pending_payments()

        assert result["checked"] == 1
        assert result["completed"] == 1
        mock_task.kiq.assert_called_once_with(payment_id=str(payment.id))


@pytest.mark.asyncio
async def test_verify_pending_updates_cancelled_invoices(
    mock_db_session, mock_cryptobot, mock_remnawave, mock_telegram, mock_redis
):
    """Test verify pending updates status for cancelled/expired invoices."""
    payment = MagicMock()
    payment.id = uuid4()
    payment.external_id = "123"
    payment.status = "pending"
    payment.provider = "cryptobot"
    payment.created_at = datetime.now(UTC)

    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = [payment]
    mock_db_session.execute = AsyncMock(side_effect=[pending_result, _scalar_result(1), _scalar_result(1)])

    mock_cryptobot.get_invoices.return_value = [
        {"invoice_id": 123, "status": "expired"},
    ]

    mock_remnawave.get_user.return_value = {"uuid": "user-123", "telegram_id": 555, "username": "tester"}

    with (
        patch("src.tasks.payments.verify_pending.get_session_factory") as mock_factory,
        patch("src.tasks.payments.verify_pending.CryptoBotClient") as mock_cb,
        patch("src.tasks.payments.verify_pending.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.verify_pending.TelegramClient") as mock_tg,
        patch("src.tasks.payments.verify_pending.get_redis_client") as mock_redis_fn,
        patch("src.tasks.payments.verify_pending.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_cb.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis_fn.return_value = mock_redis

        mock_task.kiq = AsyncMock()

        result = await verify_pending_payments()

        assert result["completed"] == 0
        assert result["expired"] == 1
        assert payment.status == "expired"
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_verify_pending_empty_queue(mock_db_session, mock_cryptobot, mock_remnawave, mock_telegram, mock_redis):
    """Test verify pending with no pending payments."""
    pending_result = MagicMock()
    pending_result.scalars.return_value.all.return_value = []
    mock_db_session.execute = AsyncMock(side_effect=[pending_result, _scalar_result(0), _scalar_result(0)])

    with (
        patch("src.tasks.payments.verify_pending.get_session_factory") as mock_factory,
        patch("src.tasks.payments.verify_pending.CryptoBotClient") as mock_cb,
        patch("src.tasks.payments.verify_pending.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.verify_pending.TelegramClient") as mock_tg,
        patch("src.tasks.payments.verify_pending.get_redis_client") as mock_redis_fn,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_cb.return_value.__aenter__ = AsyncMock(return_value=mock_cryptobot)
        mock_cb.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_redis_fn.return_value = mock_redis

        result = await verify_pending_payments()

        assert result["checked"] == 0
        assert result["completed"] == 0
        assert result["expired"] == 0
        mock_cryptobot.get_invoices.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_telegram_stars_refunds_syncs_provider_state(mock_settings, mock_telegram):
    """Test Telegram Stars reconciliation forwards outgoing refund transactions to backend."""
    mock_telegram.get_star_transactions.return_value = {
        "transactions": [
            {
                "id": "tg-charge-1",
                "amount": 250,
                "date": 1713780000,
                "receiver": {
                    "type": "user",
                    "transaction_type": "invoice_payment",
                    "invoice_payload": "stars:payment:user",
                    "user": {"id": 555},
                },
            }
        ]
    }
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.reconcile_telegram_stars_refund = AsyncMock(return_value={"action": "created_and_reconciled"})

    with (
        patch("src.tasks.payments.reconcile_telegram_stars.get_settings", return_value=mock_settings),
        patch("src.tasks.payments.reconcile_telegram_stars.TelegramClient") as mock_tg,
        patch("src.tasks.payments.reconcile_telegram_stars.BackendAPIClient") as mock_backend_cls,
    ):
        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await reconcile_telegram_stars_refunds()

        mock_telegram.get_star_transactions.assert_awaited_once()
        mock_backend.reconcile_telegram_stars_refund.assert_awaited_once()
        assert result["checked"] == 1
        assert result["actions"] == {"created_and_reconciled": 1}


@pytest.mark.asyncio
async def test_reconcile_telegram_stars_refunds_skips_without_backend_config(mock_settings):
    """Test Telegram Stars reconciliation is skipped when backend hook is not configured."""
    mock_settings.backend_api_url = None
    mock_settings.backend_internal_secret = None

    with patch("src.tasks.payments.reconcile_telegram_stars.get_settings", return_value=mock_settings):
        result = await reconcile_telegram_stars_refunds()

    assert result["skipped"] is True
    assert result["reason"] == "backend_api_not_configured"


@pytest.mark.asyncio
async def test_reconcile_stage1_payments_calls_internal_backend_job(mock_settings):
    """Test S1 payment reconciliation asks backend for a safe mismatch report."""
    from src.metrics import (
        STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT,
        STAGE1_PAYMENT_RECONCILIATION_LAUNCH_BLOCKED,
        STAGE1_PAYMENT_RECONCILIATION_MAX_AGE_MINUTES,
        STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL,
    )

    before_success_runs = _metric_value(
        STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL,
        result="success",
    )
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.run_stage1_payment_reconciliation = AsyncMock(
        return_value={
            "report_version": "stage1-payment-reconciliation-v1",
            "generated_at": "2026-05-05T12:00:00+00:00",
            "summary": {
                "total_items": 2,
                "manual_review_items": 2,
                "alert_15m_items": 1,
                "p1_escalation_items": 0,
                "p0_blocker_items": 0,
                "max_age_minutes": 70,
                "launch_blocked": False,
                "mismatch_counts": {"stale_active_attempt": 2},
            },
            "items": [{"safe_reference": "s1:payment-reconciliation:test"}],
        }
    )

    with (
        patch("src.tasks.payments.reconcile_stage1.get_settings", return_value=mock_settings),
        patch("src.tasks.payments.reconcile_stage1.BackendAPIClient") as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await reconcile_stage1_payments()

    assert result["report_version"] == "stage1-payment-reconciliation-v1"
    assert result["summary"]["total_items"] == 2
    assert result["items_count"] == 1
    mock_backend.run_stage1_payment_reconciliation.assert_awaited_once_with({"limit": 250})
    assert _metric_value(STAGE1_PAYMENT_RECONCILIATION_RUNS_TOTAL, result="success") == before_success_runs + 1
    assert _metric_value(STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT, severity="manual_review") == 2
    assert _metric_value(STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT, severity="alert_15m") == 1
    assert _metric_value(STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT, severity="p1_escalation") == 0
    assert _metric_value(STAGE1_PAYMENT_RECONCILIATION_ITEMS_CURRENT, severity="p0_blocker") == 0
    assert STAGE1_PAYMENT_RECONCILIATION_MAX_AGE_MINUTES._value.get() == 70
    assert STAGE1_PAYMENT_RECONCILIATION_LAUNCH_BLOCKED._value.get() == 0


@pytest.mark.asyncio
async def test_reconcile_stage1_payments_skips_without_backend_config(mock_settings):
    """Test S1 payment reconciliation is skipped when backend hook is not configured."""
    mock_settings.backend_api_url = None
    mock_settings.backend_internal_secret = None

    with patch("src.tasks.payments.reconcile_stage1.get_settings", return_value=mock_settings):
        result = await reconcile_stage1_payments()

    assert result["skipped"] is True
    assert result["reason"] == "backend_api_not_configured"


@pytest.mark.asyncio
async def test_stage1_provisioning_retry_worker_skips_when_claiming_disabled(mock_settings):
    """Test provisioning retry worker is disabled by default before Security review."""
    mock_settings.stage1_provisioning_retry_claiming_enabled = False

    with patch("src.tasks.payments.provisioning_retries.get_settings", return_value=mock_settings):
        result = await process_stage1_provisioning_retries()

    assert result == {"skipped": True, "reason": "claiming_disabled"}


@pytest.mark.asyncio
async def test_stage1_provisioning_retry_worker_calls_backend_and_updates_metrics(mock_settings):
    """Test provisioning retry worker calls the internal backend runner."""
    from src.metrics import (
        STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL,
        STAGE1_PROVISIONING_RETRY_JOBS_CURRENT,
        STAGE1_PROVISIONING_RETRY_REMNAWAVE_ERRORS_TOTAL,
    )

    mock_settings.stage1_provisioning_retry_claiming_enabled = True
    mock_settings.stage1_provisioning_retry_batch_limit = 7
    report = {
        "claimed": 2,
        "succeeded": 1,
        "retrying": 1,
        "dead_letter": 0,
        "reconciliation_required": 0,
        "skipped": False,
        "remnawave_dependency_errors": {"ConnectionError": 1},
        "metrics": {
            "counts_by_state": {"queued": 3, "retrying": 1, "dead_letter": 0, "succeeded": 1},
            "max_job_age_seconds": 120,
        },
    }

    before_claims = _metric_value(STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL, result="claimed")
    before_errors = _metric_value(STAGE1_PROVISIONING_RETRY_REMNAWAVE_ERRORS_TOTAL, error_type="ConnectionError")
    with (
        patch("src.tasks.payments.provisioning_retries.get_settings", return_value=mock_settings),
        patch("src.tasks.payments.provisioning_retries.BackendAPIClient") as mock_backend_cls,
    ):
        backend = AsyncMock()
        backend.enabled = True
        backend.run_stage1_provisioning_retries.return_value = report
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_stage1_provisioning_retries()

    assert result == report
    backend.run_stage1_provisioning_retries.assert_awaited_once()
    payload = backend.run_stage1_provisioning_retries.await_args.args[0]
    assert payload["limit"] == 7
    assert payload["worker_id"].endswith(":task-worker")
    assert _metric_value(STAGE1_PROVISIONING_RETRY_CLAIMS_TOTAL, result="claimed") == before_claims + 1
    assert _metric_value(STAGE1_PROVISIONING_RETRY_REMNAWAVE_ERRORS_TOTAL, error_type="ConnectionError") == (
        before_errors + 1
    )
    assert _metric_value(STAGE1_PROVISIONING_RETRY_JOBS_CURRENT, state="queued") == 3


@pytest.mark.asyncio
async def test_process_completion_activates_user(mock_db_session, mock_remnawave, mock_telegram):
    """Test process completion enables user and sends notification."""
    payment_id = str(uuid4())
    user_uuid = "user-123"

    payment = MagicMock()
    payment.id = payment_id
    payment.status = "pending"
    payment.user_uuid = user_uuid
    payment.amount = 10.0
    payment.currency = "USD"
    payment.subscription_days = 30

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_remnawave.get_user.return_value = {
        "uuid": user_uuid,
        "username": "testuser",
        "telegram_id": 12345,
    }
    mock_remnawave.bulk_extend_expiration_date = AsyncMock()

    with (
        patch("src.tasks.payments.process_completion.get_session_factory") as mock_factory,
        patch("src.tasks.payments.process_completion.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.process_completion.TelegramClient") as mock_tg,
        patch("src.tasks.payments.process_completion.publish_event", new_callable=AsyncMock),
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_payment_completion(payment_id=payment_id)

        assert result["payment_updated"] is True
        assert result["user_enabled"] is True
        assert result["subscription_extended"] is True
        assert payment.status == "completed"
        mock_remnawave.bulk_extend_expiration_date.assert_called_once_with([user_uuid], 30)
        mock_remnawave.enable_user.assert_called_once_with(user_uuid)
        mock_telegram.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_process_completion_sends_notification(mock_db_session, mock_remnawave, mock_telegram):
    """Test process completion sends notification to user."""
    payment_id = str(uuid4())
    user_uuid = "user-123"

    payment = MagicMock()
    payment.id = payment_id
    payment.status = "pending"
    payment.user_uuid = user_uuid
    payment.amount = 15.0
    payment.currency = "EUR"
    payment.subscription_days = 90

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_remnawave.get_user.return_value = {
        "uuid": user_uuid,
        "username": "prouser",
        "telegram_id": 99999,
    }
    mock_remnawave.bulk_extend_expiration_date = AsyncMock()

    with (
        patch("src.tasks.payments.process_completion.get_session_factory") as mock_factory,
        patch("src.tasks.payments.process_completion.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.process_completion.TelegramClient") as mock_tg,
        patch("src.tasks.payments.process_completion.publish_event", new_callable=AsyncMock),
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_tg.return_value.__aenter__ = AsyncMock(return_value=mock_telegram)
        mock_tg.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_payment_completion(payment_id=payment_id)

        call_args = mock_telegram.send_message.call_args
        assert call_args[1]["chat_id"] == 99999
        mock_remnawave.bulk_extend_expiration_date.assert_called_once_with([user_uuid], 90)


@pytest.mark.asyncio
async def test_process_completion_payment_not_found(mock_db_session):
    """Test process completion handles payment not found."""
    payment_id = str(uuid4())

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.tasks.payments.process_completion.get_session_factory") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        result = await process_payment_completion(payment_id=payment_id)

        assert result["error"] == "payment_not_found"


@pytest.mark.asyncio
async def test_process_completion_already_processed(mock_db_session):
    """Test process completion skips already completed payments."""
    payment_id = str(uuid4())

    payment = MagicMock()
    payment.id = payment_id
    payment.status = "completed"  # Already completed

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.tasks.payments.process_completion.get_session_factory") as mock_factory:
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        result = await process_payment_completion(payment_id=payment_id)

        assert result["already_processed"] is True


@pytest.mark.asyncio
async def test_process_completion_enable_user_fails(mock_db_session, mock_remnawave):
    """Test process completion handles enable user failure."""
    payment_id = str(uuid4())
    user_uuid = "user-123"

    payment = MagicMock()
    payment.id = payment_id
    payment.status = "pending"
    payment.user_uuid = user_uuid
    payment.amount = 10.0
    payment.currency = "USD"
    payment.subscription_days = 30

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = payment
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_remnawave.get_user.return_value = {"uuid": user_uuid}
    mock_remnawave.bulk_extend_expiration_date = AsyncMock()
    mock_remnawave.enable_user.side_effect = Exception("API Error")

    with (
        patch("src.tasks.payments.process_completion.get_session_factory") as mock_factory,
        patch("src.tasks.payments.process_completion.RemnawaveClient") as mock_rw,
        patch("src.tasks.payments.process_completion.publish_event", new_callable=AsyncMock),
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)

        mock_rw.return_value.__aenter__ = AsyncMock(return_value=mock_remnawave)
        mock_rw.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_payment_completion(payment_id=payment_id)

        assert result["payment_updated"] is True
        assert result["user_enabled"] is False
        assert result["subscription_extended"] is True
        assert "error" in result


@pytest.mark.asyncio
async def test_retry_webhooks_retries_failed(mock_db_session):
    """Test retry webhooks reprocesses valid but unprocessed webhooks."""
    webhook1 = MagicMock()
    webhook1.id = uuid4()
    webhook1.is_valid = True
    webhook1.processed_at = None
    webhook1.error_message = None
    webhook1.payload = {"payment_id": "payment-1"}

    webhook2 = MagicMock()
    webhook2.id = uuid4()
    webhook2.is_valid = True
    webhook2.processed_at = None
    webhook2.error_message = None
    webhook2.payload = {"payment_id": "payment-2"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [webhook1, webhook2]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("src.tasks.payments.retry_webhooks.get_session_factory") as mock_factory,
        patch("src.tasks.payments.retry_webhooks.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_task.kiq = AsyncMock()

        result = await retry_failed_webhooks()

        assert result["retried"] == 2
        assert mock_task.kiq.call_count == 2


@pytest.mark.asyncio
async def test_retry_webhooks_skips_invalid(mock_db_session):
    """Test retry webhooks skips invalid webhooks."""
    webhook = MagicMock()
    webhook.id = uuid4()
    webhook.is_valid = False  # Invalid webhook
    webhook.processed_at = None
    webhook.error_message = None
    webhook.payload = {"payment_id": "payment-1"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # Query filters out invalid
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("src.tasks.payments.retry_webhooks.get_session_factory") as mock_factory,
        patch("src.tasks.payments.retry_webhooks.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_task.kiq = AsyncMock()

        result = await retry_failed_webhooks()

        assert result["retried"] == 0
        mock_task.kiq.assert_not_called()


@pytest.mark.asyncio
async def test_retry_webhooks_limits_batch_size(mock_db_session):
    """Test retry webhooks respects batch size limit."""
    webhooks = []
    for i in range(60):  # More than limit of 50
        webhook = MagicMock()
        webhook.id = uuid4()
        webhook.is_valid = True
        webhook.processed_at = None
        webhook.error_message = None
        webhook.payload = {"payment_id": f"payment-{i}"}
        webhooks.append(webhook)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = webhooks[:50]  # Query limits to 50
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("src.tasks.payments.retry_webhooks.get_session_factory") as mock_factory,
        patch("src.tasks.payments.retry_webhooks.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_task.kiq = AsyncMock()

        result = await retry_failed_webhooks()

        assert result["retried"] == 50  # Limited to 50
        assert mock_task.kiq.call_count == 50


@pytest.mark.asyncio
async def test_retry_webhooks_skips_missing_payment_id(mock_db_session):
    """Test retry webhooks skips webhooks without payment_id."""
    webhook1 = MagicMock()
    webhook1.id = uuid4()
    webhook1.is_valid = True
    webhook1.processed_at = None
    webhook1.error_message = None
    webhook1.payload = {}  # No payment_id

    webhook2 = MagicMock()
    webhook2.id = uuid4()
    webhook2.is_valid = True
    webhook2.processed_at = None
    webhook2.error_message = None
    webhook2.payload = {"payment_id": "payment-2"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [webhook1, webhook2]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    with (
        patch("src.tasks.payments.retry_webhooks.get_session_factory") as mock_factory,
        patch("src.tasks.payments.retry_webhooks.process_payment_completion") as mock_task,
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        mock_task.kiq = AsyncMock()

        result = await retry_failed_webhooks()

        assert result["retried"] == 1  # Only webhook2
        mock_task.kiq.assert_called_once_with(payment_id="payment-2")
