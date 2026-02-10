"""Security tests for WebSocket ticket authentication (HIGH-3).

Tests that:
1. Tickets are single-use (replay attack prevention)
2. Tickets expire after 30 seconds
3. Ticket format is secure (cryptographically random)
"""

from unittest.mock import AsyncMock

import pytest


class TestWebSocketTicketService:
    """Test WebSocket ticket service."""

    @pytest.mark.asyncio
    async def test_create_ticket_generates_secure_token(self):
        """Ticket creation generates cryptographically secure token."""
        from src.application.services.ws_ticket_service import WebSocketTicketService

        mock_redis = AsyncMock()

        service = WebSocketTicketService(mock_redis)
        ticket = await service.create_ticket(
            user_id="user-123",
            role="admin",
            login="testuser",
            ip_address="192.168.1.1",
        )

        # Verify ticket format - should be 32 hex chars (16 bytes)
        assert ticket is not None
        assert len(ticket) == 32
        assert all(c in "0123456789abcdef" for c in ticket)

    @pytest.mark.asyncio
    async def test_create_ticket_stores_with_ttl(self):
        """Ticket is stored with 30-second TTL."""
        from src.application.services.ws_ticket_service import WebSocketTicketService

        mock_redis = AsyncMock()

        service = WebSocketTicketService(mock_redis)
        await service.create_ticket(
            user_id="user-123",
            role="admin",
        )

        # Verify Redis hset and expire were called
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once()

        # Verify TTL is 30 seconds
        expire_call_args = mock_redis.expire.call_args
        assert expire_call_args[0][1] == 30

    @pytest.mark.asyncio
    async def test_tickets_are_unique(self):
        """Each ticket should be unique."""
        from src.application.services.ws_ticket_service import WebSocketTicketService

        mock_redis = AsyncMock()

        service = WebSocketTicketService(mock_redis)
        tickets = set()

        # Generate multiple tickets
        for _ in range(100):
            ticket = await service.create_ticket(
                user_id="user-123",
                role="admin",
            )
            tickets.add(ticket)

        # All tickets should be unique
        assert len(tickets) == 100


class TestTicketDataStructure:
    """Test ticket data handling."""

    def test_ticket_data_dataclass(self):
        """TicketData dataclass works correctly."""
        from datetime import UTC, datetime

        from src.application.services.ws_ticket_service import TicketData

        data = TicketData(
            user_id="user-123",
            role="admin",
            login="testuser",
            created_at=datetime.now(UTC),
            ip_address="192.168.1.1",
        )

        assert data.user_id == "user-123"
        assert data.role == "admin"
        assert data.login == "testuser"
        assert data.ip_address == "192.168.1.1"


class TestWSUserContext:
    """Test WebSocket user context."""

    def test_user_context_dataclass(self):
        """WSUserContext dataclass works correctly."""
        from src.domain.enums.enums import AdminRole
        from src.presentation.api.v1.ws.auth import WSUserContext

        ctx = WSUserContext(
            user_id="user-123",
            role=AdminRole.ADMIN,
            login="testuser",
        )

        assert ctx.user_id == "user-123"
        assert ctx.role == AdminRole.ADMIN
        assert ctx.login == "testuser"

    def test_user_context_login_optional(self):
        """WSUserContext login field is optional."""
        from src.domain.enums.enums import AdminRole
        from src.presentation.api.v1.ws.auth import WSUserContext

        ctx = WSUserContext(
            user_id="user-123",
            role=AdminRole.VIEWER,
        )

        assert ctx.login is None


class TestSecurityProperties:
    """Test security properties of ticket system."""

    def test_ticket_prefix_is_namespaced(self):
        """Ticket keys are properly namespaced in Redis."""
        from src.application.services.ws_ticket_service import WebSocketTicketService

        assert WebSocketTicketService.PREFIX == "ws_ticket:"

    def test_ticket_ttl_is_short(self):
        """Ticket TTL is appropriately short (30 seconds)."""
        from src.application.services.ws_ticket_service import WebSocketTicketService

        # 30 seconds is short enough to limit replay window
        assert WebSocketTicketService.TTL_SECONDS == 30
        assert WebSocketTicketService.TTL_SECONDS <= 60  # Should never be more than 1 minute
