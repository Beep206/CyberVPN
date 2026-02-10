"""Server statistics use case."""

from src.domain.enums import ServerStatus
from src.infrastructure.remnawave.server_gateway import RemnawaveServerGateway


class ServerStatsUseCase:
    """Use case for retrieving server statistics."""

    def __init__(self, gateway: RemnawaveServerGateway):
        """Initialize the use case with a server gateway.

        Args:
            gateway: The server gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self) -> dict:
        """Execute the server stats use case.

        Returns:
            A dictionary containing server statistics
        """
        servers = await self.gateway.get_all()

        online_count = sum(1 for s in servers if s.status == ServerStatus.ONLINE)
        offline_count = sum(1 for s in servers if s.status == ServerStatus.OFFLINE)
        maintenance_count = sum(1 for s in servers if s.status == ServerStatus.MAINTENANCE)
        warning_count = sum(1 for s in servers if s.status == ServerStatus.WARNING)

        return {
            "total": len(servers),
            "online": online_count,
            "offline": offline_count,
            "maintenance": maintenance_count,
            "warning": warning_count,
            "servers": [
                {
                    "uuid": str(s.uuid),
                    "name": s.name,
                    "address": s.address,
                    "port": s.port,
                    "status": s.status.value if hasattr(s.status, "value") else s.status,
                }
                for s in servers
            ],
        }
