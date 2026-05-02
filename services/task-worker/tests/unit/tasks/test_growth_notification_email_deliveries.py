"""Unit tests for scheduled growth notification email delivery processing."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tasks.email.process_growth_notification_deliveries import (
    process_growth_notification_deliveries,
)


class _SuccessfulSmtpNotificationClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_growth_notification(self, **kwargs):
        return {"id": "msg-growth-1", "status": "sent"}


class _FailingSmtpNotificationClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_growth_notification(self, **kwargs):
        raise TimeoutError("smtp timed out")


@pytest.mark.asyncio
async def test_process_growth_notification_deliveries_marks_success(mock_settings, mock_db_session):
    delivery = MagicMock()
    delivery.id = uuid4()
    delivery.delivery_payload = {
        "recipient_email": "growth@example.com",
        "locale": "en-EN",
        "route_slug": "/referral",
        "notes": ["Ticket: SUP-42"],
    }
    delivery.title = "Account review update"
    delivery.message = "Support issued a manual growth notice."
    delivery.delivery_status = "planned"
    delivery.status_reason = None
    delivery.delivered_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [delivery]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_settings.email_dev_mode = True
    mock_settings.magic_link_base_url = "https://app.cybervpn.test"

    with (
        patch(
            "src.tasks.email.process_growth_notification_deliveries.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.email.process_growth_notification_deliveries.get_session_factory",
        ) as mock_factory,
        patch(
            "src.tasks.email.process_growth_notification_deliveries.SmtpClient",
            _SuccessfulSmtpNotificationClient,
        ),
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        result = await process_growth_notification_deliveries.original_func()

    assert result["sent"] == 1
    assert result["failed"] == 0
    assert delivery.delivery_status == "delivered"
    assert delivery.delivered_at is not None
    assert delivery.status_reason is None


@pytest.mark.asyncio
async def test_process_growth_notification_deliveries_marks_failure(mock_settings, mock_db_session):
    delivery = MagicMock()
    delivery.id = uuid4()
    delivery.delivery_payload = {
        "recipient_email": "growth@example.com",
        "locale": "en-EN",
        "route_slug": "/referral",
        "notes": [],
    }
    delivery.title = "Account review update"
    delivery.message = "Support issued a manual growth notice."
    delivery.delivery_status = "planned"
    delivery.status_reason = None
    delivery.delivered_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [delivery]
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    mock_settings.email_dev_mode = True
    mock_settings.magic_link_base_url = "https://app.cybervpn.test"

    with (
        patch(
            "src.tasks.email.process_growth_notification_deliveries.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "src.tasks.email.process_growth_notification_deliveries.get_session_factory",
        ) as mock_factory,
        patch(
            "src.tasks.email.process_growth_notification_deliveries.SmtpClient",
            _FailingSmtpNotificationClient,
        ),
    ):
        mock_factory.return_value = MagicMock(return_value=mock_db_session)
        result = await process_growth_notification_deliveries.original_func()

    assert result["sent"] == 0
    assert result["failed"] == 1
    assert delivery.delivery_status == "failed"
    assert delivery.status_reason == "timeout"
