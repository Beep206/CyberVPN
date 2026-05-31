"""Telegram Mini App initData replay protection contracts."""

from typing import Protocol


class TelegramInitDataReplayError(Exception):
    """Base error for Telegram Mini App initData replay protection."""


class TelegramInitDataReplayedError(TelegramInitDataReplayError):
    """Raised when an initData payload was already accepted."""


class TelegramInitDataReplayUnavailableError(TelegramInitDataReplayError):
    """Raised when replay protection cannot make a safe decision."""


class TelegramInitDataReplayGuard(Protocol):
    """Accepts each validated Telegram Mini App initData payload at most once."""

    async def accept(
        self,
        *,
        canonical_init_data: str,
        telegram_id: str,
        auth_date: int,
        max_age_seconds: int,
    ) -> None:
        """Record a validated initData payload or raise when it was already used."""
