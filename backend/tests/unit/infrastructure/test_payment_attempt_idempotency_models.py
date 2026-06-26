from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel


def test_payment_attempt_model_declares_database_idempotency_invariants() -> None:
    table = PaymentAttemptModel.__table__
    constraint_names = {constraint.name for constraint in table.constraints if isinstance(constraint, UniqueConstraint)}
    assert "uq_payment_attempts_order_idempotency_key" in constraint_names

    order_attempt_number = _index(table.indexes, "uq_payment_attempts_order_attempt_number")
    assert order_attempt_number.unique is True
    assert [column.name for column in order_attempt_number.columns] == ["order_id", "attempt_number"]

    active_attempt = _index(table.indexes, "uq_payment_attempts_order_active")
    assert active_attempt.unique is True
    assert [column.name for column in active_attempt.columns] == ["order_id"]
    assert str(active_attempt.dialect_options["postgresql"]["where"]) == "status IN ('pending', 'processing')"
    assert str(active_attempt.dialect_options["sqlite"]["where"]) == "status IN ('pending', 'processing')"

    succeeded_attempt = _index(table.indexes, "uq_payment_attempts_order_succeeded")
    assert succeeded_attempt.unique is True
    assert [column.name for column in succeeded_attempt.columns] == ["order_id"]
    assert str(succeeded_attempt.dialect_options["postgresql"]["where"]) == "status = 'succeeded'"
    assert str(succeeded_attempt.dialect_options["sqlite"]["where"]) == "status = 'succeeded'"


def test_payment_model_declares_internal_zero_external_reference_uniqueness() -> None:
    check_names = {
        constraint.name for constraint in PaymentModel.__table__.constraints if isinstance(constraint, CheckConstraint)
    }
    assert "ck_payments_internal_zero_external_id_required" in check_names

    internal_zero = _index(PaymentModel.__table__.indexes, "uq_payments_internal_zero_external_id")
    assert internal_zero.unique is True
    assert [column.name for column in internal_zero.columns] == ["provider", "external_id"]
    assert (
        str(internal_zero.dialect_options["postgresql"]["where"])
        == "provider = 'internal_zero' AND external_id IS NOT NULL"
    )
    assert (
        str(internal_zero.dialect_options["sqlite"]["where"])
        == "provider = 'internal_zero' AND external_id IS NOT NULL"
    )


def _index(indexes: set[Index], name: str) -> Index:
    index = next((candidate for candidate in indexes if candidate.name == name), None)
    assert index is not None
    return index
