from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from src.config.settings import settings


@dataclass(frozen=True)
class TelegramStarsRefundResult:
    external_reference: str
    provider_snapshot: dict[str, Any]
    already_refunded: bool = False


class TelegramStarsRefundError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class TelegramStarsClient:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: SecretStr | str | None = None) -> None:
        self._bot_token = bot_token if bot_token is not None else settings.telegram_bot_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self._client

    async def refund_payment(
        self,
        *,
        user_id: int,
        telegram_payment_charge_id: str,
        provider_payment_charge_id: str | None = None,
    ) -> TelegramStarsRefundResult:
        token = self._resolve_bot_token()
        if not token:
            raise TelegramStarsRefundError("Telegram bot token is not configured", status_code=503)

        client = await self._get_client()
        try:
            response = await client.post(
                f"/bot{token}/refundStarPayment",
                json={
                    "user_id": user_id,
                    "telegram_payment_charge_id": telegram_payment_charge_id,
                },
            )
        except httpx.HTTPError as exc:
            raise TelegramStarsRefundError(f"Telegram Stars refund request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise TelegramStarsRefundError("Telegram Stars refund returned invalid JSON") from exc

        if payload.get("ok") is True and payload.get("result") is True:
            return TelegramStarsRefundResult(
                external_reference=telegram_payment_charge_id,
                provider_snapshot={
                    "provider": "telegram_stars",
                    "refund_method": "refundStarPayment",
                    "telegram_user_id": user_id,
                    "telegram_payment_charge_id": telegram_payment_charge_id,
                    "provider_payment_charge_id": provider_payment_charge_id,
                    "provider_result": "refunded",
                    "telegram_status_code": response.status_code,
                },
                already_refunded=False,
            )

        description = str(payload.get("description") or "Telegram Stars refund failed")
        if _looks_like_already_refunded(description):
            return TelegramStarsRefundResult(
                external_reference=telegram_payment_charge_id,
                provider_snapshot={
                    "provider": "telegram_stars",
                    "refund_method": "refundStarPayment",
                    "telegram_user_id": user_id,
                    "telegram_payment_charge_id": telegram_payment_charge_id,
                    "provider_payment_charge_id": provider_payment_charge_id,
                    "provider_result": "already_refunded",
                    "telegram_status_code": response.status_code,
                    "telegram_error_description": description,
                },
                already_refunded=True,
            )

        raise TelegramStarsRefundError(description)

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    def _resolve_bot_token(self) -> str:
        if isinstance(self._bot_token, SecretStr):
            return self._bot_token.get_secret_value().strip()
        return str(self._bot_token or "").strip()


def _looks_like_already_refunded(description: str) -> bool:
    normalized = description.strip().lower()
    return "already refunded" in normalized or "already_refunded" in normalized
