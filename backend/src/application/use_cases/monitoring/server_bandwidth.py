"""Server bandwidth use case."""
from src.infrastructure.remnawave.client import RemnawaveClient


class ServerBandwidthUseCase:
    """Use case for retrieving server bandwidth data."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self) -> dict:
        """Execute the server bandwidth use case.

        Returns:
            A dictionary containing bandwidth data from Remnawave

        Raises:
            Exception: If API request fails
        """
        data = await self.client.get("/api/monitoring/bandwidth")
        if isinstance(data, dict):
            return data
        return {"bandwidth": data if data else []}
