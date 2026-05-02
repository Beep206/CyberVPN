"""Task modules for CyberVPN task worker. Import all to register with broker."""

import src.tasks.analytics
import src.tasks.email
import src.tasks.monitoring
import src.tasks.notifications
import src.tasks.sync
import src.tasks.wallet  # noqa: F401
