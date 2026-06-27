from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

from src.application.use_cases.growth_code_sets.reversals import (
    ReverseOrderCodeApplicationsForRefundUseCase,
    ReverseZeroPaymentOrderCancellationUseCase,
)
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthReversalEventModel,
    OrderCodeApplicationModel,
)
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


class _ScalarResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> list[SimpleNamespace]:
        return self._rows

    def first(self) -> SimpleNamespace | None:
        return self._rows[0] if self._rows else None


class _ExecuteResult:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._rows)


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session:
    def __init__(
        self,
        execute_rows: list[list[SimpleNamespace]],
        get_values: list[SimpleNamespace] | None = None,
    ) -> None:
        self._execute_rows = list(execute_rows)
        self._get_values = list(get_values or [])
        self.reversal_event = None
        self.added: list[object] = []
        self.flushed = 0
        self.committed = 0

    async def execute(self, statement):
        if "growth_reversal_events" in str(statement):
            return _ExecuteResult([self.reversal_event] if self.reversal_event is not None else [])
        if not self._execute_rows:
            raise AssertionError(f"unexpected statement: {statement}")
        return _ExecuteResult(self._execute_rows.pop(0))

    def add(self, value: object) -> None:
        self.added.append(value)
        if value.__class__.__name__ == "GrowthReversalEventModel":
            self.reversal_event = value

    async def flush(self) -> None:
        self.flushed += 1

    async def commit(self) -> None:
        self.committed += 1

    def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()

    async def get(self, _model, _id, *, with_for_update: bool = False):
        if not self._get_values:
            raise AssertionError("unexpected get")
        return self._get_values.pop(0)


def _application(*, order_id, reservation_id=None, snapshot=None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        order_id=order_id,
        reservation_id=reservation_id,
        application_status="applied",
        application_snapshot=snapshot or {"snapshot_version": "order_code_application.v6"},
        discount_amount=Decimal("12.34"),
        currency_code="USD",
        source_amount=Decimal("10.00"),
        source_currency_code="EUR",
        fx_conversion_id=UUID("00000000-0000-0000-0000-00000000f001"),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_refund_reversal_marks_each_order_code_application_once() -> None:
    order_id = uuid4()
    refund_id = uuid4()
    already_reversed_refund_id = uuid4()
    first_application = _application(order_id=order_id)
    second_application = _application(
        order_id=order_id,
        snapshot={
            "snapshot_version": "order_code_application.v6",
            "reversals": [
                {
                    "refund_id": str(already_reversed_refund_id),
                    "reversal_reason": "previous_refund",
                    "reversed_at": "2026-06-26T00:00:00+00:00",
                }
            ],
        },
    )
    session = _Session(
        [
            [first_application, second_application],
            [],
            [],
            [first_application, second_application],
            [],
            [],
        ]
    )

    result = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )

    assert result.reversed_count == 2
    assert result.application_ids == [first_application.id, second_application.id]
    for application in (first_application, second_application):
        assert application.application_status == "reversed"
        assert application.application_snapshot["reversal_state"] == "refund_reversed"
        assert application.application_snapshot["last_reversal"]["event_type"] == "refund"
        assert application.application_snapshot["last_reversal"]["refund_id"] == str(refund_id)
        assert application.application_snapshot["last_reversal"]["reversal_reason"] == "refund_succeeded"
        assert application.application_snapshot["last_reversal"]["applied_target_amount"] == "12.34"
        assert application.application_snapshot["last_reversal"]["source_amount"] == "10.00"
        assert application.application_snapshot["last_reversal"]["fx_conversion_id"] == str(
            UUID("00000000-0000-0000-0000-00000000f001")
        )
    assert second_application.application_snapshot["reversals"][0]["refund_id"] == str(already_reversed_refund_id)
    assert session.reversal_event is not None
    assert session.reversal_event.event_status == "applied"
    assert session.reversal_event.event_payload["order_code_application_count"] == 2
    assert session.reversal_event.event_payload["order_code_application_ids"] == [
        str(first_application.id),
        str(second_application.id),
    ]

    result = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )

    assert result.reversed_count == 0
    assert len(first_application.application_snapshot["reversals"]) == 1
    assert len(second_application.application_snapshot["reversals"]) == 2
    assert session.reversal_event.event_payload["order_code_application_count"] == 2


@pytest.mark.asyncio
async def test_refund_reversal_revokes_only_unused_invite_benefit_codes_once() -> None:
    order_id = uuid4()
    refund_id = uuid4()
    fulfillment_id = uuid4()
    batch_id = uuid4()
    fulfillment = SimpleNamespace(
        id=fulfillment_id,
        order_id=order_id,
        user_id=uuid4(),
        config_snapshot={"reversal_mode": "revoke_unredeemed"},
        result_payload={
            "invite_batch_id": str(batch_id),
            "requested_count": 2,
            "issued_count": 2,
        },
        created_at=datetime.now(UTC),
    )
    batch = SimpleNamespace(
        id=batch_id,
        source_order_id=order_id,
        status="issued",
        revoked_at=None,
        revoked_reason=None,
    )
    unused_code = SimpleNamespace(
        id=uuid4(),
        is_used=False,
        used_at=None,
        status="issued",
        revoked_at=None,
        revoked_reason=None,
    )
    used_code = SimpleNamespace(
        id=uuid4(),
        is_used=True,
        used_at=datetime.now(UTC),
        status="used",
        revoked_at=None,
        revoked_reason=None,
    )
    session = _Session(
        [
            [],
            [fulfillment],
            [unused_code, used_code],
            [],
            [],
            [fulfillment],
            [],
        ],
        get_values=[batch],
    )

    result = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )
    replay = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )

    assert result.fulfillment_reversal_count == 1
    assert result.invite_batches_revoked_count == 1
    assert result.invite_codes_revoked_count == 1
    assert unused_code.status == "revoked"
    assert unused_code.revoked_at is not None
    assert unused_code.revoked_reason == "refund_succeeded"
    assert used_code.status == "used"
    assert used_code.revoked_at is None
    assert batch.status == "partially_revoked"
    assert fulfillment.result_payload["last_reversal"]["status"] == "reversed"
    assert fulfillment.result_payload["last_reversal"]["idempotency_key"] == (
        f"benefit-reversal:{fulfillment_id}:{refund_id}"
    )
    assert fulfillment.result_payload["last_reversal"]["preserved_redeemed_invite_code_ids"] == [str(used_code.id)]
    assert session.reversal_event.event_payload["benefit_fulfillment_reversal_count"] == 1
    assert session.reversal_event.event_payload["invite_codes_revoked_count"] == 1
    assert replay.fulfillment_reversal_count == 0


@pytest.mark.asyncio
async def test_refund_reversal_marks_private_grant_revoked_without_reissuing_consumed_order_grant() -> None:
    order_id = uuid4()
    refund_id = uuid4()
    grant = SimpleNamespace(
        id=uuid4(),
        consumed_order_id=order_id,
        status="consumed",
        revoked_at=None,
        revoked_reason=None,
        metadata_={"code_count": 1},
        created_at=datetime.now(UTC),
    )
    session = _Session(
        [
            [],
            [],
            [grant],
            [],
            [],
            [grant],
        ]
    )

    result = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )
    replay = await ReverseOrderCodeApplicationsForRefundUseCase(session).execute(
        order_id=order_id,
        refund_id=refund_id,
        reversal_reason="refund_succeeded",
    )

    assert result.private_grants_revoked_count == 1
    assert grant.status == "revoked"
    assert grant.consumed_order_id == order_id
    assert grant.revoked_at is not None
    assert grant.revoked_reason == "refund_succeeded"
    assert grant.metadata_["last_reversal"]["status"] == "revoked"
    assert session.reversal_event.event_payload["private_grants_revoked_count"] == 1
    assert replay.private_grants_revoked_count == 0


@pytest.mark.asyncio
async def test_zero_payment_cancellation_releases_committed_reservation_and_runs_reversal_once() -> None:
    order_id = uuid4()
    reservation_id = uuid4()
    group_id = uuid4()
    order = SimpleNamespace(
        id=order_id,
        gateway_amount=Decimal("0"),
        order_status="committed",
        settlement_status="pending_internal_settlement",
    )
    application = _application(order_id=order_id, reservation_id=reservation_id)
    reservation = SimpleNamespace(
        id=reservation_id,
        reservation_group_id=group_id,
        status="committed",
        released_at=None,
        release_reason=None,
    )
    group = SimpleNamespace(
        id=group_id,
        status="committed",
        released_at=None,
        release_reason=None,
    )
    session = _Session(
        [
            [order],
            [application],
            [reservation],
            [group],
            [],
            [],
        ]
    )

    result = await ReverseZeroPaymentOrderCancellationUseCase(session).execute(
        order_id=order_id,
        reason_code="admin_zero_payment_cancelled",
    )

    assert order.order_status == "cancelled"
    assert order.settlement_status == "cancelled"
    assert result.reversed_count == 1
    assert result.reservations_released_count == 1
    assert reservation.status == "released"
    assert reservation.release_reason == "admin_zero_payment_cancelled"
    assert group.status == "released"
    assert group.release_reason == "admin_zero_payment_cancelled"
    assert application.application_snapshot["last_reversal"]["event_type"] == "zero_payment_cancellation"
    assert session.reversal_event.event_type == "zero_payment_cancellation"
    assert session.reversal_event.event_payload["reservations_released_count"] == 1


@pytest.mark.asyncio
async def test_refund_reversal_persists_event_and_application_snapshot_in_database() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    realm_id = uuid4()
    brand_id = uuid4()
    storefront_id = uuid4()
    user_id = uuid4()
    quote_id = uuid4()
    checkout_id = uuid4()
    order_id = uuid4()
    code_set_id = uuid4()
    growth_code_id = uuid4()
    application_id = uuid4()
    payment_id = uuid4()
    refund_id = uuid4()

    try:
        with sessionmaker() as db:
            db.execute(
                text(
                    """
                    INSERT INTO auth_realms (
                        id, realm_key, realm_type, display_name, audience, cookie_namespace
                    )
                    VALUES (:id, 'customer', 'customer', 'Customer', 'customer', 'customer')
                    """
                ),
                {"id": str(realm_id)},
            )
            db.execute(
                text("INSERT INTO brands (id, brand_key, display_name) VALUES (:id, 'cybervpn', 'CyberVPN')"),
                {"id": str(brand_id)},
            )
            db.execute(
                text(
                    """
                    INSERT INTO storefronts (id, storefront_key, brand_id, display_name, host, auth_realm_id)
                    VALUES (:id, 'official', :brand_id, 'Official', 'example.test', :realm_id)
                    """
                ),
                {"id": str(storefront_id), "brand_id": str(brand_id), "realm_id": str(realm_id)},
            )
            db.execute(
                text(
                    """
                    INSERT INTO mobile_users (id, public_uid, auth_realm_id, email, password_hash)
                    VALUES (:id, 10000001, :realm_id, 'customer@example.test', 'hash')
                    """
                ),
                {"id": str(user_id), "realm_id": str(realm_id)},
            )
            db.execute(
                text(
                    """
                    INSERT INTO quote_sessions (
                        id, user_id, auth_realm_id, storefront_id, request_snapshot,
                        quote_snapshot, context_snapshot, expires_at
                    )
                    VALUES (:id, :user_id, :realm_id, :storefront_id, '{}', '{}', '{}', :expires_at)
                    """
                ),
                {
                    "id": str(quote_id),
                    "user_id": str(user_id),
                    "realm_id": str(realm_id),
                    "storefront_id": str(storefront_id),
                    "expires_at": NOW.isoformat(),
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO checkout_sessions (
                        id, quote_session_id, user_id, auth_realm_id, storefront_id,
                        idempotency_key, request_snapshot, checkout_snapshot, context_snapshot, expires_at
                    )
                    VALUES (
                        :id, :quote_id, :user_id, :realm_id, :storefront_id,
                        'checkout-idem', '{}', '{}', '{}', :expires_at
                    )
                    """
                ),
                {
                    "id": str(checkout_id),
                    "quote_id": str(quote_id),
                    "user_id": str(user_id),
                    "realm_id": str(realm_id),
                    "storefront_id": str(storefront_id),
                    "expires_at": NOW.isoformat(),
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO growth_codes (
                        id, code_hash, code_prefix, code_type, issuer_type,
                        storefront_id, auth_realm_id
                    )
                    VALUES (:id, 'hash-1', 'PR', 'promo', 'admin', :storefront_id, :realm_id)
                    """
                ),
                {"id": str(growth_code_id), "storefront_id": str(storefront_id), "realm_id": str(realm_id)},
            )
            db.execute(
                text(
                    """
                    INSERT INTO checkout_code_sets (
                        id, code_set_hash, user_id, auth_realm_id, storefront_id,
                        sale_channel, action_context, status, acceptance_mode, order_id
                    )
                    VALUES (
                        :id, 'set-hash', :user_id, :realm_id, :storefront_id,
                        'web', 'checkout', 'consumed', 'strict', :order_id
                    )
                    """
                ),
                {
                    "id": str(code_set_id),
                    "user_id": str(user_id),
                    "realm_id": str(realm_id),
                    "storefront_id": str(storefront_id),
                    "order_id": str(order_id),
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO orders (
                        id, quote_session_id, checkout_session_id, user_id, auth_realm_id, storefront_id,
                        code_set_id, base_price, displayed_price, discount_amount, gateway_amount
                    )
                    VALUES (
                        :id, :quote_id, :checkout_id, :user_id, :realm_id, :storefront_id,
                        :code_set_id, 20.00, 15.00, 5.00, 15.00
                    )
                    """
                ),
                {
                    "id": str(order_id),
                    "quote_id": str(quote_id),
                    "checkout_id": str(checkout_id),
                    "user_id": str(user_id),
                    "realm_id": str(realm_id),
                    "storefront_id": str(storefront_id),
                    "code_set_id": str(code_set_id),
                },
            )
            db.execute(
                text(
                    """
                    INSERT INTO payments (
                        id, external_id, user_uuid, amount, currency, status, provider,
                        subscription_days, code_set_id, discount_amount, final_amount
                    )
                    VALUES (
                        :id, 'payment-1', :user_id, 15.00, 'USD', 'completed',
                        'manual', 30, :code_set_id, 5.00, 15.00
                    )
                    """
                ),
                {"id": str(payment_id), "user_id": str(user_id), "code_set_id": str(code_set_id)},
            )
            db.execute(
                text(
                    """
                    INSERT INTO refunds (
                        id, order_id, payment_id, refund_status, amount, currency_code,
                        provider, reason_code, idempotency_key
                    )
                    VALUES (
                        :id, :order_id, :payment_id, 'succeeded', 15.00, 'USD',
                        'manual', 'customer_request', 'refund-idem'
                    )
                    """
                ),
                {"id": str(refund_id), "order_id": str(order_id), "payment_id": str(payment_id)},
            )
            db.add(
                OrderCodeApplicationModel(
                    id=application_id,
                    order_id=order_id,
                    code_set_id=code_set_id,
                    growth_code_id=growth_code_id,
                    application_role="discount",
                    application_status="applied",
                    discount_amount=Decimal("5.00"),
                    currency_code="USD",
                    source_amount=Decimal("4.50"),
                    source_currency_code="EUR",
                    fx_conversion_id=UUID("00000000-0000-0000-0000-00000000f002"),
                    application_snapshot={"snapshot_version": "order_code_application.v6"},
                )
            )
            db.commit()

            result = await ReverseOrderCodeApplicationsForRefundUseCase(SyncSessionAdapter(db)).execute(
                order_id=order_id,
                refund_id=refund_id,
                reversal_reason="refund_succeeded",
                commit=True,
            )

            assert result.reversed_count == 1
            event = db.execute(select(GrowthReversalEventModel)).scalars().one()
            persisted_application = db.get(OrderCodeApplicationModel, application_id)
            assert event.event_type == "refund"
            assert event.refund_id == refund_id
            assert event.order_id == order_id
            assert event.idempotency_key == f"growth-reversal:refund:{refund_id}:order:{order_id}"
            assert event.event_payload["order_code_application_ids"] == [str(application_id)]
            assert event.event_payload["reversal_event_id"] == str(event.id)
            assert persisted_application is not None
            assert persisted_application.application_status == "reversed"
            assert persisted_application.application_snapshot["last_reversal"]["refund_id"] == str(refund_id)
            assert persisted_application.application_snapshot["last_reversal"]["applied_target_amount"] == "5.00000000"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
