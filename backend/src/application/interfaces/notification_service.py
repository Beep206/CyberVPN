from abc import ABC, abstractmethod


class NotificationService(ABC):
    @abstractmethod
    async def send_telegram(self, telegram_id: int, message: str) -> bool: ...

    @abstractmethod
    async def send_email(self, email: str, subject: str, body: str) -> bool: ...

    @abstractmethod
    async def send_sms(self, phone: str, message: str) -> bool: ...
