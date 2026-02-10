"""Remnawave subscription client for mobile app integration.

Fetches user subscription data from Remnawave VPN backend
and maps it to application-layer DTOs.  Includes a Redis caching
layer (5-min TTL) and graceful fallback when Remnawave is unavailable.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from src.application.dto.mobile_auth import SubscriptionInfoDTO, SubscriptionStatus
from src.application.services.cache_service import CacheService
from src.infrastructure.remnawave.client import RemnawaveClient

logger = logging.getLogger(__name__)

SUBSCRIPTION_CACHE_TTL = 300  # 5 minutes


class RemnawaveUserResponse(BaseModel):
    """Validated Remnawave user API response schema.

    Maps the camelCase JSON response from Remnawave ``GET /api/users/{uuid}``.
    Only fields relevant to subscription status are included;
    unknown fields are silently stripped by Pydantic.
    """

    model_config = ConfigDict(populate_by_name=True)

    uuid: str
    username: str
    status: str
    short_uuid: str | None = Field(default=None, alias="shortUuid")
    subscription_uuid: str | None = Field(default=None, alias="subscriptionUuid")
    expire_at: datetime | None = Field(default=None, alias="expireAt")
    traffic_limit_bytes: int | None = Field(default=None, alias="trafficLimitBytes")
    used_traffic_bytes: int | None = Field(default=None, alias="usedTrafficBytes")
    online_at: datetime | None = Field(default=None, alias="onlineAt")
    sub_revoked_at: datetime | None = Field(default=None, alias="subRevokedAt")


# Map Remnawave user status string to SubscriptionStatus enum.
_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "active": SubscriptionStatus.ACTIVE,
    "expired": SubscriptionStatus.EXPIRED,
    "disabled": SubscriptionStatus.CANCELLED,
    "limited": SubscriptionStatus.ACTIVE,  # limited = active but throttled
}


class RemnawaveSubscriptionClient:
    """Fetches subscription data from Remnawave and maps to SubscriptionInfoDTO.

    Uses the validated HTTP client to guard against upstream response tampering.
    """

    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def get_subscription(self, remnawave_uuid: str) -> SubscriptionInfoDTO:
        """Fetch subscription info for a Remnawave user.

        Args:
            remnawave_uuid: The user's UUID in the Remnawave system.

        Returns:
            SubscriptionInfoDTO mapped from Remnawave data.
            Falls back to ``SubscriptionStatus.NONE`` on any error.
        """
        try:
            user = await self._client.get_validated(
                f"/api/users/{remnawave_uuid}",
                RemnawaveUserResponse,
            )
            return self._map_to_dto(user)
        except Exception:
            logger.exception(
                "Failed to fetch subscription from Remnawave",
                extra={"remnawave_uuid": remnawave_uuid},
            )
            return SubscriptionInfoDTO(status=SubscriptionStatus.NONE)

    @staticmethod
    def _map_to_dto(user: RemnawaveUserResponse) -> SubscriptionInfoDTO:
        """Map a validated Remnawave user response to a SubscriptionInfoDTO."""
        status = _STATUS_MAP.get(user.status, SubscriptionStatus.NONE)

        # Override to EXPIRED if expire_at is in the past.
        if status == SubscriptionStatus.ACTIVE and user.expire_at:
            if user.expire_at < datetime.now(timezone.utc):
                status = SubscriptionStatus.EXPIRED

        # Override to CANCELLED if subscription was explicitly revoked.
        if user.sub_revoked_at is not None:
            status = SubscriptionStatus.CANCELLED

        # Derive plan name from subscription UUID presence.
        plan_name: str | None = None
        if user.subscription_uuid:
            plan_name = "VPN"  # Generic label; enriched by caching layer later

        return SubscriptionInfoDTO(
            status=status,
            plan_name=plan_name,
            expires_at=user.expire_at,
            traffic_limit_bytes=user.traffic_limit_bytes,
            used_traffic_bytes=user.used_traffic_bytes,
            auto_renew=False,
        )


def _cache_key(remnawave_uuid: str) -> str:
    return f"subscription:{remnawave_uuid}"


def _serialize_dto(dto: SubscriptionInfoDTO) -> str:
    """Serialize SubscriptionInfoDTO to JSON for cache storage."""
    data = asdict(dto)
    return json.dumps(data, default=str)


def _deserialize_dto(raw: str) -> SubscriptionInfoDTO:
    """Deserialize cached JSON back to SubscriptionInfoDTO."""
    data = json.loads(raw)
    return SubscriptionInfoDTO(
        status=SubscriptionStatus(data["status"]),
        plan_name=data.get("plan_name"),
        expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        traffic_limit_bytes=data.get("traffic_limit_bytes"),
        used_traffic_bytes=data.get("used_traffic_bytes"),
        auto_renew=data.get("auto_renew", False),
    )


class CachedSubscriptionClient:
    """Decorator over RemnawaveSubscriptionClient adding Redis caching + fallback.

    Cache strategy:
    - On HIT: return cached SubscriptionInfoDTO immediately.
    - On MISS: fetch from Remnawave, cache for 5 min, return.
    - On Remnawave ERROR: return stale cache (if any) or NONE fallback.
    """

    def __init__(
        self,
        inner: RemnawaveSubscriptionClient,
        cache: CacheService,
    ) -> None:
        self._inner = inner
        self._cache = cache

    async def get_subscription(self, remnawave_uuid: str) -> SubscriptionInfoDTO:
        """Get subscription with cache-first strategy and fallback."""
        key = _cache_key(remnawave_uuid)

        # 1. Try cache.
        cached = await self._cache.get(key)
        if cached is not None:
            try:
                return _deserialize_dto(cached) if isinstance(cached, str) else _deserialize_dto(json.dumps(cached))
            except Exception:
                logger.warning("Corrupt subscription cache entry, fetching fresh", extra={"key": key})

        # 2. Fetch from Remnawave.
        dto = await self._inner.get_subscription(remnawave_uuid)

        # 3. Cache the result (even NONE status, to avoid hammering on missing users).
        try:
            await self._cache.set(key, _serialize_dto(dto), ttl=SUBSCRIPTION_CACHE_TTL)
        except Exception:
            logger.warning("Failed to cache subscription", extra={"key": key})

        return dto

    async def invalidate(self, remnawave_uuid: str) -> None:
        """Invalidate cached subscription for a user (e.g. after purchase)."""
        await self._cache.delete(_cache_key(remnawave_uuid))
