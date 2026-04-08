"""Bandwidth analytics use case."""

from typing import Any

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
        data = await self.client.get("/api/system/stats/bandwidth")
        key = self._period_key(period)
        current_stat = self._as_dict(data.get(key))
        current_total = self._parse_int(current_stat.get("current"))

        return {
            "bytes_in": 0,
            "bytes_out": current_total,
        }

    @staticmethod
    def _period_key(period: str) -> str:
        mapping = {
            "today": "bandwidthLastTwoDays",
            "week": "bandwidthLastSevenDays",
            "month": "bandwidthCalendarMonth",
        }
        return mapping.get(period, "bandwidthLastTwoDays")

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _parse_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
