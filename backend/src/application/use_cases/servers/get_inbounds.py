"""Get inbounds use case."""

from src.infrastructure.remnawave.client import RemnawaveClient


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
        data = await self.client.get("/api/inbounds")
        if isinstance(data, list):
            return data
        return data.get("inbounds", [])
