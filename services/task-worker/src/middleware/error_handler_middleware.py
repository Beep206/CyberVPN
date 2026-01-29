"""Error handler middleware with Telegram admin alerts."""

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from src.services.telegram_client import TelegramClient
from src.utils.formatting import worker_error

logger = structlog.get_logger(__name__)

CRITICAL_ERRORS = (ConnectionError, TimeoutError, OSError, RuntimeError)


class ErrorHandlerMiddleware(TaskiqMiddleware):
    """Middleware for handling task errors with admin alerts for critical failures."""

    async def on_error(self, message: TaskiqMessage, result: TaskiqResult, exception: BaseException) -> None:
        """Handle task errors and send admin alerts for critical errors.

        Args:
            message: The task message that failed
            result: The task result containing error information
            exception: The exception that was raised

        """
        task_name = message.task_name
        error_type = type(exception).__name__
        error_msg = str(exception)

        logger.error(
            "task_failed",
            task_name=task_name,
            task_id=message.task_id,
            error_type=error_type,
            error_message=error_msg[:500],
        )

        if isinstance(exception, CRITICAL_ERRORS):
            try:
                alert_text = worker_error(
                    task_name=task_name,
                    error_type=error_type,
                    error_message=error_msg,
                    task_id=message.task_id,
                )
                async with TelegramClient() as tg:
                    await tg.send_admin_alert(alert_text, severity="critical")
            except Exception as alert_err:
                logger.error("failed_to_send_error_alert", error=str(alert_err))
