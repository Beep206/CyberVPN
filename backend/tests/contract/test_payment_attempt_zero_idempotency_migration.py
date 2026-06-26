"""Payment attempt/internal-zero idempotency migration contract tests."""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import Engine


def _load_migration():
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic" / "versions" / "20260625_payment_attempt_idempotency.py"
    )
    spec = importlib.util.spec_from_file_location("payment_attempt_zero_idempotency_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def _sqlite_engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        yield engine
    finally:
        engine.dispose()


def test_payment_attempt_idempotency_migration_blocks_duplicate_attempt_numbers() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_payment_attempts_table(conn)
        conn.execute(
            sa.text(
                """
                INSERT INTO payment_attempts (id, order_id, attempt_number, status, idempotency_key)
                VALUES
                    ('attempt-1', 'order-1', 1, 'failed', 'retry-1'),
                    ('attempt-2', 'order-1', 1, 'expired', 'retry-2')
                """
            )
        )

        with pytest.raises(RuntimeError, match="attempt-number uniqueness"):
            migration._assert_no_duplicate_attempt_numbers(conn)

        conn.execute(sa.text("DELETE FROM payment_attempts WHERE id = 'attempt-2'"))
        migration._assert_no_duplicate_attempt_numbers(conn)


def test_payment_attempt_idempotency_migration_blocks_duplicate_active_attempts() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_payment_attempts_table(conn)
        conn.execute(
            sa.text(
                """
                INSERT INTO payment_attempts (id, order_id, attempt_number, status, idempotency_key)
                VALUES
                    ('attempt-1', 'order-1', 1, 'pending', 'retry-1'),
                    ('attempt-2', 'order-1', 2, 'processing', 'retry-2')
                """
            )
        )

        with pytest.raises(RuntimeError, match="active-attempt uniqueness"):
            migration._assert_no_duplicate_active_attempts(conn)

        conn.execute(sa.text("UPDATE payment_attempts SET status = 'failed' WHERE id = 'attempt-2'"))
        migration._assert_no_duplicate_active_attempts(conn)


def test_payment_attempt_idempotency_migration_blocks_duplicate_succeeded_attempts() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_payment_attempts_table(conn)
        conn.execute(
            sa.text(
                """
                INSERT INTO payment_attempts (id, order_id, attempt_number, status, idempotency_key)
                VALUES
                    ('attempt-1', 'order-1', 1, 'succeeded', 'retry-1'),
                    ('attempt-2', 'order-1', 2, 'succeeded', 'retry-2')
                """
            )
        )

        with pytest.raises(RuntimeError, match="succeeded-attempt uniqueness"):
            migration._assert_no_duplicate_succeeded_attempts(conn)

        conn.execute(sa.text("UPDATE payment_attempts SET status = 'refunded' WHERE id = 'attempt-2'"))
        migration._assert_no_duplicate_succeeded_attempts(conn)


def test_payment_attempt_idempotency_migration_blocks_duplicate_internal_zero_external_ids_only() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_payments_table(conn)
        conn.execute(
            sa.text(
                """
                INSERT INTO payments (id, provider, external_id)
                VALUES
                    ('payment-1', 'cryptobot', 'provider-reference-1'),
                    ('payment-2', 'cryptobot', 'provider-reference-1'),
                    ('payment-3', 'internal_zero', 'internal_zero:order-1'),
                    ('payment-4', 'internal_zero', 'internal_zero:order-1'),
                    ('payment-5', 'internal_zero', NULL),
                    ('payment-6', 'internal_zero', NULL)
                """
            )
        )

        with pytest.raises(RuntimeError, match="internal_zero payment external-reference uniqueness"):
            migration._assert_no_duplicate_internal_zero_external_ids(conn)

        conn.execute(sa.text("DELETE FROM payments WHERE id = 'payment-4'"))
        migration._assert_no_duplicate_internal_zero_external_ids(conn)


def test_payment_attempt_idempotency_migration_blocks_internal_zero_null_external_ids() -> None:
    migration = _load_migration()
    with _sqlite_engine() as engine, engine.begin() as conn:
        _create_payments_table(conn)
        conn.execute(
            sa.text(
                """
                INSERT INTO payments (id, provider, external_id)
                VALUES
                    ('payment-1', 'internal_zero', NULL),
                    ('payment-2', 'cryptobot', NULL)
                """
            )
        )

        with pytest.raises(RuntimeError, match="NULL external_id"):
            migration._assert_no_internal_zero_null_external_ids(conn)

        conn.execute(sa.text("UPDATE payments SET external_id = 'internal_zero:order-1' WHERE id = 'payment-1'"))
        migration._assert_no_internal_zero_null_external_ids(conn)


def _create_payment_attempts_table(conn: sa.Connection) -> None:
    conn.execute(
        sa.text(
            """
            CREATE TABLE payment_attempts (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT NOT NULL
            )
            """
        )
    )


def _create_payments_table(conn: sa.Connection) -> None:
    conn.execute(
        sa.text(
            """
            CREATE TABLE payments (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                external_id TEXT NULL
            )
            """
        )
    )
