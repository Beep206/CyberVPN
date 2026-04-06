"""Task modules for CyberVPN task worker. Import all to register with broker."""

import src.tasks.email  # noqa: F401
import src.tasks.monitoring  # noqa: F401
import src.tasks.notifications  # noqa: F401
import src.tasks.sync  # noqa: F401
import src.tasks.wallet  # noqa: F401
