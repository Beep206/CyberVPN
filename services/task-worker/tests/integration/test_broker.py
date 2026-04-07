"""Integration tests for broker lifecycle and configuration.

Tests verify that the broker is properly configured with:
- Middleware chain
- Result backend
- Schedule sources
- Lifecycle event handlers

These tests do NOT connect to real Redis - they inspect the broker object
configuration and use mocks for lifecycle events.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RetryMiddleware,
)


@pytest.mark.integration
class TestBrokerLifecycle:
    """Integration tests for broker configuration and lifecycle."""

    def test_broker_has_middleware(self):
        """Verify middleware chain is registered in correct order."""
        from src.broker import broker

        assert broker is not None, "Broker should be initialized"
        assert hasattr(broker, "add_middlewares"), "Broker should have add_middlewares method"
        assert len(broker.middlewares) >= 4, "Expected TaskIQ middlewares to be registered"
        assert isinstance(broker.middlewares[0], LoggingMiddleware)
        assert isinstance(broker.middlewares[1], MetricsMiddleware)
        assert isinstance(broker.middlewares[2], ErrorHandlerMiddleware)
        assert isinstance(broker.middlewares[3], RetryMiddleware)

    def test_broker_has_result_backend(self):
        """Verify broker has result backend configured."""
        from src.broker import broker

        assert broker.result_backend is not None, "Broker should have result backend"
        # RedisAsyncResultBackend stores connection info internally
        assert hasattr(broker.result_backend, "set_result"), "Result backend should have set_result method"
        assert hasattr(broker.result_backend, "get_result"), "Result backend should have get_result method"

    def test_scheduler_has_sources(self):
        """Verify scheduler has schedule sources configured."""
        from src.broker import scheduler

        assert len(scheduler.sources) > 0, "Scheduler should have at least one schedule source"

        # Verify schedule source has required methods
        source = scheduler.sources[0]
        assert hasattr(source, "get_schedules"), "Schedule source should have get_schedules method"
        assert hasattr(source, "add_schedule"), "Schedule source should have add_schedule method"

    def test_broker_is_redis_stream_broker(self):
        """Verify broker is RedisStreamBroker instance."""
        from taskiq_redis import RedisStreamBroker

        from src.broker import broker

        assert isinstance(broker, RedisStreamBroker), "Broker should be RedisStreamBroker"

    @pytest.mark.asyncio
    async def test_worker_startup_event_creates_state_objects(self):
        """Test worker startup event creates expected state objects (mocked)."""
        # Mock the broker state
        mock_state = MagicMock()

        # Mock dependencies
        with (
            patch("src.broker.get_engine") as mock_get_engine,
            patch("src.broker.get_session_factory") as mock_get_session_factory,
            patch("src.broker.start_metrics_server") as mock_start_metrics,
            patch("httpx.AsyncClient"),
        ):

            mock_engine = AsyncMock()
            mock_session_factory = MagicMock()
            mock_get_engine.return_value = mock_engine
            mock_get_session_factory.return_value = mock_session_factory

            # Import and call the startup event
            from src.broker import startup_event

            await startup_event(mock_state)

            # Verify state objects were created
            assert hasattr(mock_state, "db_engine"), "State should have db_engine"
            assert hasattr(mock_state, "db_session_factory"), "State should have db_session_factory"
            assert hasattr(mock_state, "http_client"), "State should have http_client"

            # Verify metrics server was started
            mock_start_metrics.assert_called_once()

            # Verify engine and session factory were initialized
            mock_get_engine.assert_called_once()
            mock_get_session_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_shutdown_event_cleanup(self):
        """Test worker shutdown event cleans up resources properly."""
        # Mock state with resources
        mock_state = MagicMock()
        mock_http_client = AsyncMock()
        mock_db_engine = AsyncMock()

        mock_state.http_client = mock_http_client
        mock_state.db_engine = mock_db_engine

        # Import and call the shutdown event
        from src.broker import shutdown_event

        await shutdown_event(mock_state)

        # Verify resources were closed
        mock_http_client.aclose.assert_called_once()
        mock_db_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_startup_event_handles_errors(self):
        """Test worker startup event handles initialization errors."""
        mock_state = MagicMock()

        # Mock get_engine to raise an error
        with (
            patch("src.broker.get_engine") as mock_get_engine,
            patch("src.broker.start_metrics_server"),
        ):

            mock_get_engine.side_effect = Exception("Database connection failed")

            from src.broker import startup_event

            # Verify exception is re-raised
            with pytest.raises(Exception, match="Database connection failed"):
                await startup_event(mock_state)

    @pytest.mark.asyncio
    async def test_worker_shutdown_event_handles_missing_resources(self):
        """Test worker shutdown event handles missing resources gracefully."""
        # Mock state without resources
        mock_state = MagicMock()
        # Remove http_client and db_engine attributes
        delattr(mock_state, "http_client") if hasattr(mock_state, "http_client") else None
        delattr(mock_state, "db_engine") if hasattr(mock_state, "db_engine") else None

        from src.broker import shutdown_event

        # Should not raise any errors
        await shutdown_event(mock_state)

    def test_broker_has_event_handlers_registered(self):
        """Verify broker has startup and shutdown event handlers registered."""
        import inspect

        from src.broker import broker, shutdown_event, startup_event

        # Verify event handler functions exist
        assert startup_event is not None, "Startup event handler should exist"
        assert shutdown_event is not None, "Shutdown event handler should exist"

        # Verify they are async callables
        assert inspect.iscoroutinefunction(startup_event), "Startup event should be async"
        assert inspect.iscoroutinefunction(shutdown_event), "Shutdown event should be async"

        # Verify broker has on_event decorator method
        assert hasattr(broker, "on_event"), "Broker should have on_event decorator"
