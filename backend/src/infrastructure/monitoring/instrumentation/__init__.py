"""Instrumentation utilities for custom application metrics."""

from src.infrastructure.monitoring.instrumentation.cache import track_cache_operation
from src.infrastructure.monitoring.instrumentation.database import instrument_database
from src.infrastructure.monitoring.instrumentation.http_client import (
    create_instrumented_client,
    instrument_existing_client,
)
from src.infrastructure.monitoring.instrumentation.routes import (
    track_auth_attempt,
    track_payment,
    track_registration,
    track_subscription_activation,
    track_trial_activation,
)

__all__ = [
    "instrument_database",
    "track_cache_operation",
    "create_instrumented_client",
    "instrument_existing_client",
    "track_auth_attempt",
    "track_registration",
    "track_payment",
    "track_subscription_activation",
    "track_trial_activation",
]
