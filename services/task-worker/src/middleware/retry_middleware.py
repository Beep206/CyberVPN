"""Custom retry middleware with per-domain policies and exponential backoff.

Uses AsyncKicker to re-queue failed tasks via the broker with configurable
retry delays per task queue/domain. Falls back to SimpleRetryMiddleware
pattern from TaskIQ but adds domain-specific delay scheduling.
"""

import asyncio

import structlog
from taskiq import NoResultError, TaskiqMessage, TaskiqMiddleware, TaskiqResult
from taskiq.kicker import AsyncKicker

from src.utils.constants import RETRY_POLICIES

logger = structlog.get_logger(__name__)


class RetryMiddleware(TaskiqMiddleware):
    """Middleware implementing per-domain retry policies with backoff delays.

    Looks up retry policy by the task's ``queue`` label. If a policy exists
    and the retry limit has not been exceeded, sleeps for the configured delay
    then re-queues the task via ``AsyncKicker.kiq()``.

    When a task is retried, ``TaskiqResult.error`` is set to ``NoResultError``
    so the result backend does not store a partial/error result for the
    intermediate attempt.
    """

    def _get_policy(self, message: TaskiqMessage) -> dict[str, int | str | list[int]] | None:
        """Resolve retry policy from the task's queue label."""
        policy_name = message.labels.get("retry_policy")
        if policy_name:
            return RETRY_POLICIES.get(policy_name)
        queue = message.labels.get("queue", "")
        return RETRY_POLICIES.get(queue)

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult,
        exception: BaseException,
    ) -> None:
        """Handle task failure: apply domain retry policy and re-queue if allowed."""
        # Never retry internal no-result sentinel
        if isinstance(exception, NoResultError):
            return

        policy = self._get_policy(message)
        if not policy:
            return

        current_retry = int(message.labels.get("_retry_count", 0))
        max_retries: int = policy["max_retries"]

        if current_retry >= max_retries:
            logger.warning(
                "task_max_retries_exceeded",
                task_name=message.task_name,
                task_id=message.task_id,
                retries=current_retry,
                max_retries=max_retries,
                error=str(exception),
            )
            return

        # Calculate delay from policy delays list
        delays: list[int] = policy["delays"]
        delay = delays[min(current_retry, len(delays) - 1)]

        next_retry = current_retry + 1
        logger.info(
            "task_retry_scheduled",
            task_name=message.task_name,
            task_id=message.task_id,
            retry=next_retry,
            max_retries=max_retries,
            delay_seconds=delay,
            error=str(exception),
        )

        # Wait before re-queuing
        await asyncio.sleep(delay)

        # Build a kicker to re-send the task through the broker
        kicker: AsyncKicker = AsyncKicker(
            task_name=message.task_name,
            broker=self.broker,
            labels={**message.labels, "_retry_count": str(next_retry)},
        )

        await kicker.kiq(*message.args, **message.kwargs)

        # Suppress intermediate error result so result backend
        # does not store the failed attempt
        result.error = NoResultError()
