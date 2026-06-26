"""Harden payment attempt and internal-zero idempotency.

Revision ID: 20260625_pay_attempt_idem
Revises: 20260625_internal_status
Create Date: 2026-06-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260625_pay_attempt_idem"
down_revision: str | Sequence[str] | None = "20260625_internal_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYMENT_ATTEMPT_ORDER_NUMBER_INDEX = "uq_payment_attempts_order_attempt_number"
PAYMENT_ATTEMPT_ACTIVE_INDEX = "uq_payment_attempts_order_active"
PAYMENT_ATTEMPT_SUCCEEDED_INDEX = "uq_payment_attempts_order_succeeded"
PAYMENT_INTERNAL_ZERO_EXTERNAL_INDEX = "uq_payments_internal_zero_external_id"
PAYMENT_INTERNAL_ZERO_EXTERNAL_CHECK = "ck_payments_internal_zero_external_id_required"


def upgrade() -> None:
    bind = op.get_bind()
    _assert_no_duplicate_attempt_numbers(bind)
    _assert_no_duplicate_active_attempts(bind)
    _assert_no_duplicate_succeeded_attempts(bind)
    _assert_no_internal_zero_null_external_ids(bind)
    _assert_no_duplicate_internal_zero_external_ids(bind)

    op.create_index(
        PAYMENT_ATTEMPT_ORDER_NUMBER_INDEX,
        "payment_attempts",
        ["order_id", "attempt_number"],
        unique=True,
    )
    op.create_index(
        PAYMENT_ATTEMPT_ACTIVE_INDEX,
        "payment_attempts",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
        sqlite_where=sa.text("status IN ('pending', 'processing')"),
    )
    op.create_index(
        PAYMENT_ATTEMPT_SUCCEEDED_INDEX,
        "payment_attempts",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
        sqlite_where=sa.text("status = 'succeeded'"),
    )
    op.create_index(
        PAYMENT_INTERNAL_ZERO_EXTERNAL_INDEX,
        "payments",
        ["provider", "external_id"],
        unique=True,
        postgresql_where=sa.text("provider = 'internal_zero' AND external_id IS NOT NULL"),
        sqlite_where=sa.text("provider = 'internal_zero' AND external_id IS NOT NULL"),
    )
    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_check_constraint(
            PAYMENT_INTERNAL_ZERO_EXTERNAL_CHECK,
            "provider <> 'internal_zero' OR external_id IS NOT NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint(PAYMENT_INTERNAL_ZERO_EXTERNAL_CHECK, type_="check")
    op.drop_index(PAYMENT_INTERNAL_ZERO_EXTERNAL_INDEX, table_name="payments")
    op.drop_index(PAYMENT_ATTEMPT_SUCCEEDED_INDEX, table_name="payment_attempts")
    op.drop_index(PAYMENT_ATTEMPT_ACTIVE_INDEX, table_name="payment_attempts")
    op.drop_index(PAYMENT_ATTEMPT_ORDER_NUMBER_INDEX, table_name="payment_attempts")


def _assert_no_duplicate_attempt_numbers(bind: sa.Connection) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT order_id, attempt_number, COUNT(*) AS duplicate_count
            FROM payment_attempts
            GROUP BY order_id, attempt_number
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add payment attempt attempt-number uniqueness while duplicate "
            "(order_id, attempt_number) rows exist. Resolve duplicate payment attempts first."
        )


def _assert_no_duplicate_active_attempts(bind: sa.Connection) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT order_id, COUNT(*) AS active_count
            FROM payment_attempts
            WHERE status IN ('pending', 'processing')
            GROUP BY order_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add payment attempt active-attempt uniqueness while an order has multiple "
            "pending or processing attempts. Terminally classify duplicate active attempts first."
        )


def _assert_no_duplicate_succeeded_attempts(bind: sa.Connection) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT order_id, COUNT(*) AS succeeded_count
            FROM payment_attempts
            WHERE status = 'succeeded'
            GROUP BY order_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add payment attempt succeeded-attempt uniqueness while an order has multiple "
            "succeeded attempts. Resolve duplicate settlement rows before migration."
        )


def _assert_no_internal_zero_null_external_ids(bind: sa.Connection) -> None:
    invalid = bind.execute(
        sa.text(
            """
            SELECT id
            FROM payments
            WHERE provider = 'internal_zero'
              AND external_id IS NULL
            LIMIT 1
            """
        )
    ).first()
    if invalid is not None:
        raise RuntimeError(
            "Cannot require internal_zero payment external references while existing "
            "internal_zero rows have NULL external_id. Backfill deterministic internal "
            "settlement references before migration."
        )


def _assert_no_duplicate_internal_zero_external_ids(bind: sa.Connection) -> None:
    duplicate = bind.execute(
        sa.text(
            """
            SELECT external_id, COUNT(*) AS duplicate_count
            FROM payments
            WHERE provider = 'internal_zero'
              AND external_id IS NOT NULL
            GROUP BY external_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add internal_zero payment external-reference uniqueness while duplicate "
            "internal_zero external_id rows exist. Resolve duplicate internal settlements first."
        )
