import logging
from typing import Any
from uuid import UUID

from src.domain.entities.server import Server
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveTransportError,
)
from src.infrastructure.remnawave.contracts import RemnawaveDeleteResponse, RemnawaveNodeResponse
from src.infrastructure.remnawave.mappers.server_mapper import map_remnawave_server

logger = logging.getLogger(__name__)


class RemnawaveNodeCreateSafetyDisabled(RuntimeError):
    """Node create is disabled until ambiguous outcomes have durable settlement."""

    error_code = "remnawave_node_create_safety_disabled"


class RemnawaveNodeMutationAcceptedPending(RuntimeError):
    """A node mutation may have been accepted but has no exact postcondition yet."""

    error_code = "remnawave_node_mutation_accepted_pending"

    def __init__(self, *, operation: str, node_uuid: UUID) -> None:
        self.operation = operation
        self.node_uuid = node_uuid
        super().__init__(f"Remnawave node {operation} requires authoritative reconciliation")


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
        except RemnawaveHTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def get_all(self) -> list[Server]:
        nodes = await self._client.get_collection_validated("/api/nodes", "nodes", RemnawaveNodeResponse)
        return [map_remnawave_server(self._dump_validated_model(node)) for node in nodes]

    async def create(self, name: str, address: str, port: int, **kwargs) -> Server | None:
        # Remnawave does not accept a client-supplied immutable node id or an
        # idempotency key. A timeout/empty 202 cannot be reconciled by mutable
        # name/address without risking a wrong binding or a duplicate node.
        # Keep this fail-closed until a durable create-attempt settlement flow
        # is available.
        raise RemnawaveNodeCreateSafetyDisabled

    async def update(self, uuid: UUID, **kwargs) -> Server | None:
        payload = {"uuid": str(uuid), **kwargs}
        try:
            data = await self._client.patch_validated("/api/nodes", RemnawaveNodeResponse, json=payload)
        except RemnawaveTransportError:
            data = None

        if data is None:
            # A single authoritative read of the immutable target is safe and
            # avoids retrying an already-applied mutation.
            server = await self.get_by_uuid(uuid)
            if server is None:
                raise RemnawaveNodeMutationAcceptedPending(operation="update", node_uuid=uuid)
        else:
            server = map_remnawave_server(self._dump_validated_model(data))

        self._require_update_postcondition(server, node_uuid=uuid, payload=kwargs)
        return server

    async def delete(self, uuid: UUID) -> None:
        try:
            await self._client.delete_validated(f"/api/nodes/{uuid}", RemnawaveDeleteResponse)
        except RemnawaveTransportError:
            # The request may have reached the provider. Do not replay it;
            # settle against the immutable node id below.
            pass
        except RemnawaveHTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise

        if await self.get_by_uuid(uuid) is not None:
            raise RemnawaveNodeMutationAcceptedPending(operation="delete", node_uuid=uuid)

    @staticmethod
    def _require_update_postcondition(server: Server, *, node_uuid: UUID, payload: dict[str, Any]) -> None:
        observable = {
            "name": server.name,
            "address": server.address,
            "port": server.port,
        }
        if server.uuid != node_uuid or set(payload) - set(observable):
            raise RemnawaveNodeMutationAcceptedPending(operation="update", node_uuid=node_uuid)
        if any(observable[field] != expected for field, expected in payload.items()):
            raise RemnawaveNodeMutationAcceptedPending(operation="update", node_uuid=node_uuid)
