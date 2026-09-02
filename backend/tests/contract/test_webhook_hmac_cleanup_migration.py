from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260830_webhook_hmac_cleanup.py"


def _load_migration() -> Any:
    spec = importlib.util.spec_from_file_location("webhook_hmac_cleanup", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _RecordingConnection:
    def __init__(self, connection: sa.Connection) -> None:
        self._connection = connection
        self.select_limits: list[int] = []

    @property
    def dialect(self) -> sa.engine.Dialect:
        return self._connection.dialect

    def execute(self, statement: Any):
        if isinstance(statement, sa.sql.Select):
            limit_clause = statement._limit_clause  # noqa: SLF001 - migration bound assertion
            if limit_clause is not None:
                self.select_limits.append(int(limit_clause.value))
        return self._connection.execute(statement)


def _webhook_logs_table(metadata: sa.MetaData) -> sa.Table:
    return sa.Table(
        "webhook_logs",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("signature", sa.String(length=64), nullable=True),
    )


@pytest.fixture
def sqlite_engine():
    engine = sa.create_engine("sqlite://")
    try:
        yield engine
    finally:
        engine.dispose()


def test_upgrade_removes_legacy_sha_fingerprints_in_bounded_batches(monkeypatch, sqlite_engine) -> None:
    migration = _load_migration()
    migration._BATCH_SIZE = 2
    migration._MAX_MIGRATION_ROWS = 10
    metadata = sa.MetaData()
    webhook_logs = _webhook_logs_table(metadata)
    metadata.create_all(sqlite_engine)
    identifiers = [uuid4() for _ in range(5)]

    with sqlite_engine.begin() as connection:
        connection.execute(
            webhook_logs.insert(),
            [
                {
                    "id": row_id,
                    "payload": {
                        "schema": "webhook_log.redacted.v1",
                        "source": "remnawave",
                        "event_type": "user.updated",
                        "status": "active",
                        "validation_status": "valid",
                        "signature_present": True,
                        "body_sha256": "f" * 64,
                        "event_id_fingerprint": "a" * 64,
                        "subject_fingerprint": "b" * 64,
                        "raw_body": "must-not-survive-cleanup",
                    },
                    "signature": "c" * 64,
                }
                for row_id in identifiers
            ],
        )
        recording_connection = _RecordingConnection(connection)
        monkeypatch.setattr(migration.op, "get_bind", lambda: recording_connection)

        migration.upgrade()

        rows = connection.execute(sa.select(webhook_logs).order_by(webhook_logs.c.id)).mappings().all()
        first_pass = [(row["payload"], row["signature"]) for row in rows]
        assert len(rows) == 5
        assert recording_connection.select_limits == [1, 2, 2, 2, 2]
        for row in rows:
            payload = row["payload"]
            assert row["signature"] is None
            assert payload == {
                "event_type": "user.updated",
                "legacy_fingerprints_removed": True,
                "schema": "webhook_log.redacted.v2",
                "signature_present": True,
                "source": "remnawave",
                "status": "active",
                "validation_status": "valid",
            }

        recording_connection.select_limits.clear()
        migration.upgrade()
        rows_after_retry = connection.execute(sa.select(webhook_logs).order_by(webhook_logs.c.id)).mappings().all()
        assert [(row["payload"], row["signature"]) for row in rows_after_retry] == first_pass
        assert recording_connection.select_limits == []


def test_upgrade_fails_before_updates_when_backlog_exceeds_transaction_cap(monkeypatch, sqlite_engine) -> None:
    migration = _load_migration()
    migration._MAX_MIGRATION_ROWS = 2
    metadata = sa.MetaData()
    webhook_logs = _webhook_logs_table(metadata)
    metadata.create_all(sqlite_engine)
    identifiers = [uuid4() for _ in range(3)]

    with sqlite_engine.begin() as connection:
        connection.execute(
            webhook_logs.insert(),
            [
                {
                    "id": row_id,
                    "payload": {"schema": "webhook_log.redacted.v1", "raw_body": "must-survive-refusal"},
                    "signature": "a" * 64,
                }
                for row_id in identifiers
            ],
        )
        monkeypatch.setattr(migration.op, "get_bind", lambda: _RecordingConnection(connection))

        with pytest.raises(RuntimeError, match="safe Alembic cap"):
            migration.upgrade()

        rows = connection.execute(sa.select(webhook_logs).order_by(webhook_logs.c.id)).mappings().all()
        assert len(rows) == 3
        assert all(row["signature"] == "a" * 64 for row in rows)
        assert all(row["payload"]["raw_body"] == "must-survive-refusal" for row in rows)


def test_downgrade_preserves_irreversible_privacy_cleanup(monkeypatch, sqlite_engine) -> None:
    migration = _load_migration()
    metadata = sa.MetaData()
    webhook_logs = _webhook_logs_table(metadata)
    metadata.create_all(sqlite_engine)

    with sqlite_engine.begin() as connection:
        row_id = uuid4()
        connection.execute(
            webhook_logs.insert().values(
                id=row_id,
                payload={
                    "schema": "webhook_log.redacted.v1",
                    "source": "cryptobot",
                    "invoice_id_fingerprint": "d" * 64,
                },
                signature="e" * 64,
            )
        )
        monkeypatch.setattr(migration.op, "get_bind", lambda: _RecordingConnection(connection))

        migration.upgrade()
        migration.downgrade()

        row = connection.execute(sa.select(webhook_logs).where(webhook_logs.c.id == row_id)).mappings().one()
        assert row["signature"] is None
        assert row["payload"] == {
            "legacy_fingerprints_removed": True,
            "schema": "webhook_log.redacted.v2",
            "source": "cryptobot",
        }


def test_reupgrade_privacy_safely_drops_existing_v2_fingerprints() -> None:
    migration = _load_migration()

    sanitized = migration._sanitize_payload(
        {
            "schema": "webhook_log.redacted.v2",
            "source": "remnawave",
            "event_type": "user.updated",
            "body_fingerprint": "a" * 64,
            "event_id_fingerprint": "b" * 64,
            "subject_fingerprint": "c" * 64,
            "validation_status": "valid",
        },
        signature_fingerprint_present=True,
    )

    assert sanitized == {
        "event_type": "user.updated",
        "legacy_fingerprints_removed": True,
        "schema": "webhook_log.redacted.v2",
        "source": "remnawave",
        "validation_status": "valid",
    }
