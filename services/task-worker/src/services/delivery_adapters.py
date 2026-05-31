"""Future delivery-channel adapter boundaries for worker fanout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog

from src.metrics import MESSAGING_DELIVERY_ADAPTER_TOTAL

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    channel: str
    recipient_type: str
    recipient_id: str
    notification_id: str
    event_key: str


@dataclass(frozen=True, slots=True)
class DeliveryAttemptResult:
    channel: str
    status: str
    provider_message_id: str | None = None
    disabled: bool = False


class DeliveryChannelAdapter(Protocol):
    async def send(self, attempt: DeliveryAttempt) -> DeliveryAttemptResult:
        """Attempt delivery without exposing notification content to adapter logs."""


class DisabledDeliveryChannelAdapter:
    """No-op external adapter used until Telegram/email/push delivery is approved."""

    def __init__(self, channel: str) -> None:
        self.channel = channel

    async def send(self, attempt: DeliveryAttempt) -> DeliveryAttemptResult:
        logger.info(
            "messaging_delivery_adapter_disabled",
            channel=self.channel,
            recipient_type=attempt.recipient_type,
            notification_id=attempt.notification_id,
            event_key=attempt.event_key,
        )
        MESSAGING_DELIVERY_ADAPTER_TOTAL.labels(channel=self.channel, status="disabled").inc()
        return DeliveryAttemptResult(channel=self.channel, status="disabled", disabled=True)


def get_future_delivery_adapters() -> tuple[DeliveryChannelAdapter, ...]:
    """Return disabled placeholders for future external delivery channels."""

    return (
        DisabledDeliveryChannelAdapter("telegram"),
        DisabledDeliveryChannelAdapter("email"),
        DisabledDeliveryChannelAdapter("push"),
    )
