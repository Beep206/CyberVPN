"""Remnawave system recap use case."""

from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveRecapResponse


class SystemRecapUseCase:
    """Fetch aggregated Remnawave recap metrics for operations."""

    def __init__(self, client: RemnawaveClient):
        self.client = client

    async def execute(self) -> dict:
        recap = await self.client.get_validated("/api/system/stats/recap", RemnawaveRecapResponse)
        return {
            "version": recap.version,
            "init_date": recap.init_date.isoformat() if recap.init_date else None,
            "total": {
                "users": recap.total.users,
                "nodes": recap.total.nodes,
                "traffic_bytes": recap.total.traffic,
                "nodes_ram": recap.total.nodes_ram,
                "nodes_cpu_cores": recap.total.nodes_cpu_cores,
                "distinct_countries": recap.total.distinct_countries,
            },
            "this_month": (
                {
                    "users": recap.this_month.users,
                    "traffic_bytes": recap.this_month.traffic,
                }
                if recap.this_month is not None
                else None
            ),
        }
