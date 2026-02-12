import logging

from httpx import AsyncClient

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str) -> None:
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient(timeout=30.0)
        return self._client

    async def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
        client = await self._get_client()
        try:
            response = await client.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
            return response.is_success
        except Exception as e:
            logger.warning("Failed to send Telegram message to chat %s: %s", chat_id, e)
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
