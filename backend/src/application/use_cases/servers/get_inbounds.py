"""Get inbounds use case."""

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveInboundResponse


class GetInboundsUseCase:
    """Use case for retrieving inbound configurations."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self) -> list[dict]:
        """Execute the get inbounds use case.

        Returns:
            A list of inbound configuration dictionaries

        Raises:
            Exception: If API request fails
        """
        data = await self.client.get_collection_validated("/api/inbounds", "inbounds", RemnawaveInboundResponse)
        return [item.model_dump(by_alias=True, mode="json") for item in data]
