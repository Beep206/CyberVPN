"""Bandwidth analytics use case."""

from src.infrastructure.remnawave.client import RemnawaveClient


class BandwidthAnalyticsUseCase:
    """Use case for retrieving bandwidth analytics data."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self, period: str = "today") -> dict:
        """Execute the bandwidth analytics use case.

        Args:
            period: The time period for analytics (e.g., "today", "week", "month")

        Returns:
            A dictionary containing bandwidth analytics data

        Raises:
            Exception: If API request fails
        """
        endpoint = f"/api/analytics/bandwidth?period={period}"
        data = await self.client.get(endpoint)

        if isinstance(data, dict):
            return data

        # If API returns raw data, structure it
        return {
            "period": period,
            "data": data if data else [],
            "total_usage": 0,
            "peak_usage": 0,
        }
