"""Notification task definitions."""

from src.tasks.notifications.broadcast import broadcast_message
from src.tasks.notifications.process_queue import process_notification_queue
from src.tasks.notifications.send_notification import send_notification
from src.tasks.notifications.stage1_contract import (
    STAGE1_TELEGRAM_NOTIFICATION_TYPES,
    Stage1TelegramNotification,
    build_stage1_telegram_notification,
)

__all__ = [
    "STAGE1_TELEGRAM_NOTIFICATION_TYPES",
    "Stage1TelegramNotification",
    "broadcast_message",
    "build_stage1_telegram_notification",
    "process_notification_queue",
    "send_notification",
]
