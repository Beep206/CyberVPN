import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from src.config.settings import settings
from src.domain.entities.user import User
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.mappers.user_mapper import map_remnawave_user

logger = logging.getLogger(__name__)


class RemnawaveUserGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client
        self._default_internal_squad_uuids: list[str] | None = None

    async def _resolve_default_internal_squad_uuids(self) -> list[str]:
        if self._default_internal_squad_uuids is not None:
            return self._default_internal_squad_uuids

        configured_uuid = settings.remnawave_default_internal_squad_uuid.strip()
        if configured_uuid:
            self._default_internal_squad_uuids = [configured_uuid]
            return self._default_internal_squad_uuids

        configured_name = settings.remnawave_default_internal_squad_name.strip() or "Default-Squad"

        try:
            payload = await self._client.get("/internal-squads")
        except Exception as exc:
            logger.warning("Failed to fetch Remnawave internal squads: %s", exc)
            self._default_internal_squad_uuids = []
            return self._default_internal_squad_uuids

        squads = payload.get("internalSquads", payload) if isinstance(payload, dict) else payload
        if not isinstance(squads, list):
            self._default_internal_squad_uuids = []
            return self._default_internal_squad_uuids

        named_match = [
            str(squad["uuid"])
            for squad in squads
            if isinstance(squad, dict)
            and squad.get("uuid")
            and squad.get("name") == configured_name
        ]
        if named_match:
            self._default_internal_squad_uuids = named_match[:1]
            return self._default_internal_squad_uuids

        if len(squads) == 1 and isinstance(squads[0], dict) and squads[0].get("uuid"):
            self._default_internal_squad_uuids = [str(squads[0]["uuid"])]
            return self._default_internal_squad_uuids

        logger.warning(
            "No default Remnawave internal squad resolved. "
            "Configure REMNAWAVE_DEFAULT_INTERNAL_SQUAD_UUID or ensure %s exists.",
            configured_name,
        )
        self._default_internal_squad_uuids = []
        return self._default_internal_squad_uuids

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        try:
            data = await self._client.get(f"/api/users/{uuid}")
            return map_remnawave_user(data)
        except Exception as e:
            logger.warning("Failed to fetch user %s from Remnawave: %s", uuid, e)
            return None

    async def get_by_username(self, username: str) -> User | None:
        try:
            data = await self._client.get(f"/api/users/by-username/{username}")
            return map_remnawave_user(data)
        except Exception as e:
            logger.warning("Failed to fetch user by username from Remnawave: %s", e)
            return None

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        try:
            data = await self._client.get(f"/api/users/by-telegram-id/{telegram_id}")
            return map_remnawave_user(data)
        except Exception as e:
            logger.warning("Failed to fetch user by telegram_id %s from Remnawave: %s", telegram_id, e)
            return None

    async def get_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        data = await self._client.get("/api/users", params={"start": offset, "size": limit})
        users = data.get("users", data) if isinstance(data, dict) else data
        return [map_remnawave_user(u) for u in users]

    @staticmethod
    def _normalize_user_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(raw_payload)

        field_mapping = {
            "expire_at": "expireAt",
            "telegram_id": "telegramId",
            "data_limit": "trafficLimitBytes",
            "traffic_limit_bytes": "trafficLimitBytes",
            "hwid_device_limit": "hwidDeviceLimit",
            "external_squad_uuid": "externalSquadUuid",
            "active_internal_squads": "activeInternalSquads",
        }

        for source, target in field_mapping.items():
            if source in payload and target not in payload:
                payload[target] = payload.pop(source)

        expire_at = payload.get("expireAt")
        if isinstance(expire_at, datetime):
            payload["expireAt"] = expire_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

        # Remnawave generates protocol secrets itself; our local password field is not part
        # of the upstream contract.
        payload.pop("password", None)

        return payload

    @staticmethod
    def _build_default_expire_at() -> str:
        expires_at = datetime.now(UTC) + timedelta(days=settings.remnawave_default_user_expire_days)
        return expires_at.isoformat().replace("+00:00", "Z")

    async def create(self, username: str, **kwargs) -> User:
        payload = self._normalize_user_payload({"username": username, **kwargs})
        if not payload.get("expireAt"):
            payload["expireAt"] = self._build_default_expire_at()
        if not payload.get("activeInternalSquads"):
            default_internal_squad_uuids = await self._resolve_default_internal_squad_uuids()
            if default_internal_squad_uuids:
                payload["activeInternalSquads"] = default_internal_squad_uuids
        data = await self._client.post("/api/users", json=payload)
        return map_remnawave_user(data)

    async def update(self, uuid: UUID, **kwargs) -> User:
        payload = self._normalize_user_payload({"uuid": str(uuid), **kwargs})
        data = await self._client.patch("/api/users", json=payload)
        return map_remnawave_user(data)

    async def delete(self, uuid: UUID) -> None:
        await self._client.delete(f"/api/users/{uuid}")
