"""WebSocket ticket service (HIGH-3).

Implements ticket-based WebSocket authentication:
1. Client requests single-use ticket via POST /api/v1/ws/ticket
2. Ticket is UUID, stored in Redis with 30-second TTL
3. WebSocket connects with ?ticket=<uuid> instead of JWT
4. Ticket exchanged for user context on connection
5. Ticket invalidated after use (single-use)

This prevents JWT tokens from appearing in WebSocket URLs (which get logged).
"""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class TicketData:
    """Data stored with a WebSocket ticket."""

    user_id: str
    role: str
    login: str | None
    created_at: datetime
    ip_address: str | None = None


class WebSocketTicketService:
    """Service for managing WebSocket authentication tickets.

    Tickets are single-use, short-lived (30 seconds), and stored in Redis.
    """

    PREFIX = "ws_ticket:"
    TTL_SECONDS = 30  # Tickets expire after 30 seconds

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def create_ticket(
        self,
        user_id: str,
        role: str,
        login: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Create a new WebSocket authentication ticket.

        Args:
            user_id: The authenticated user's ID
            role: The user's role
            login: The user's login (optional)
            ip_address: Client IP for validation (optional)

        Returns:
            The ticket UUID string
        """
        # Generate cryptographically secure ticket ID
        ticket_id = secrets.token_hex(16)

        key = f"{self.PREFIX}{ticket_id}"
        data = {
            "user_id": user_id,
            "role": role,
            "login": login or "",
            "created_at": datetime.now(UTC).isoformat(),
            "ip_address": ip_address or "",
        }

        # Store with short TTL
        await self._redis.hset(key, mapping=data)  # type: ignore[arg-type]
        await self._redis.expire(key, self.TTL_SECONDS)  # type: ignore[misc]

        logger.info(
            "WebSocket ticket created",
            extra={"user_id": user_id, "ticket_id": ticket_id[:8] + "..."},
        )

        return ticket_id

    async def validate_and_consume(
        self,
        ticket_id: str,
        client_ip: str | None = None,
    ) -> TicketData | None:
        """Validate and consume a WebSocket ticket.

        This is an atomic operation - the ticket is deleted immediately
        to prevent reuse (single-use).

        Args:
            ticket_id: The ticket UUID to validate
            client_ip: Client IP for validation (optional)

        Returns:
            TicketData if valid, None otherwise
        """
        key = f"{self.PREFIX}{ticket_id}"

        # Atomically get and delete the ticket using MULTI/EXEC
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hgetall(key)
            pipe.delete(key)
            results = await pipe.execute()

        data = results[0]
        if not data:
            logger.warning(
                "Invalid or expired WebSocket ticket",
                extra={"ticket_id": ticket_id[:8] + "..." if len(ticket_id) >= 8 else ticket_id},
            )
            return None

        # Decode bytes to strings if necessary
        if isinstance(data, dict):
            decoded = {}
            for k, v in data.items():
                key_str = k.decode() if isinstance(k, bytes) else k
                val_str = v.decode() if isinstance(v, bytes) else v
                decoded[key_str] = val_str
            data = decoded

        # Optional: validate IP address matches
        stored_ip = data.get("ip_address", "")
        if stored_ip and client_ip and stored_ip != client_ip:
            logger.warning(
                "WebSocket ticket IP mismatch",
                extra={
                    "ticket_id": ticket_id[:8] + "...",
                    "stored_ip": stored_ip,
                    "client_ip": client_ip,
                },
            )
            # Still allow for now (IPs can change due to NAT, proxies)
            # Consider making this configurable

        logger.info(
            "WebSocket ticket validated and consumed",
            extra={"user_id": data.get("user_id"), "ticket_id": ticket_id[:8] + "..."},
        )

        return TicketData(
            user_id=data.get("user_id", ""),
            role=data.get("role", "viewer"),
            login=data.get("login") or None,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
            ip_address=data.get("ip_address") or None,
        )

    async def revoke_ticket(self, ticket_id: str) -> bool:
        """Revoke a ticket before it's used.

        Args:
            ticket_id: The ticket to revoke

        Returns:
            True if ticket was revoked, False if not found
        """
        key = f"{self.PREFIX}{ticket_id}"
        deleted = await self._redis.delete(key)
        return deleted > 0
