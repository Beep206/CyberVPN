from uuid import UUID

from src.infrastructure.remnawave.client import RemnawaveClient


class GenerateConfigUseCase:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def execute(self, user_uuid: UUID, client_type: str = "clash") -> dict:
        data = await self._client.get(
            f"/api/users/{user_uuid}/subscription",
            params={"clientType": client_type},
        )
        return {
            "config_string": data.get("config", data.get("subscription", "")),
            "client_type": client_type,
        }
