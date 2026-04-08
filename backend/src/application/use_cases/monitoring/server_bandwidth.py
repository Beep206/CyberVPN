"""Server bandwidth use case."""

from typing import Any

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
        stats = await self.client.get("/api/system/stats")
        recap = await self.client.get("/api/system/stats/recap")

        users = self._as_dict(stats.get("users"))
        online_stats = self._as_dict(stats.get("onlineStats"))
        nodes = self._as_dict(stats.get("nodes"))
        recap_total = self._as_dict(self._as_dict(recap).get("total"))

        return {
            "total_users": int(users.get("totalUsers", 0) or 0),
            "active_users": int(online_stats.get("onlineNow", 0) or 0),
            "total_servers": int(recap_total.get("nodes", 0) or 0),
            "online_servers": int(nodes.get("totalOnline", 0) or 0),
            "total_traffic_bytes": self._parse_int(recap_total.get("traffic"))
            or self._parse_int(nodes.get("totalBytesLifetime")),
        }

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _parse_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
