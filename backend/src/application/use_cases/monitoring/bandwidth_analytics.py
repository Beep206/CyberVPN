"""Bandwidth analytics use case."""

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import (
    RemnawaveBandwidthAnalyticsResponse,
    RemnawaveBandwidthWindowResponse,
)


class BandwidthAnalyticsUseCase:
    """Use case for retrieving bandwidth analytics data."""

    def __init__(self, client: RemnawaveClient):
        """Initialize the use case with a Remnawave client.

        Args:
            client: The Remnawave client for API communication
        """
        self.client = client

    async def execute(self, period: str = "today") -> dict[str, int]:
        """Execute the bandwidth analytics use case.

        Args:
            period: The time period for analytics (e.g., "today", "week", "month")

        Returns:
            A dictionary containing bandwidth analytics data

        Raises:
            Exception: If API request fails
        """
        data = await self.client.get_validated(
            "/api/system/stats/bandwidth",
            RemnawaveBandwidthAnalyticsResponse,
        )
        current_stat = self._period_stat(data, period)

        return {
            "bytes_in": 0,
            "bytes_out": max(0, current_stat.current),
        }

    @staticmethod
    def _period_stat(
        data: RemnawaveBandwidthAnalyticsResponse,
        period: str,
    ) -> RemnawaveBandwidthWindowResponse:
        mapping = {
            "today": data.bandwidth_last_two_days,
            "week": data.bandwidth_last_seven_days,
            "month": data.bandwidth_calendar_month,
        }
        return mapping.get(period, data.bandwidth_last_two_days)
