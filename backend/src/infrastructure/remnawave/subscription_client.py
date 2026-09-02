"""Identity-bound Remnawave subscription client for mobile integration."""

import hashlib
import hmac
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from src.application.dto.mobile_auth import SubscriptionInfoDTO, SubscriptionStatus
from src.application.services.cache_service import CacheService
from src.config.settings import settings
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveUserResponse

logger = logging.getLogger(__name__)

SUBSCRIPTION_CACHE_TTL = 300  # 5 minutes
_SUBSCRIPTION_CACHE_SCHEMA_VERSION = 2
_SUBSCRIPTION_CACHE_HMAC_CONTEXT = b"cybervpn/remnawave-subscription-cache/v2\0"


class RemnawaveSubscriptionError(RuntimeError):
    """Base error for a subscription result that must not become an entitlement."""


class RemnawaveSubscriptionIdentityError(RemnawaveSubscriptionError):
    """The upstream or cached result is not bound to the requested exact user."""


class RemnawaveSubscriptionUnavailableError(RemnawaveSubscriptionError):
    """The provider could not produce a trustworthy subscription result."""


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

    async def get_subscription(
        self,
        user_ref: RemnawaveUserRef | int,
    ) -> SubscriptionInfoDTO:
        """Fetch subscription info for a Remnawave user.

        Args:
            user_ref: Exact numeric Remnawave 3.x identity.

        Returns:
            SubscriptionInfoDTO mapped from an exact identity-bound response.

        Raises:
            RemnawaveSubscriptionIdentityError: Upstream returned another user.
            RemnawaveSubscriptionUnavailableError: No trustworthy result exists.
        """
        identifier = _canonical_numeric_identifier(user_ref)
        try:
            user = await self._client.get_validated(
                f"/api/users/{identifier}",
                RemnawaveUserResponse,
            )
            _require_exact_upstream_identity(user, user_ref=user_ref, numeric_user_id=identifier)
            return self._map_to_dto(user)
        except RemnawaveSubscriptionIdentityError:
            logger.warning(
                "Rejected subscription response with mismatched Remnawave identity",
                extra={"numeric_identity": True},
            )
            raise
        except Exception as exc:
            logger.warning(
                "Failed to fetch subscription from Remnawave",
                extra={"numeric_identity": True, "error_type": type(exc).__name__},
            )
            raise RemnawaveSubscriptionUnavailableError("Remnawave subscription is temporarily unavailable") from exc

    @staticmethod
    def _map_to_dto(user: RemnawaveUserResponse) -> SubscriptionInfoDTO:
        """Map a validated Remnawave user response to a SubscriptionInfoDTO."""
        status = _STATUS_MAP.get(str(user.status).lower(), SubscriptionStatus.NONE)

        # Override to EXPIRED if expire_at is in the past.
        if status == SubscriptionStatus.ACTIVE and user.expire_at:
            if user.expire_at < datetime.now(UTC):
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


class RemnawaveSubscriptionLegacyRollbackClient:
    """Explicit Remnawave 2.x UUID reader for a selected rollback runbook."""

    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def get_subscription(self, legacy_uuid: UUID) -> SubscriptionInfoDTO:
        if not isinstance(legacy_uuid, UUID):
            raise ValueError("Legacy rollback subscription reads require a UUID")
        try:
            user = await self._client.get_validated(
                f"/api/users/{legacy_uuid}",
                RemnawaveUserResponse,
            )
            _require_exact_legacy_upstream_identity(user, legacy_uuid)
            return RemnawaveSubscriptionClient._map_to_dto(user)
        except RemnawaveSubscriptionIdentityError:
            logger.warning(
                "Rejected rollback subscription response with mismatched Remnawave identity",
                extra={"numeric_identity": False, "rollback_adapter": True},
            )
            raise
        except Exception as exc:
            logger.warning(
                "Failed to fetch rollback subscription from Remnawave",
                extra={
                    "numeric_identity": False,
                    "rollback_adapter": True,
                    "error_type": type(exc).__name__,
                },
            )
            raise RemnawaveSubscriptionUnavailableError(
                "Remnawave rollback subscription is temporarily unavailable"
            ) from exc


def _canonical_numeric_identifier(user_ref: RemnawaveUserRef | int) -> int:
    numeric_user_id = user_ref.require_numeric_id() if isinstance(user_ref, RemnawaveUserRef) else user_ref
    if isinstance(numeric_user_id, bool) or not isinstance(numeric_user_id, int) or numeric_user_id <= 0:
        raise ValueError("Remnawave 3.x subscription reads require a reconciled numeric user id")
    return numeric_user_id


def _require_exact_upstream_identity(
    user: RemnawaveUserResponse,
    *,
    user_ref: RemnawaveUserRef | int,
    numeric_user_id: int,
) -> None:
    upstream_numeric_id = user.remnawave_numeric_id
    if (
        isinstance(upstream_numeric_id, bool)
        or not isinstance(upstream_numeric_id, int)
        or upstream_numeric_id <= 0
        or upstream_numeric_id != numeric_user_id
    ):
        raise RemnawaveSubscriptionIdentityError(
            "Remnawave subscription response identity does not match the requested numeric user"
        )
    if isinstance(user_ref, RemnawaveUserRef) and user_ref.legacy_uuid is not None and user.uuid is not None:
        _require_exact_legacy_upstream_identity(user, user_ref.legacy_uuid)


def _require_exact_legacy_upstream_identity(user: RemnawaveUserResponse, expected_legacy_uuid: UUID) -> None:
    try:
        upstream_legacy_uuid = UUID(str(user.uuid))
    except (TypeError, ValueError) as exc:
        raise RemnawaveSubscriptionIdentityError(
            "Remnawave subscription response has no valid rollback identity"
        ) from exc
    if upstream_legacy_uuid != expected_legacy_uuid:
        raise RemnawaveSubscriptionIdentityError(
            "Remnawave subscription response rollback identity does not match the requested user"
        )


def _cache_identity_binding(user_ref: RemnawaveUserRef | int) -> str:
    numeric_user_id = _canonical_numeric_identifier(user_ref)
    legacy_uuid = user_ref.legacy_uuid if isinstance(user_ref, RemnawaveUserRef) else None
    identity_material = f"{numeric_user_id}\0{legacy_uuid or '-'}".encode()
    secret = settings.jwt_secret.get_secret_value().encode()
    return hmac.new(
        secret,
        _SUBSCRIPTION_CACHE_HMAC_CONTEXT + identity_material,
        hashlib.sha256,
    ).hexdigest()


def _cache_key(user_ref: RemnawaveUserRef | int) -> str:
    # Neither the numeric identifier nor the legacy UUID is exposed in Redis
    # keys. The same numeric ID with another rollback UUID is a different key.
    return f"subscription:v2:{_cache_identity_binding(user_ref)}"


def _serialize_dto(dto: SubscriptionInfoDTO, *, identity_binding: str) -> str:
    """Serialize an entitlement together with its exact identity binding."""
    return json.dumps(
        {
            "schema_version": _SUBSCRIPTION_CACHE_SCHEMA_VERSION,
            "identity_binding": identity_binding,
            "subscription": asdict(dto),
        },
        default=str,
    )


def _deserialize_dto(raw: str, *, expected_identity_binding: str) -> SubscriptionInfoDTO:
    """Deserialize only an exact identity-bound v2 cache envelope."""
    envelope = json.loads(raw)
    if not isinstance(envelope, dict) or envelope.get("schema_version") != _SUBSCRIPTION_CACHE_SCHEMA_VERSION:
        raise ValueError("Unsupported subscription cache schema")
    if not hmac.compare_digest(str(envelope.get("identity_binding", "")), expected_identity_binding):
        raise RemnawaveSubscriptionIdentityError("Cached subscription identity binding does not match")
    data = envelope.get("subscription")
    if not isinstance(data, dict):
        raise ValueError("Subscription cache payload is missing")
    return SubscriptionInfoDTO(
        status=SubscriptionStatus(data["status"]),
        plan_name=data.get("plan_name"),
        expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        traffic_limit_bytes=data.get("traffic_limit_bytes"),
        used_traffic_bytes=data.get("used_traffic_bytes"),
        auto_renew=data.get("auto_renew", False),
    )


class CachedSubscriptionClient:
    """Decorator over RemnawaveSubscriptionClient adding identity-bound caching.

    Cache strategy:
    - On exact identity-bound HIT: return cached SubscriptionInfoDTO.
    - On MISS: fetch from Remnawave, cache for 5 min, return.
    - On identity/provider error: propagate a typed error; never synthesize NONE.
    """

    def __init__(
        self,
        inner: RemnawaveSubscriptionClient,
        cache: CacheService,
    ) -> None:
        self._inner = inner
        self._cache = cache

    async def get_subscription(
        self,
        user_ref: RemnawaveUserRef | int,
    ) -> SubscriptionInfoDTO:
        """Get subscription with cache-first strategy and fallback."""
        identity_binding = _cache_identity_binding(user_ref)
        key = _cache_key(user_ref)

        # 1. Try cache.
        cached = await self._cache.get(key)
        if cached is not None:
            try:
                raw = cached if isinstance(cached, str) else json.dumps(cached)
                return _deserialize_dto(raw, expected_identity_binding=identity_binding)
            except RemnawaveSubscriptionIdentityError:
                logger.warning("Rejected subscription cache entry with mismatched identity binding")
                raise
            except Exception as exc:
                logger.warning(
                    "Corrupt subscription cache entry; fetching fresh",
                    extra={"error_type": type(exc).__name__},
                )

        # 2. Fetch from Remnawave.
        dto = await self._inner.get_subscription(user_ref)

        # NONE is a legitimate, identity-bound upstream state only when the
        # provider returned a valid user whose status maps to NONE. Provider
        # and identity failures raise typed exceptions before this point.
        if dto.status is SubscriptionStatus.NONE:
            return dto

        # 3. Cache the successfully identity-bound result.
        try:
            await self._cache.set(
                key,
                _serialize_dto(dto, identity_binding=identity_binding),
                ttl=SUBSCRIPTION_CACHE_TTL,
            )
        except Exception as exc:
            logger.warning(
                "Failed to cache subscription",
                extra={"error_type": type(exc).__name__},
            )

        return dto

    async def invalidate(self, user_ref: RemnawaveUserRef | int) -> None:
        """Invalidate cached subscription for a user (e.g. after purchase)."""
        await self._cache.delete(_cache_key(user_ref))
