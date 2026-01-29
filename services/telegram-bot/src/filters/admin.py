"""CyberVPN Telegram Bot — Admin access filter.

Restricts handler access to configured admin Telegram IDs.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.config import BotSettings


class IsAdmin(BaseFilter):
    """Filter that passes only for admin users.

    Checks the user's Telegram ID against the ADMIN_IDS list
    from bot settings.

    Usage in handlers:
        @router.message(IsAdmin(), Command("admin"))
        async def admin_panel(message: Message): ...
    """

    async def __call__(
        self,
        event: Message | CallbackQuery,
        settings: BotSettings,
    ) -> bool:
        """Check if the event sender is an admin.

        Args:
            event: Incoming message or callback query.
            settings: Bot settings with admin IDs list.

        Returns:
            True if the sender is in the admin list.
        """
        user = event.from_user
        if user is None:
            return False
        return settings.is_admin(user.id)
