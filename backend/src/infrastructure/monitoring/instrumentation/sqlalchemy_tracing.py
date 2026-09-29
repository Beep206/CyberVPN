"""OpenTelemetry tracing for the SQLAlchemy engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sqlalchemy
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

if TYPE_CHECKING:
    from opentelemetry.trace import TracerProvider
    from sqlalchemy.engine import Engine

# opentelemetry-instrumentation-sqlalchemy (<= 0.66b0) still declares support
# only for SQLAlchemy < 2.1 and, without this override, logs an error and
# installs no hooks at all on 2.1 (open-telemetry/opentelemetry-python-contrib
# issue #5118).  Its engine event hooks work unchanged on 2.1, which is covered
# by tests/unit/infrastructure/test_sqlalchemy_tracing.py.  The declared-range
# check is bypassed only for series verified in this repository; any other
# series falls back to the library's own compatibility check.
VERIFIED_SQLALCHEMY_SERIES = frozenset({"2.0", "2.1"})


def _sqlalchemy_series() -> str:
    return ".".join(sqlalchemy.__version__.split(".")[:2])


def instrument_sqlalchemy_engine(sync_engine: Engine, *, tracer_provider: TracerProvider | None = None) -> None:
    """Attach OpenTelemetry query spans to ``sync_engine``."""
    options: dict[str, Any] = {"engine": sync_engine}
    if tracer_provider is not None:
        options["tracer_provider"] = tracer_provider
    if _sqlalchemy_series() in VERIFIED_SQLALCHEMY_SERIES:
        options["skip_dep_check"] = True
    SQLAlchemyInstrumentor().instrument(**options)
