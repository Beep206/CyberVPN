from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.notification_queue_model import NotificationQueue
from src.infrastructure.external.telegram_notifier import TelegramNotifier


class SendNotificationUseCase:
    def __init__(self, notifier: TelegramNotifier, session: AsyncSession) -> None:
        self._notifier = notifier
        self._session = session

    async def send_immediate(self, telegram_id: int, message: str) -> bool:
        return await self._notifier.send_message(telegram_id, message)

    async def queue_for_later(
        self, telegram_id: int, message: str, notification_type: str | None = None
    ) -> NotificationQueue:
        entry = NotificationQueue(
            telegram_id=telegram_id,
            message=message,
            notification_type=notification_type,
            scheduled_at=datetime.now(UTC),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def broadcast(self, telegram_ids: list[int], message: str) -> int:
        sent = 0
        for tid in telegram_ids:
            if await self._notifier.send_message(tid, message):
                sent += 1
        return sent
