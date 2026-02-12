import logging
from uuid import UUID

from src.domain.entities.server import Server
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.mappers.server_mapper import map_remnawave_server

logger = logging.getLogger(__name__)


class RemnawaveServerGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    async def get_by_uuid(self, uuid: UUID) -> Server | None:
        try:
            data = await self._client.get(f"/api/nodes/{uuid}")
            return map_remnawave_server(data)
        except Exception as e:
            logger.warning("Failed to fetch server %s from Remnawave: %s", uuid, e)
            return None

    async def get_all(self) -> list[Server]:
        data = await self._client.get("/api/nodes")
        nodes = data.get("nodes", data) if isinstance(data, dict) else data
        return [map_remnawave_server(n) for n in nodes]

    async def create(self, name: str, address: str, port: int, **kwargs) -> Server:
        payload = {"name": name, "address": address, "port": port, **kwargs}
        data = await self._client.post("/api/nodes", json=payload)
        return map_remnawave_server(data)

    async def update(self, uuid: UUID, **kwargs) -> Server:
        data = await self._client.put(f"/api/nodes/{uuid}", json=kwargs)
        return map_remnawave_server(data)

    async def delete(self, uuid: UUID) -> None:
        await self._client.delete(f"/api/nodes/{uuid}")
