"""Email task dispatcher using TaskIQ RedisStreamBroker.

Dispatches OTP email tasks to the task-worker service via Redis streams.
Implements fire-and-forget pattern for non-blocking email delivery.
"""

import hashlib
import json
import uuid
from typing import Any

import redis.asyncio as redis
import structlog
from taskiq.serializers.json_serializer import JSONSerializer
from taskiq_redis import RedisStreamBroker

from src.config.settings import settings

logger = structlog.get_logger(__name__)

EMAIL_TASK_PAYLOAD_KEY_PREFIX = "cybervpn:email-task-payload:"
DEFAULT_EMAIL_TASK_PAYLOAD_TTL_SECONDS = 4 * 60 * 60


def _recipient_log_fields(email: str) -> dict[str, str]:
    """Return non-reversible recipient identifiers safe for structured logs."""
    normalized = email.strip().lower()
    domain = normalized.rsplit("@", 1)[1] if "@" in normalized else "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "recipient_hash": digest[:16],
        "recipient_domain": domain or "unknown",
    }


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

    def __init__(self, redis_url: str | None = None, payload_ttl_seconds: int | None = None) -> None:
        """
        Initialize email task dispatcher.

        Args:
            redis_url: Redis URL for TaskIQ broker. Defaults to settings.redis_url.
            payload_ttl_seconds: TTL for sensitive email payload indirection.
        """
        self._redis_url = redis_url or settings.redis_url
        self._payload_ttl_seconds = payload_ttl_seconds or DEFAULT_EMAIL_TASK_PAYLOAD_TTL_SECONDS
        self._broker: RedisStreamBroker | None = None
        self._serializer = JSONSerializer()

    async def _get_broker(self) -> RedisStreamBroker:
        """Get or create TaskIQ broker connection."""
        if self._broker is None:
            self._broker = RedisStreamBroker(url=self._redis_url)
            await self._broker.startup()
        return self._broker

    async def _enqueue_email_task(
        self,
        *,
        task_name: str,
        payload_kind: str,
        payload: dict[str, Any],
        log_event_prefix: str,
    ) -> str:
        """Store sensitive payload out-of-band and enqueue a TaskIQ reference."""
        await self._get_broker()

        task_id = str(uuid.uuid4())
        payload_ref = f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}{task_id}"
        payload_body = {
            "version": 1,
            "kind": payload_kind,
            **payload,
        }
        recipient_fields = _recipient_log_fields(str(payload.get("email", "")))

        logger.info(
            f"dispatching_{log_event_prefix}_task",
            task_id=task_id,
            locale=payload.get("locale"),
            is_resend=payload.get("is_resend", False),
            channel=payload.get("channel"),
            **recipient_fields,
        )

        full_message = {
            "task_id": task_id,
            "task_name": task_name,
            "labels": {"queue": "email", "retry_policy": "email_delivery"},
            "args": [],
            "kwargs": {
                "payload_ref": payload_ref,
            },
        }
        message_bytes = self._serializer.dumpb(full_message)

        redis_client = redis.from_url(self._redis_url)
        try:
            stored = await redis_client.set(
                payload_ref,
                json.dumps(payload_body, separators=(",", ":")),
                ex=self._payload_ttl_seconds,
                nx=True,
            )
            if stored is not True:
                raise RuntimeError("email_task_payload_ref_collision")

            # TaskIQ RedisStreamBroker uses stream named "taskiq".
            await redis_client.xadd("taskiq", {"data": message_bytes})
        except Exception:
            await redis_client.delete(payload_ref)
            raise
        finally:
            await redis_client.aclose()

        logger.info(
            f"{log_event_prefix}_task_dispatched",
            task_id=task_id,
            is_resend=payload.get("is_resend", False),
            **recipient_fields,
        )

        return task_id

    async def dispatch_otp_email(
        self,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
        is_resend: bool = False,
        channel: str = "web",
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
        return await self._enqueue_email_task(
            task_name="send_otp_email",
            payload_kind="otp",
            payload={
                "email": email,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
                "channel": channel,
            },
            log_event_prefix="otp_email",
        )

    async def dispatch_magic_link_email(
        self,
        email: str,
        token: str,
        otp_code: str = "",
        locale: str = "en-EN",
        is_resend: bool = False,
        channel: str = "web",
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
        return await self._enqueue_email_task(
            task_name="send_magic_link_email",
            payload_kind="magic_link",
            payload={
                "email": email,
                "token": token,
                "otp_code": otp_code,
                "locale": locale,
                "is_resend": is_resend,
                "channel": channel,
            },
            log_event_prefix="magic_link_email",
        )

    async def dispatch_password_reset_email(
        self,
        email: str,
        otp_code: str,
        locale: str = "en-EN",
        channel: str = "web",
    ) -> str:
        """Dispatch password reset email task to task-worker.

        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code for password reset
            locale: User's locale for email template

        Returns:
            Task ID for tracking
        """
        return await self._enqueue_email_task(
            task_name="send_password_reset_email",
            payload_kind="password_reset",
            payload={
                "email": email,
                "otp_code": otp_code,
                "locale": locale,
                "channel": channel,
            },
            log_event_prefix="password_reset_email",
        )

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
