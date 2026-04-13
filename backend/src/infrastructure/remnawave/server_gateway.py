import logging
from typing import Any
from uuid import UUID

from src.domain.entities.server import Server
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveDeleteResponse, RemnawaveNodeResponse
from src.infrastructure.remnawave.mappers.server_mapper import map_remnawave_server

logger = logging.getLogger(__name__)


class RemnawaveServerGateway:
    def __init__(self, client: RemnawaveClient) -> None:
        self._client = client

    @staticmethod
    def _dump_validated_model(data: Any) -> dict[str, Any]:
        return data.model_dump(by_alias=True, mode="json")

    async def get_by_uuid(self, uuid: UUID) -> Server | None:
        try:
            data = await self._client.get_validated(f"/api/nodes/{uuid}", RemnawaveNodeResponse)
            return map_remnawave_server(self._dump_validated_model(data))
        except Exception as e:
            logger.warning("Failed to fetch server %s from Remnawave: %s", uuid, e)
            return None

    async def get_all(self) -> list[Server]:
        nodes = await self._client.get_collection_validated("/api/nodes", "nodes", RemnawaveNodeResponse)
        return [map_remnawave_server(self._dump_validated_model(node)) for node in nodes]

    async def create(self, name: str, address: str, port: int, **kwargs) -> Server:
        payload = {"name": name, "address": address, "port": port, **kwargs}
        data = await self._client.post_validated("/api/nodes", RemnawaveNodeResponse, json=payload)
        return map_remnawave_server(self._dump_validated_model(data))

    async def update(self, uuid: UUID, **kwargs) -> Server:
        data = await self._client.put_validated(f"/api/nodes/{uuid}", RemnawaveNodeResponse, json=kwargs)
        return map_remnawave_server(self._dump_validated_model(data))

    async def delete(self, uuid: UUID) -> None:
        await self._client.delete_validated(f"/api/nodes/{uuid}", RemnawaveDeleteResponse)
