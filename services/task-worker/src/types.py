"""Shared type aliases for the task worker.

This module provides common type aliases used throughout the task worker
to improve type safety and code readability.
"""

# Task result type - represents the return value of task functions
# Tasks typically return dictionaries with counts, statuses, or other metadata
type TaskResult = dict[str, int | str | float | bool | list | None]

# Common type aliases for task parameters
type UserId = int
type NodeId = int
type PaymentId = int
type NotificationId = int
type SubscriptionId = int

# Bulk operation types
type BulkOperationType = str  # e.g., "enable_users", "disable_users", "send_notifications"
type BulkOperationStatus = str  # e.g., "pending", "processing", "completed", "failed"

# Date/time strings
type DateString = str  # Format: YYYY-MM-DD
type DateTimeString = str  # ISO 8601 format

# Queue names
type QueueName = str

__all__ = [
    "BulkOperationStatus",
    "BulkOperationType",
    "DateString",
    "DateTimeString",
    "NodeId",
    "NotificationId",
    "PaymentId",
    "QueueName",
    "SubscriptionId",
    "TaskResult",
    "UserId",
]
