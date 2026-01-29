"""Shared type aliases for the task worker.

This module provides common type aliases used throughout the task worker
to improve type safety and code readability.
"""

from typing import TypeAlias

# Task result type - represents the return value of task functions
# Tasks typically return dictionaries with counts, statuses, or other metadata
TaskResult: TypeAlias = dict[str, int | str | float | bool | list | None]

# Common type aliases for task parameters
UserId: TypeAlias = int
NodeId: TypeAlias = int
PaymentId: TypeAlias = int
NotificationId: TypeAlias = int
SubscriptionId: TypeAlias = int

# Bulk operation types
BulkOperationType: TypeAlias = str  # e.g., "enable_users", "disable_users", "send_notifications"
BulkOperationStatus: TypeAlias = str  # e.g., "pending", "processing", "completed", "failed"

# Date/time strings
DateString: TypeAlias = str  # Format: YYYY-MM-DD
DateTimeString: TypeAlias = str  # ISO 8601 format

# Queue names
QueueName: TypeAlias = str

__all__ = [
    "TaskResult",
    "UserId",
    "NodeId",
    "PaymentId",
    "NotificationId",
    "SubscriptionId",
    "BulkOperationType",
    "BulkOperationStatus",
    "DateString",
    "DateTimeString",
    "QueueName",
]
