"""Production TaskIQ scheduler entrypoint.

The TaskIQ CLI imports only the object named on its command line.  Import the
schedule definitions here so every label-based cron task is registered before
the scheduler starts consuming its sources.
"""

from src.broker import scheduler
from src.schedules import definitions as _schedule_definitions

__all__ = ["scheduler"]

# Keep an explicit reference for import-order documentation and debuggability.
assert _schedule_definitions is not None
