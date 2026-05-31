"""Redis-backed replay guard for Telegram Mini App initData."""

import hashlib
import logging
import time

import redis.asyncio as redis

from src.application.services.telegram_init_data_replay import (
    TelegramInitDataReplayedError,
    TelegramInitDataReplayUnavailableError,
)
from src.config.settings import settings

logger = logging.getLogger(__name__)

_FUTURE_AUTH_DATE_SKEW_SECONDS = 300


class RedisTelegramInitDataReplayGuard:
    """Stores deterministic initData fingerprints in Redis with NX semantics."""

    _KEY_PREFIX = "cybervpn:tg_auth:miniapp:init_data_replay"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def accept(
        self,
        *,
        canonical_init_data: str,
        telegram_id: str,
        auth_date: int,
        max_age_seconds: int,
    ) -> None:
        digest = self._build_digest(
            canonical_init_data=canonical_init_data,
            telegram_id=telegram_id,
            auth_date=auth_date,
        )
        key = f"{self._KEY_PREFIX}:{digest}"
        ttl_seconds = self._ttl_seconds(auth_date=auth_date, max_age_seconds=max_age_seconds)

        try:
            accepted = await self._redis.set(
                key,
                "1",
                ex=ttl_seconds,
                nx=True,
            )
        except Exception as exc:
            logger.error(
                "Telegram Mini App initData replay guard unavailable",
                extra={"replay_digest_prefix": digest[:12], "posture": self._failure_posture()},
            )
            if str(settings.environment).lower() == "production":
                raise TelegramInitDataReplayUnavailableError("Telegram replay guard unavailable") from exc
            return

        if not accepted:
            logger.warning(
                "Telegram Mini App initData replay rejected",
                extra={"replay_digest_prefix": digest[:12]},
            )
            raise TelegramInitDataReplayedError("Telegram initData has already been used")

    @classmethod
    def _build_digest(cls, *, canonical_init_data: str, telegram_id: str, auth_date: int) -> str:
        material = f"{canonical_init_data}\n{auth_date}\n{telegram_id}".encode()
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def _ttl_seconds(*, auth_date: int, max_age_seconds: int) -> int:
        max_age = max(1, int(max_age_seconds))
        expires_at = auth_date + max_age
        remaining = expires_at - int(time.time())
        return max(1, min(max_age + _FUTURE_AUTH_DATE_SKEW_SECONDS, remaining))

    @staticmethod
    def _failure_posture() -> str:
        if str(settings.environment).lower() == "production":
            return "fail_closed"
        return "fail_open_non_production"
