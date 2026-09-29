"""SQLAlchemy OpenTelemetry tracing must survive the SQLAlchemy 2.1 upgrade."""

from __future__ import annotations

import pytest
import sqlalchemy
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import create_engine, text

from src.infrastructure.database import session as db_session
from src.infrastructure.monitoring.instrumentation import sqlalchemy_tracing
from src.infrastructure.monitoring.instrumentation.sqlalchemy_tracing import (
    VERIFIED_SQLALCHEMY_SERIES,
    instrument_sqlalchemy_engine,
)


@pytest.mark.unit
def test_installed_sqlalchemy_series_is_verified_for_tracing() -> None:
    series = ".".join(sqlalchemy.__version__.split(".")[:2])

    assert series in VERIFIED_SQLALCHEMY_SERIES


@pytest.mark.unit
def test_engine_queries_emit_spans_on_installed_sqlalchemy() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    engine = create_engine("sqlite://")
    # The application may already have instrumented its own engine on import
    # (the instrumentor is a process-wide singleton); isolate this test and
    # restore that state afterwards.
    was_instrumented = SQLAlchemyInstrumentor().is_instrumented_by_opentelemetry
    if was_instrumented:
        SQLAlchemyInstrumentor().uninstrument()
    try:
        instrument_sqlalchemy_engine(engine, tracer_provider=provider)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        SQLAlchemyInstrumentor().uninstrument()
        engine.dispose()
        if was_instrumented:
            instrument_sqlalchemy_engine(db_session.engine.sync_engine)

    spans = exporter.get_finished_spans()
    assert [span.name for span in spans if span.name.startswith("SELECT")]


@pytest.mark.unit
def test_unverified_sqlalchemy_series_keeps_library_dependency_check(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _RecordingInstrumentor:
        def instrument(self, **options: object) -> None:
            captured.update(options)

    monkeypatch.setattr(sqlalchemy_tracing, "_sqlalchemy_series", lambda: "2.2")
    monkeypatch.setattr(sqlalchemy_tracing, "SQLAlchemyInstrumentor", _RecordingInstrumentor)
    engine = create_engine("sqlite://")
    try:
        instrument_sqlalchemy_engine(engine)
    finally:
        engine.dispose()

    assert captured == {"engine": engine}
