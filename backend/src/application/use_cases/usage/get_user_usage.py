"""Use case for fetching user VPN usage statistics from Remnawave."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.domain.entities.user import User
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = logging.getLogger(__name__)


class UsageData:
    """DTO for user usage statistics."""

    def __init__(
        self,
        bandwidth_used_bytes: int,
        bandwidth_limit_bytes: int,
        connections_active: int,
        connections_limit: int,
        period_start: datetime,
        period_end: datetime,
        last_connection_at: datetime | None,
    ):
        self.bandwidth_used_bytes = bandwidth_used_bytes
        self.bandwidth_limit_bytes = bandwidth_limit_bytes
        self.connections_active = connections_active
        self.connections_limit = connections_limit
        self.period_start = period_start
        self.period_end = period_end
        self.last_connection_at = last_connection_at


class GetUserUsageUseCase:
    """Use case for retrieving VPN usage statistics for a user."""

    def __init__(self, user_gateway: RemnawaveUserGateway):
        """Initialize with user gateway.

        Args:
            user_gateway: Gateway for interacting with Remnawave user API
        """
        self.user_gateway = user_gateway

    async def execute(self, user_uuid: UUID) -> UsageData:
        """Fetch VPN usage statistics for a user from Remnawave.

        Args:
            user_uuid: UUID of the user in Remnawave

        Returns:
            UsageData with bandwidth, connections, and period information

        Raises:
            ValueError: If user not found in Remnawave
        """
        # Fetch user from Remnawave
        user = await self.user_gateway.get_by_uuid(user_uuid)
        if not user:
            logger.warning("User not found in Remnawave", extra={"user_uuid": str(user_uuid)})
            raise ValueError(f"User {user_uuid} not found in VPN backend")

        return self._map_user_to_usage(user)

    def _map_user_to_usage(self, user: User) -> UsageData:
        """Map Remnawave User entity to UsageData DTO.

        Args:
            user: Domain User entity from Remnawave

        Returns:
            UsageData with all fields populated
        """
        # Bandwidth data (in bytes)
        bandwidth_used = user.used_traffic_bytes or 0
        bandwidth_limit = user.traffic_limit_bytes or 0

        # Connection limits (Remnawave tracks this via hwid_device_limit)
        connections_limit = user.hwid_device_limit or 5  # Default to 5 if not set
        connections_active = 1 if user.online_at else 0  # User is online if online_at is recent

        # Billing period calculation
        period_start, period_end = self._calculate_billing_period(user)

        # Last connection timestamp
        last_connection_at = user.online_at

        return UsageData(
            bandwidth_used_bytes=bandwidth_used,
            bandwidth_limit_bytes=bandwidth_limit,
            connections_active=connections_active,
            connections_limit=connections_limit,
            period_start=period_start,
            period_end=period_end,
            last_connection_at=last_connection_at,
        )

    def _calculate_billing_period(self, user: User) -> tuple[datetime, datetime]:
        """Calculate billing period start and end dates.

        Args:
            user: Domain User entity

        Returns:
            Tuple of (period_start, period_end) datetimes
        """
        now = datetime.now(UTC)

        # Use last_traffic_reset_at if available, otherwise use start of current month
        if user.last_traffic_reset_at:
            period_start = user.last_traffic_reset_at
            # Period end is when user expires or next month, whichever comes first
            next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = user.expire_at if user.expire_at and user.expire_at < next_month else next_month
        else:
            # Default to current calendar month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            period_end = user.expire_at if user.expire_at and user.expire_at < next_month else next_month

        return period_start, period_end
