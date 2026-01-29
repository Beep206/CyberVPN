"""Schedule definitions for periodic tasks.

Registers all scheduled tasks with the TaskIQ scheduler using cron expressions
from src.utils.constants.
"""

from src.schedules.definitions import register_schedules

__all__ = ["register_schedules"]
