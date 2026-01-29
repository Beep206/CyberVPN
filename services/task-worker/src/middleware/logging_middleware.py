"""Structlog logging middleware for TaskIQ tasks."""

import time

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

logger = structlog.get_logger(__name__)


class LoggingMiddleware(TaskiqMiddleware):
    """Middleware for structured logging of task execution with structlog."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Log task start with structured context.

        Args:
            message: TaskIQ message containing task information

        Returns:
            The same message with start time added to labels
        """
        message.labels["_start_time"] = time.monotonic()
        logger.info(
            "task_started",
            task_name=message.task_name,
            task_id=message.task_id,
            labels=message.labels,
        )
        return message

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        """Log task completion with duration and status.

        Args:
            message: TaskIQ message containing task information
            result: Task execution result
        """
        start = message.labels.get("_start_time", time.monotonic())
        duration = time.monotonic() - start
        log = logger.info if not result.is_err else logger.error
        log(
            "task_completed",
            task_name=message.task_name,
            task_id=message.task_id,
            is_error=result.is_err,
            duration_s=round(duration, 3),
            return_value_type=type(result.return_value).__name__ if not result.is_err else None,
        )

    async def on_error(self, message: TaskiqMessage, result: TaskiqResult, exception: BaseException) -> None:
        """Log task error with exception details.

        Args:
            message: TaskIQ message containing task information
            result: Task execution result
            exception: Exception that occurred during task execution
        """
        logger.exception(
            "task_error",
            task_name=message.task_name,
            task_id=message.task_id,
            error_type=type(exception).__name__,
            error_message=str(exception),
        )
