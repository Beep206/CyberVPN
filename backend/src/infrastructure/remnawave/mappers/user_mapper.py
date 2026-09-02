from datetime import datetime
from typing import Any
from uuid import UUID

from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.subscription_urls import normalize_public_subscription_url


def map_remnawave_user(data: dict[str, Any]) -> User:
    status_map = {
        "active": UserStatus.ACTIVE,
        "disabled": UserStatus.DISABLED,
        "limited": UserStatus.LIMITED,
        "expired": UserStatus.EXPIRED,
    }
    raw_status = str(data.get("status", "")).lower()
    raw_uuid = data.get("uuid")
    raw_id = next((data[key] for key in ("id", "userId", "numericId") if key in data), None)
    if raw_uuid is None and raw_id is None:
        raise ValueError("Remnawave user payload contains neither numeric id nor legacy UUID")
    if raw_id is not None and (isinstance(raw_id, bool) or not isinstance(raw_id, int) or raw_id <= 0):
        raise ValueError("Remnawave numeric user id must be an exact positive integer")
    raw_user_traffic = data.get("userTraffic")
    user_traffic: dict[str, Any] = raw_user_traffic if isinstance(raw_user_traffic, dict) else {}
    active_internal_squad_uuids = _normalize_active_internal_squads(data)
    return User(
        uuid=UUID(str(raw_uuid)) if raw_uuid else None,
        username=data["username"],
        status=status_map.get(raw_status, UserStatus.DISABLED),
        short_uuid=data.get("shortUuid", ""),
        created_at=datetime.fromisoformat(data["createdAt"]),
        updated_at=datetime.fromisoformat(data["updatedAt"]),
        remnawave_id=raw_id,
        subscription_uuid=UUID(data["subscriptionUuid"]) if data.get("subscriptionUuid") else None,
        expire_at=datetime.fromisoformat(data["expireAt"]) if data.get("expireAt") else None,
        traffic_limit_bytes=data.get("trafficLimitBytes"),
        used_traffic_bytes=data.get("usedTrafficBytes", user_traffic.get("usedTrafficBytes")),
        download_bytes=data.get("downloadBytes"),
        upload_bytes=data.get("uploadBytes"),
        lifetime_used_traffic_bytes=data.get("lifetimeUsedTrafficBytes", user_traffic.get("lifetimeUsedTrafficBytes")),
        online_at=datetime.fromisoformat(data.get("onlineAt") or user_traffic["onlineAt"])
        if data.get("onlineAt") or user_traffic.get("onlineAt")
        else None,
        sub_last_user_agent=data.get("subLastUserAgent"),
        sub_revoked_at=datetime.fromisoformat(data["subRevokedAt"]) if data.get("subRevokedAt") else None,
        last_traffic_reset_at=datetime.fromisoformat(data["lastTrafficResetAt"])
        if data.get("lastTrafficResetAt")
        else None,
        telegram_id=data.get("telegramId"),
        email=data.get("email"),
        hwid_device_limit=data.get("hwidDeviceLimit"),
        subscription_url=normalize_public_subscription_url(data.get("subscriptionUrl") or data.get("subscriptionURL")),
        auto_renew=data.get("autoRenew", data.get("auto_renew")),
        traffic_limit_strategy=data.get("trafficLimitStrategy") if "trafficLimitStrategy" in data else None,
        active_internal_squad_uuids=active_internal_squad_uuids,
        external_squad_uuid=data.get("externalSquadUuid") if "externalSquadUuid" in data else None,
        external_squad_uuid_observed="externalSquadUuid" in data,
    )


def _normalize_active_internal_squads(data: dict[str, Any]) -> tuple[str, ...] | None:
    if "activeInternalSquads" not in data:
        return None
    raw_squads = data["activeInternalSquads"]
    if not isinstance(raw_squads, list):
        raise ValueError("Remnawave activeInternalSquads must be a list")
    normalized: list[str] = []
    for raw_squad in raw_squads:
        if isinstance(raw_squad, str):
            squad_uuid = raw_squad
        elif isinstance(raw_squad, dict) and raw_squad.get("uuid"):
            squad_uuid = str(raw_squad["uuid"])
        else:
            raise ValueError("Remnawave activeInternalSquads contains an invalid squad reference")
        if not squad_uuid:
            raise ValueError("Remnawave activeInternalSquads contains an empty squad reference")
        normalized.append(squad_uuid)
    if len(normalized) != len(set(normalized)):
        raise ValueError("Remnawave activeInternalSquads contains duplicate squad references")
    return tuple(normalized)
