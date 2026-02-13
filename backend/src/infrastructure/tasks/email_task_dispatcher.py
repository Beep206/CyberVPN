"""Email task dispatcher using TaskIQ RedisStreamBroker.

Dispatches OTP email tasks to the task-worker service via Redis streams.
Implements fire-and-forget pattern for non-blocking email delivery.
"""

import uuid

import structlog
from taskiq.serializers.json_serializer import JSONSerializer
from taskiq_redis import RedisStreamBroker

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class EmailTaskDispatcher:
    """
    Dispatches email tasks to task-worker via TaskIQ.

    Connects to the same Redis instance as task-worker to enqueue
    background jobs for email delivery. Uses the TaskIQ message format
    to communicate with task-worker without importing its task definitions.

    Usage:
        dispatcher = EmailTaskDispatcher()
        await dispatcher.dispatch_otp_email("user@example.com", "123456")
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """
        Initialize email task dispatcher.

        Args:
            redis_url: Redis URL for TaskIQ broker. Defaults to settings.redis_url.
        """
        self._redis_url = redis_url or settings.redis_url
        self._broker: RedisStreamBroker | None = None
        self._serializer = JSONSerializer()

    async def _get_broker(self) -> RedisStreamBroker:
        """Get or create TaskIQ broker connection."""
        if self._broker is None:
            self._broker = RedisStreamBroker(url=self._redis_url)
            await self._broker.startup()
        return self._broker

    async def dispatch_otp_email(
        self,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
        is_resend: bool = False,
    ) -> str:
        """
        Dispatch OTP email task to task-worker.

        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code
            locale: User's locale for email template
            is_resend: If True, task-worker uses Brevo (secondary provider)

        Returns:
            Task ID for tracking

        Raises:
            Exception: If task dispatch fails
        """
        await self._get_broker()

        task_id = str(uuid.uuid4())

        logger.info(
            "dispatching_otp_email_task",
            task_id=task_id,
            email=email,
            locale=locale,
            is_resend=is_resend,
        )

        # Create full TaskIQ message with task metadata
        # The message must include ALL fields that TaskiqMessage expects
        full_message = {
            "task_id": task_id,
            "task_name": "send_otp_email",
            "labels": {"queue": "email", "retry_policy": "email_delivery"},
            "args": [],
            "kwargs": {
                "email": email,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
            },
        }
        message_bytes = self._serializer.dumpb(full_message)

        # Send directly to Redis stream (same queue as task-worker)
        import redis.asyncio as redis

        redis_client = redis.from_url(self._redis_url)
        try:
            # TaskIQ RedisStreamBroker uses stream named "taskiq"
            await redis_client.xadd("taskiq", {"data": message_bytes})
        finally:
            await redis_client.aclose()

        logger.info(
            "otp_email_task_dispatched",
            task_id=task_id,
            email=email,
            is_resend=is_resend,
        )

        return task_id

    async def dispatch_magic_link_email(
        self,
        email: str,
        token: str,
        otp_code: str = "",
        locale: str = "en-EN",
        is_resend: bool = False,
    ) -> str:
        """Dispatch magic link email task to task-worker.

        Args:
            email: Recipient email address
            token: Magic link token
            otp_code: 6-digit OTP code (alternative to clicking the link)
            locale: User's locale for email template
            is_resend: If True, task-worker uses Brevo (secondary provider)

        Returns:
            Task ID for tracking
        """
        await self._get_broker()

        task_id = str(uuid.uuid4())

        logger.info(
            "dispatching_magic_link_email_task",
            task_id=task_id,
            email=email,
            locale=locale,
            is_resend=is_resend,
        )

        full_message = {
            "task_id": task_id,
            "task_name": "send_magic_link_email",
            "labels": {"queue": "email", "retry_policy": "email_delivery"},
            "args": [],
            "kwargs": {
                "email": email,
                "token": token,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
            },
        }
        message_bytes = self._serializer.dumpb(full_message)

        import redis.asyncio as redis

        redis_client = redis.from_url(self._redis_url)
        try:
            await redis_client.xadd("taskiq", {"data": message_bytes})
        finally:
            await redis_client.aclose()

        logger.info(
            "magic_link_email_task_dispatched",
            task_id=task_id,
            email=email,
        )

        return task_id

    async def dispatch_password_reset_email(
        self,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
    ) -> str:
        """Dispatch password reset email task to task-worker.

        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code for password reset
            locale: User's locale for email template

        Returns:
            Task ID for tracking
        """
        await self._get_broker()

        task_id = str(uuid.uuid4())

        logger.info(
            "dispatching_password_reset_email_task",
            task_id=task_id,
            email=email,
            locale=locale,
        )

        full_message = {
            "task_id": task_id,
            "task_name": "send_password_reset_email",
            "labels": {"queue": "email", "retry_policy": "email_delivery"},
            "args": [],
            "kwargs": {
                "email": email,
                "otp_code": otp_code,
                "locale": locale,
            },
        }
        message_bytes = self._serializer.dumpb(full_message)

        import redis.asyncio as redis

        redis_client = redis.from_url(self._redis_url)
        try:
            await redis_client.xadd("taskiq", {"data": message_bytes})
        finally:
            await redis_client.aclose()

        logger.info(
            "password_reset_email_task_dispatched",
            task_id=task_id,
            email=email,
        )

        return task_id

    async def close(self) -> None:
        """Close broker connection."""
        if self._broker is not None:
            await self._broker.shutdown()
            self._broker = None


# Singleton instance for FastAPI dependency injection
_dispatcher: EmailTaskDispatcher | None = None


async def get_email_dispatcher() -> EmailTaskDispatcher:
    """
    Get email task dispatcher singleton.

    For use as a FastAPI dependency.
    """
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = EmailTaskDispatcher()
    return _dispatcher


async def shutdown_email_dispatcher() -> None:
    """
    Shutdown email dispatcher on app shutdown.

    Call this in FastAPI lifespan shutdown.
    """
    global _dispatcher
    if _dispatcher is not None:
        await _dispatcher.close()
        _dispatcher = None
