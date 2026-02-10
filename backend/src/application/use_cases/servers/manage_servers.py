"""Manage servers use case."""

from typing import Any
from uuid import UUID

from src.domain.entities.server import Server
from src.infrastructure.remnawave.server_gateway import RemnawaveServerGateway


class ManageServersUseCase:
    """Use case for managing server operations."""

    def __init__(self, gateway: RemnawaveServerGateway):
        """Initialize the use case with a server gateway.

        Args:
            gateway: The server gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def get_all(self) -> list[Server]:
        """Get all servers.

        Returns:
            A list of all Server entities
        """
        return await self.gateway.get_all()

    async def get_by_uuid(self, uuid: UUID) -> Server | None:
        """Get a server by UUID.

        Args:
            uuid: The UUID of the server to retrieve

        Returns:
            The Server entity if found, None otherwise
        """
        return await self.gateway.get_by_uuid(uuid)

    async def create(self, name: str, address: str, port: int, **kwargs: Any) -> Server:
        """Create a new server.

        Args:
            name: The server name
            address: The server address
            port: The server port
            **kwargs: Additional server configuration options

        Returns:
            The created Server entity

        Raises:
            Exception: If server creation fails
        """
        return await self.gateway.create(name=name, address=address, port=port, **kwargs)

    async def update(self, uuid: UUID, **kwargs: Any) -> Server:
        """Update a server.

        Args:
            uuid: The UUID of the server to update
            **kwargs: Fields to update (e.g., name, address, port, status)

        Returns:
            The updated Server entity

        Raises:
            Exception: If server update fails or server not found
        """
        return await self.gateway.update(uuid, **kwargs)

    async def delete(self, uuid: UUID) -> None:
        """Delete a server.

        Args:
            uuid: The UUID of the server to delete

        Raises:
            Exception: If server deletion fails or server not found
        """
        await self.gateway.delete(uuid)
