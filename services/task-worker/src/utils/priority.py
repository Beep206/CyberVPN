"""Notification priority levels and queue mapping.

Defines priority levels for notifications and maps them to dedicated Redis queues
for priority-based processing.
"""

from enum import IntEnum


class NotificationPriority(IntEnum):
    """Priority levels for notifications (higher value = higher priority)."""

    LOW = 0  # Marketing messages, bulk announcements
    NORMAL = 1  # Regular notifications, payment confirmations
    HIGH = 2  # Service alerts, expiration warnings
    CRITICAL = 3  # System failures, security alerts


# Map priority levels to dedicated Redis queue names
PRIORITY_QUEUES: dict[NotificationPriority, str] = {
    NotificationPriority.CRITICAL: "notifications:critical",
    NotificationPriority.HIGH: "notifications:high",
    NotificationPriority.NORMAL: "notifications:normal",
    NotificationPriority.LOW: "notifications:low",
}


def get_queue_for_priority(priority: NotificationPriority) -> str:
    """Get Redis queue name for a given priority level.

    Args:
        priority: Notification priority level

    Returns:
        Redis queue name

    Raises:
        ValueError: If priority is invalid
    """
    if priority not in PRIORITY_QUEUES:
        raise ValueError(f"Invalid priority level: {priority}")
    return PRIORITY_QUEUES[priority]
