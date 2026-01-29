from uuid import UUID

from src.domain.entities.user import User
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.mappers.user_mapper import map_remnawave_user


class RemnawaveUserGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def get_by_uuid(self, uuid: UUID) -> User | None:
        try:
            data = await self._client.get(f"/api/users/{uuid}")
            return map_remnawave_user(data)
        except Exception:
            return None

    async def get_by_username(self, username: str) -> User | None:
        try:
            data = await self._client.get(f"/api/users/by-username/{username}")
            return map_remnawave_user(data)
        except Exception:
            return None

    async def get_all(self, offset: int = 0, limit: int = 100) -> list[User]:
        data = await self._client.get("/api/users", params={"offset": offset, "limit": limit})
        users = data.get("users", data) if isinstance(data, dict) else data
        return [map_remnawave_user(u) for u in users]

    async def create(self, username: str, **kwargs) -> User:
        payload = {"username": username, **kwargs}
        data = await self._client.post("/api/users", json=payload)
        return map_remnawave_user(data)

    async def update(self, uuid: UUID, **kwargs) -> User:
        data = await self._client.put(f"/api/users/{uuid}", json=kwargs)
        return map_remnawave_user(data)

    async def delete(self, uuid: UUID) -> None:
        await self._client.delete(f"/api/users/{uuid}")
