from datetime import datetime
from uuid import UUID

from src.domain.entities.user import User
from src.domain.enums import UserStatus


def map_remnawave_user(data: dict) -> User:
    status_map = {
        "active": UserStatus.ACTIVE,
        "disabled": UserStatus.DISABLED,
        "limited": UserStatus.LIMITED,
        "expired": UserStatus.EXPIRED,
    }
    return User(
        uuid=UUID(data["uuid"]),
        username=data["username"],
        status=status_map.get(data.get("status", ""), UserStatus.DISABLED),
        short_uuid=data.get("shortUuid", ""),
        created_at=datetime.fromisoformat(data["createdAt"]),
        updated_at=datetime.fromisoformat(data["updatedAt"]),
        subscription_uuid=UUID(data["subscriptionUuid"]) if data.get("subscriptionUuid") else None,
        expire_at=datetime.fromisoformat(data["expireAt"]) if data.get("expireAt") else None,
        traffic_limit_bytes=data.get("trafficLimitBytes"),
        used_traffic_bytes=data.get("usedTrafficBytes"),
        download_bytes=data.get("downloadBytes"),
        upload_bytes=data.get("uploadBytes"),
        lifetime_used_traffic_bytes=data.get("lifetimeUsedTrafficBytes"),
        online_at=datetime.fromisoformat(data["onlineAt"]) if data.get("onlineAt") else None,
        sub_last_user_agent=data.get("subLastUserAgent"),
        sub_revoked_at=datetime.fromisoformat(data["subRevokedAt"]) if data.get("subRevokedAt") else None,
        last_traffic_reset_at=datetime.fromisoformat(data["lastTrafficResetAt"])
        if data.get("lastTrafficResetAt")
        else None,
        telegram_id=data.get("telegramId"),
        email=data.get("email"),
        hwid_device_limit=data.get("hwidDeviceLimit"),
        subscription_url=data.get("subscriptionUrl") or data.get("subscriptionURL"),
    )
