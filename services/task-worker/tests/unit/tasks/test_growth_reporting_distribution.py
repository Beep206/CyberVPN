"""Unit tests for recurring growth reporting delivery and cleanup tasks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.tasks.analytics.cleanup_growth_reporting import cleanup_growth_reporting_artifacts
from src.tasks.analytics.process_growth_reporting_governance_followups import (
    process_growth_reporting_governance_followups,
)
from src.tasks.email.process_growth_reporting_deliveries import (
    process_growth_reporting_deliveries,
)


class _SuccessfulSmtpReportingClient:
    last_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_growth_notification(self, **kwargs):
        type(self).last_kwargs = kwargs
        return {"id": "msg-report-1", "status": "sent"}


class _FailingSmtpReportingClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_growth_notification(self, **kwargs):
        raise TimeoutError("smtp timed out")


@pytest.mark.asyncio
async def test_process_growth_reporting_deliveries_claims_and_completes_successfully(
    mock_settings,
) -> None:
    mock_settings.email_dev_mode = True
    _SuccessfulSmtpReportingClient.last_kwargs = None

    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.claim_growth_reporting_deliveries = AsyncMock(
        return_value={
            "deliveries": [
                {
                    "delivery_id": "delivery-1",
                    "recipient_email": "finance-growth@example.test",
                    "recipient_name": "Finance",
                    "audience_key": "finance",
                    "delivery_channel": "email",
                    "subject": "Finance digest",
                    "title": "Finance growth reporting digest",
                    "message": "Daily growth reporting digest is ready.",
                    "notes": ["Window: 2026-03-24 -> 2026-04-22"],
                    "locale": "en-EN",
                }
            ],
            "claimed_count": 1,
            "skipped_count": 0,
            "overdue_count": 0,
        }
    )
    mock_backend.complete_growth_reporting_delivery = AsyncMock(
        return_value={
            "id": "delivery-1",
            "delivery_status": "delivered",
            "provider_name": "smtp",
            "provider_message_id": "msg-report-1",
        }
    )

    with (
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.BackendAPIClient",
        ) as mock_backend_cls,
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.SmtpClient",
            _SuccessfulSmtpReportingClient,
        ),
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_growth_reporting_deliveries.original_func()

    assert result["claimed_count"] == 1
    assert result["delivered_count"] == 1
    assert result["failed_count"] == 0
    assert _SuccessfulSmtpReportingClient.last_kwargs["subject"] == "Finance digest"
    mock_backend.claim_growth_reporting_deliveries.assert_awaited_once_with({"limit": 10})
    mock_backend.complete_growth_reporting_delivery.assert_awaited_once_with(
        delivery_id="delivery-1",
        payload={
            "delivery_status": "delivered",
            "provider_name": "smtp",
            "provider_message_id": "msg-report-1",
            "failure_message": None,
        },
    )


@pytest.mark.asyncio
async def test_process_growth_reporting_deliveries_marks_failed_delivery_on_email_error(
    mock_settings,
) -> None:
    mock_settings.email_dev_mode = True

    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.claim_growth_reporting_deliveries = AsyncMock(
        return_value={
            "deliveries": [
                {
                    "delivery_id": "delivery-2",
                    "recipient_email": "risk-growth@example.test",
                    "recipient_name": "Risk",
                    "audience_key": "risk",
                    "delivery_channel": "email",
                    "subject": "Risk digest",
                    "title": "Risk growth reporting digest",
                    "message": "Weekly growth reporting digest is ready.",
                    "notes": [],
                    "locale": "en-EN",
                }
            ],
            "claimed_count": 1,
            "skipped_count": 0,
            "overdue_count": 0,
        }
    )
    mock_backend.complete_growth_reporting_delivery = AsyncMock(
        return_value={
            "id": "delivery-2",
            "delivery_status": "failed",
            "provider_name": "smtp",
        }
    )

    with (
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.BackendAPIClient",
        ) as mock_backend_cls,
        patch(
            "src.tasks.email.process_growth_reporting_deliveries.SmtpClient",
            _FailingSmtpReportingClient,
        ),
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_growth_reporting_deliveries.original_func()

    assert result["claimed_count"] == 1
    assert result["delivered_count"] == 0
    assert result["failed_count"] == 1
    mock_backend.complete_growth_reporting_delivery.assert_awaited_once_with(
        delivery_id="delivery-2",
        payload={
            "delivery_status": "failed",
            "provider_name": "smtp",
            "provider_message_id": None,
            "failure_message": "timeout",
        },
    )


@pytest.mark.asyncio
async def test_cleanup_growth_reporting_artifacts_calls_backend_cleanup(mock_settings) -> None:
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.cleanup_growth_reporting_artifacts = AsyncMock(
        return_value={
            "rollups_deleted": 3,
            "refresh_runs_deleted": 2,
            "deliveries_deleted": 4,
            "executed_at": "2026-04-22T15:00:00Z",
        }
    )

    with (
        patch(
            "src.tasks.analytics.cleanup_growth_reporting.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.analytics.cleanup_growth_reporting.BackendAPIClient",
        ) as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await cleanup_growth_reporting_artifacts.original_func()

    assert result["rollups_deleted"] == 3
    assert result["refresh_runs_deleted"] == 2
    assert result["deliveries_deleted"] == 4
    mock_backend.cleanup_growth_reporting_artifacts.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_process_growth_reporting_governance_followups_calls_backend(mock_settings) -> None:
    mock_backend = AsyncMock()
    mock_backend.enabled = True
    mock_backend.process_growth_reporting_governance_followups = AsyncMock(
        return_value={
            "processed_at": "2026-04-22T15:30:00Z",
            "scanned_count": 6,
            "opened_count": 2,
            "reopened_count": 1,
            "auto_resolved_count": 1,
            "reminded_count": 1,
            "open_count": 2,
            "overdue_count": 1,
        }
    )

    with (
        patch(
            "src.tasks.analytics.process_growth_reporting_governance_followups.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.analytics.process_growth_reporting_governance_followups.BackendAPIClient",
        ) as mock_backend_cls,
    ):
        mock_backend_cls.return_value.__aenter__ = AsyncMock(return_value=mock_backend)
        mock_backend_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await process_growth_reporting_governance_followups.original_func()

    assert result["scanned_count"] == 6
    assert result["opened_count"] == 2
    assert result["overdue_count"] == 1
    mock_backend.process_growth_reporting_governance_followups.assert_awaited_once_with()
