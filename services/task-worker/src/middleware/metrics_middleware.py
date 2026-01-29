"""Prometheus metrics middleware for TaskIQ tasks."""

import time

from prometheus_client import Counter, Gauge, Histogram
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from src.services.redis_client import get_redis_client

# Task execution metrics
TASK_TOTAL = Counter(
    "taskiq_tasks_total",
    "Total tasks processed",
    ["task_name", "status"],
)
TASK_DURATION = Histogram(
    "taskiq_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)
TASKS_IN_PROGRESS = Gauge(
    "taskiq_tasks_in_progress",
    "Number of tasks currently being executed",
    ["task_name"],
)
TASK_ERRORS = Counter(
    "taskiq_task_errors_total",
    "Total task errors by error type",
    ["task_name", "error_type"],
)

ERROR_RATE_WINDOW_SECONDS = 900
ERROR_RATE_TOTAL_KEY = "cybervpn:metrics:task_total"
ERROR_RATE_ERRORS_KEY = "cybervpn:metrics:task_errors"
ERROR_RATE_KEY = "cybervpn:metrics:error_rate"


class MetricsMiddleware(TaskiqMiddleware):
    """Middleware for Prometheus metrics collection during task execution."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Record task start metrics.

        Args:
            message: TaskIQ message containing task information

        Returns:
            The same message with metrics start time added to labels
        """
        message.labels["_metrics_start"] = time.monotonic()
        TASKS_IN_PROGRESS.labels(task_name=message.task_name).inc()
        return message

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        """Record task completion metrics including duration and status.

        Args:
            message: TaskIQ message containing task information
            result: Task execution result
        """
        start = message.labels.get("_metrics_start", time.monotonic())
        duration = time.monotonic() - start
        task_name = message.task_name

        TASKS_IN_PROGRESS.labels(task_name=task_name).dec()
        TASK_DURATION.labels(task_name=task_name).observe(duration)
        status = "error" if result.is_err else "success"
        TASK_TOTAL.labels(task_name=task_name, status=status).inc()

        redis = None
        try:
            redis = get_redis_client()
            total = await redis.incr(ERROR_RATE_TOTAL_KEY)
            await redis.expire(ERROR_RATE_TOTAL_KEY, ERROR_RATE_WINDOW_SECONDS)
            errors_raw = await redis.get(ERROR_RATE_ERRORS_KEY)
            errors = int(errors_raw or 0)
            rate = (errors / total * 100) if total else 0.0
            await redis.set(ERROR_RATE_KEY, f"{rate:.4f}", ex=ERROR_RATE_WINDOW_SECONDS)
        except Exception:
            pass
        finally:
            if redis:
                await redis.aclose()

    async def on_error(self, message: TaskiqMessage, result: TaskiqResult, exception: BaseException) -> None:
        """Record error metrics for failed tasks.

        Args:
            message: TaskIQ message containing task information
            result: Task execution result
            exception: Exception that occurred during task execution
        """
        TASK_ERRORS.labels(
            task_name=message.task_name,
            error_type=type(exception).__name__,
        ).inc()

        redis = None
        try:
            redis = get_redis_client()
            errors = await redis.incr(ERROR_RATE_ERRORS_KEY)
            await redis.expire(ERROR_RATE_ERRORS_KEY, ERROR_RATE_WINDOW_SECONDS)
            total_raw = await redis.get(ERROR_RATE_TOTAL_KEY)
            total = int(total_raw or 0)
            rate = (errors / total * 100) if total else 0.0
            await redis.set(ERROR_RATE_KEY, f"{rate:.4f}", ex=ERROR_RATE_WINDOW_SECONDS)
        except Exception:
            pass
        finally:
            if redis:
                await redis.aclose()
