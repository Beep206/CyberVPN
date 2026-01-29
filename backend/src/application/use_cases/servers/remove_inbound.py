"""Remove inbound use case."""
from uuid import UUID

from src.infrastructure.remnawave.client import RemnawaveClient


class RemoveInboundUseCase:
    """Use case for removing an inbound configuration."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self, uuid: UUID) -> None:
        """Execute the remove inbound use case.

        Args:
            uuid: The UUID of the inbound to remove

        Raises:
            Exception: If API request fails or inbound not found
        """
        await self.client.delete(f"/api/inbounds/{uuid}")
