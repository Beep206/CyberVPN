from src.domain.events.base import DomainEvent, PaymentCompletedEvent, ServerStatusChangedEvent
from src.infrastructure.messaging.websocket_manager import ws_manager


class NotificationEventHandler:
    async def handle(self, event: DomainEvent) -> None:
        await ws_manager.broadcast("events", {
            "event": event.event_type,
            "data": event.data,
            "occurred_at": event.occurred_at.isoformat(),
        })

        if isinstance(event, ServerStatusChangedEvent):
            await ws_manager.broadcast("monitoring", {
                "event": "server_status",
                "server_uuid": str(event.server_uuid),
                "status": event.new_status,
            })

        if isinstance(event, PaymentCompletedEvent):
            await ws_manager.broadcast("notifications", {
                "event": "payment_completed",
                "user_uuid": str(event.user_uuid),
                "amount": event.amount,
            })
