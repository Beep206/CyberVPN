"""Tests for TaskIQ middleware modules."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from taskiq import TaskiqMessage, TaskiqResult


@pytest.mark.asyncio
async def test_logging_middleware_pre_execute():
    """Test logging middleware logs task start."""
    from src.middleware.logging_middleware import LoggingMiddleware

    middleware = LoggingMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )

    result = await middleware.pre_execute(message)

    assert "_start_time" in result.labels
    assert result.task_id == "test-123"


@pytest.mark.asyncio
async def test_logging_middleware_post_execute_success():
    """Test logging middleware logs successful completion."""
    from src.middleware.logging_middleware import LoggingMiddleware

    middleware = LoggingMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={"_start_time": time.monotonic()},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=False, return_value={"status": "success"}, execution_time=0.5)

    await middleware.post_execute(message, result)

    # Should complete without error


@pytest.mark.asyncio
async def test_logging_middleware_on_error():
    """Test logging middleware logs errors."""
    from src.middleware.logging_middleware import LoggingMiddleware

    middleware = LoggingMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, error=ValueError("Test error"), execution_time=0.1)
    exception = ValueError("Test error")

    await middleware.on_error(message, result, exception)

    # Should log exception without raising


@pytest.mark.asyncio
async def test_metrics_middleware_pre_execute():
    """Test metrics middleware increments in_progress gauge."""
    from src.middleware.metrics_middleware import MetricsMiddleware, TASKS_IN_PROGRESS

    middleware = MetricsMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )

    with patch.object(TASKS_IN_PROGRESS, "labels") as mock_labels:
        mock_gauge = MagicMock()
        mock_labels.return_value = mock_gauge

        result = await middleware.pre_execute(message)

        assert "_metrics_start" in result.labels
        mock_gauge.inc.assert_called_once()


@pytest.mark.asyncio
async def test_metrics_middleware_post_execute():
    """Test metrics middleware records completion metrics."""
    from src.middleware.metrics_middleware import MetricsMiddleware, TASK_TOTAL, TASK_DURATION, TASKS_IN_PROGRESS

    middleware = MetricsMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={"_metrics_start": time.monotonic()},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=False, return_value={"status": "success"}, execution_time=0.5)

    with patch.object(TASKS_IN_PROGRESS, "labels") as mock_in_progress, \
         patch.object(TASK_DURATION, "labels") as mock_duration, \
         patch.object(TASK_TOTAL, "labels") as mock_total:

        mock_gauge = MagicMock()
        mock_histogram = MagicMock()
        mock_counter = MagicMock()

        mock_in_progress.return_value = mock_gauge
        mock_duration.return_value = mock_histogram
        mock_total.return_value = mock_counter

        await middleware.post_execute(message, result)

        mock_gauge.dec.assert_called_once()
        mock_histogram.observe.assert_called_once()
        mock_counter.inc.assert_called_once()


@pytest.mark.asyncio
async def test_metrics_middleware_on_error():
    """Test metrics middleware records error metrics."""
    from src.middleware.metrics_middleware import MetricsMiddleware, TASK_ERRORS

    middleware = MetricsMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = ValueError("Test error")

    with patch.object(TASK_ERRORS, "labels") as mock_labels:
        mock_counter = MagicMock()
        mock_labels.return_value = mock_counter

        await middleware.on_error(message, result, exception)

        mock_counter.inc.assert_called_once()


@pytest.mark.asyncio
async def test_error_handler_middleware_critical_error():
    """Test error handler sends alerts for critical errors."""
    from src.middleware.error_handler_middleware import ErrorHandlerMiddleware

    middleware = ErrorHandlerMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = ConnectionError("Database connection failed")

    with patch("src.middleware.error_handler_middleware.TelegramClient") as mock_tg_cls:
        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        await middleware.on_error(message, result, exception)

        mock_tg.send_admin_alert.assert_called_once()


@pytest.mark.asyncio
async def test_error_handler_middleware_non_critical_error():
    """Test error handler does not alert for non-critical errors."""
    from src.middleware.error_handler_middleware import ErrorHandlerMiddleware

    middleware = ErrorHandlerMiddleware()
    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = ValueError("Invalid input")

    with patch("src.middleware.error_handler_middleware.TelegramClient") as mock_tg_cls:
        mock_tg = AsyncMock()
        mock_tg_cls.return_value.__aenter__.return_value = mock_tg

        await middleware.on_error(message, result, exception)

        mock_tg.send_admin_alert.assert_not_called()


@pytest.mark.asyncio
async def test_retry_middleware_retry_scheduled():
    """Test retry middleware schedules retry on failure."""
    from src.middleware.retry_middleware import RetryMiddleware

    middleware = RetryMiddleware()
    middleware.broker = MagicMock()

    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={"queue": "default", "_retry_count": "0"},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = Exception("Temporary failure")

    with patch("src.middleware.retry_middleware.RETRY_POLICIES", {"default": {"max_retries": 3, "delays": [1, 2, 4]}}), \
         patch("src.middleware.retry_middleware.asyncio.sleep") as mock_sleep, \
         patch("src.middleware.retry_middleware.AsyncKicker") as mock_kicker_cls:

        mock_kicker = AsyncMock()
        mock_kicker_cls.return_value = mock_kicker

        await middleware.on_error(message, result, exception)

        mock_sleep.assert_called_once_with(1)
        mock_kicker.kiq.assert_called_once()


@pytest.mark.asyncio
async def test_retry_middleware_max_retries_exceeded():
    """Test retry middleware stops after max retries."""
    from src.middleware.retry_middleware import RetryMiddleware

    middleware = RetryMiddleware()
    middleware.broker = MagicMock()

    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={"queue": "default", "_retry_count": "3"},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = Exception("Permanent failure")

    with patch("src.middleware.retry_middleware.RETRY_POLICIES", {"default": {"max_retries": 3, "delays": [1, 2, 4]}}), \
         patch("src.middleware.retry_middleware.AsyncKicker") as mock_kicker_cls:

        mock_kicker = AsyncMock()
        mock_kicker_cls.return_value = mock_kicker

        await middleware.on_error(message, result, exception)

        mock_kicker.kiq.assert_not_called()


@pytest.mark.asyncio
async def test_retry_middleware_no_policy():
    """Test retry middleware skips retry when no policy exists."""
    from src.middleware.retry_middleware import RetryMiddleware

    middleware = RetryMiddleware()
    middleware.broker = MagicMock()

    message = TaskiqMessage(
        task_id="test-123",
        task_name="test_task",
        labels={"queue": "unknown_queue"},
        args=[],
        kwargs={},
    )
    result = TaskiqResult(is_err=True, return_value=None, execution_time=0.1)
    exception = Exception("Failure")

    with patch("src.middleware.retry_middleware.RETRY_POLICIES", {}), \
         patch("src.middleware.retry_middleware.AsyncKicker") as mock_kicker_cls:

        mock_kicker = AsyncMock()
        mock_kicker_cls.return_value = mock_kicker

        await middleware.on_error(message, result, exception)

        mock_kicker.kiq.assert_not_called()
