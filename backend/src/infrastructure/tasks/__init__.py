"""TaskIQ task infrastructure for dispatching background jobs."""

from src.infrastructure.tasks.email_task_dispatcher import EmailTaskDispatcher

__all__ = ["EmailTaskDispatcher"]
