"""Server bandwidth use case."""

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import (
    RemnawaveRawSystemStatsResponse,
    RemnawaveRecapResponse,
)


class ServerBandwidthUseCase:
    """Use case for retrieving server bandwidth data."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self) -> dict[str, int]:
        """Execute the server bandwidth use case.

        Returns:
            A dictionary containing bandwidth data from Remnawave

        Raises:
            Exception: If API request fails
        """
        stats = await self.client.get_validated("/api/system/stats", RemnawaveRawSystemStatsResponse)
        recap = await self.client.get_validated("/api/system/stats/recap", RemnawaveRecapResponse)
        recap_total = recap.total

        return {
            "total_users": max(0, stats.users.total_users),
            "active_users": max(0, stats.online_stats.online_now),
            "total_servers": max(0, recap_total.nodes),
            "online_servers": max(0, stats.nodes.total_online),
            "total_traffic_bytes": max(0, recap_total.traffic) or max(0, stats.nodes.total_bytes_lifetime),
        }
