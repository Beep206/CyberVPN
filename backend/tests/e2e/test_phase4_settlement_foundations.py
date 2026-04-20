from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.services.phase4_reconciliation import build_phase4_settlement_reconciliation_pack
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.earning_hold_model import EarningHoldModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.payout_execution_model import PayoutExecutionModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.models.reserve_model import ReserveModel
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    FakeRedis,
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_order_attribution_resolution import _create_quote_checkout, _make_admin_token
from tests.integration.test_order_commit import _make_customer_access_token, _seed_order_context

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

_PENNY = Decimal("0.01")


def _quantize_money(value: Decimal) -> float:
    return float(value.quantize(_PENNY, rounding=ROUND_HALF_UP))


def _reserve_amount_for_event(total_amount: Decimal) -> Decimal:
    candidate = min(Decimal("1.25"), max(Decimal("0.25"), total_amount / Decimal("4")))
    reserve_amount = candidate.quantize(_PENNY, rounding=ROUND_HALF_UP)
    if reserve_amount >= total_amount:
        reserve_amount = (total_amount / Decimal("2")).quantize(_PENNY, rounding=ROUND_HALF_UP)
    return max(reserve_amount, Decimal("0.01"))


def _serialize_phase4_snapshot(db, *, partner_account_id: uuid.UUID) -> dict:
    earning_events = db.execute(
        select(EarningEventModel).where(EarningEventModel.partner_account_id == partner_account_id)
    ).scalars().all()
    earning_holds = db.execute(
        select(EarningHoldModel).where(EarningHoldModel.partner_account_id == partner_account_id)
    ).scalars().all()
    reserves = db.execute(
        select(ReserveModel).where(ReserveModel.partner_account_id == partner_account_id)
    ).scalars().all()
    partner_statements = db.execute(
        select(PartnerStatementModel).where(PartnerStatementModel.partner_account_id == partner_account_id)
    ).scalars().all()
    statement_ids = [item.id for item in partner_statements]
    payout_instructions = db.execute(
        select(PayoutInstructionModel).where(PayoutInstructionModel.partner_account_id == partner_account_id)
    ).scalars().all()
    payout_executions = db.execute(
        select(PayoutExecutionModel).where(PayoutExecutionModel.partner_account_id == partner_account_id)
    ).scalars().all()
    statement_adjustments = (
        db.execute(
            select(StatementAdjustmentModel).where(StatementAdjustmentModel.partner_statement_id.in_(statement_ids))
        ).scalars().all()
        if statement_ids
        else []
    )

    return {
        "metadata": {
            "snapshot_id": "phase4-e2e-dry-run",
            "source": "phase4-settlement-foundations-e2e",
            "replay_generated_at": "2026-04-18T18:00:00+00:00",
        },
        "earning_events": [
            {
                "id": item.id,
                "partner_account_id": item.partner_account_id,
                "event_status": item.event_status,
                "total_amount": item.total_amount,
                "currency_code": item.currency_code,
                "created_at": item.created_at,
            }
            for item in earning_events
        ],
        "earning_holds": [
            {
                "id": item.id,
                "earning_event_id": item.earning_event_id,
                "partner_account_id": item.partner_account_id,
                "hold_status": item.hold_status,
                "created_at": item.created_at,
            }
            for item in earning_holds
        ],
        "reserves": [
            {
                "id": item.id,
                "partner_account_id": item.partner_account_id,
                "source_earning_event_id": item.source_earning_event_id,
                "reserve_scope": item.reserve_scope,
                "reserve_reason_type": item.reserve_reason_type,
                "reserve_status": item.reserve_status,
                "amount": item.amount,
                "currency_code": item.currency_code,
                "reason_code": item.reason_code,
                "created_at": item.created_at,
            }
            for item in reserves
        ],
        "partner_statements": [
            {
                "id": item.id,
                "partner_account_id": item.partner_account_id,
                "settlement_period_id": item.settlement_period_id,
                "statement_status": item.statement_status,
                "statement_version": item.statement_version,
                "superseded_by_statement_id": item.superseded_by_statement_id,
                "reopened_from_statement_id": item.reopened_from_statement_id,
                "currency_code": item.currency_code,
                "accrual_amount": item.accrual_amount,
                "on_hold_amount": item.on_hold_amount,
                "reserve_amount": item.reserve_amount,
                "adjustment_net_amount": item.adjustment_net_amount,
                "available_amount": item.available_amount,
                "source_event_count": item.source_event_count,
                "held_event_count": item.held_event_count,
                "active_reserve_count": item.active_reserve_count,
                "adjustment_count": item.adjustment_count,
                "statement_snapshot": item.statement_snapshot,
                "created_at": item.created_at,
            }
            for item in partner_statements
        ],
        "statement_adjustments": [
            {
                "id": item.id,
                "partner_statement_id": item.partner_statement_id,
                "partner_account_id": item.partner_account_id,
                "source_reference_type": item.source_reference_type,
                "source_reference_id": item.source_reference_id,
                "adjustment_type": item.adjustment_type,
                "adjustment_direction": item.adjustment_direction,
                "amount": item.amount,
                "currency_code": item.currency_code,
                "created_at": item.created_at,
            }
            for item in statement_adjustments
        ],
        "payout_instructions": [
            {
                "id": item.id,
                "partner_account_id": item.partner_account_id,
                "partner_statement_id": item.partner_statement_id,
                "partner_payout_account_id": item.partner_payout_account_id,
                "instruction_status": item.instruction_status,
                "payout_amount": item.payout_amount,
                "currency_code": item.currency_code,
                "created_at": item.created_at,
            }
            for item in payout_instructions
        ],
        "payout_executions": [
            {
                "id": item.id,
                "payout_instruction_id": item.payout_instruction_id,
                "partner_account_id": item.partner_account_id,
                "partner_statement_id": item.partner_statement_id,
                "partner_payout_account_id": item.partner_payout_account_id,
                "execution_mode": item.execution_mode,
                "execution_status": item.execution_status,
                "created_at": item.created_at,
            }
            for item in payout_executions
        ],
    }


@pytest.mark.asyncio
async def test_phase4_settlement_foundations_end_to_end(async_client: AsyncClient) -> None:
    auth_service = AuthService()
    fake_redis = FakeRedis()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    async def _override_redis():
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_order_context(sessionmaker, auth_service)
            customer_realm = AuthRealmModel(
                id=uuid.UUID(seeded["customer_realm_id"]),
                realm_key=seeded["customer_realm_key"],
                realm_type="customer",
                display_name="Customer Realm",
                audience=seeded["customer_realm_audience"],
                cookie_namespace="customer",
                status="active",
                is_default=True,
            )

            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="phase4-dry-run-owner@example.test",
                    password_hash=await auth_service.hash_password("Phase4DryRunOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="phase4-dry-run-workspace",
                    display_name="Phase4 Dry Run Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PH4DRY01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                maker_admin = AdminUserModel(
                    login="phase4_dry_run_maker",
                    email="phase4-dry-run-maker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase4DryRunMaker123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                checker_admin = AdminUserModel(
                    login="phase4_dry_run_checker",
                    email="phase4-dry-run-checker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase4DryRunChecker123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, partner_account, partner_code, maker_admin, checker_admin])
                db.commit()
                maker_token = _make_admin_token(auth_service, user_id=maker_admin.id, realm=admin_realm)
                checker_token = _make_admin_token(auth_service, user_id=checker_admin.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            maker_headers = {
                "Authorization": f"Bearer {maker_token}",
                "X-Auth-Realm": "admin",
            }
            checker_headers = {
                "Authorization": f"Bearer {checker_token}",
                "X-Auth-Realm": "admin",
            }

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="phase4-dry-run-order",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal(str(order_payload["displayed_price"])),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    partner_code_id=partner_code.id,
                    metadata_={"commission_base_amount": str(order_payload["commission_base_amount"])},
                )
                attempt = PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=uuid.UUID(order_payload["id"]),
                    payment_id=payment.id,
                    attempt_number=1,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status="succeeded",
                    displayed_amount=Decimal(str(order_payload["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(order_payload["gateway_amount"])),
                    idempotency_key="phase4-dry-run-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()
                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()
                earning_event_id = results["settlement_earning_event_id"]
                assert earning_event_id is not None

            earning_event_response = await async_client.get(
                f"/api/v1/earning-events/{earning_event_id}",
                headers=maker_headers,
            )
            assert earning_event_response.status_code == 200
            earning_event_payload = earning_event_response.json()
            assert earning_event_payload["event_status"] == "on_hold"
            event_total_amount = Decimal(str(earning_event_payload["total_amount"]))
            reserve_amount = _reserve_amount_for_event(event_total_amount)

            active_holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={earning_event_id}&hold_status=active",
                headers=maker_headers,
            )
            assert active_holds_response.status_code == 200
            active_holds = active_holds_response.json()
            assert len(active_holds) == 1

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-phase4-dry-run",
                    "currency_code": "usd",
                    "window_start": "2026-04-01T00:00:00Z",
                    "window_end": "2026-05-01T00:00:00Z",
                },
            )
            assert period_response.status_code == 201
            period_payload = period_response.json()

            initial_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=maker_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert initial_statement_response.status_code == 201
            initial_statement = initial_statement_response.json()
            assert initial_statement["held_event_count"] == 1
            assert initial_statement["on_hold_amount"] == _quantize_money(event_total_amount)
            assert initial_statement["available_amount"] == 0.0

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{active_holds[0]['id']}/release",
                headers=maker_headers,
                json={"release_reason_code": "phase4_dry_run_ready", "force": True},
            )
            assert release_hold_response.status_code == 200

            reserve_response = await async_client.post(
                "/api/v1/reserves/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "amount": _quantize_money(reserve_amount),
                    "currency_code": "usd",
                    "reserve_scope": "partner_account",
                    "reserve_reason_type": "manual",
                    "reason_code": "phase4_dry_run_buffer",
                    "reserve_payload": {"source": "phase4-dry-run-e2e"},
                },
            )
            assert reserve_response.status_code == 201
            reserve_payload = reserve_response.json()
            assert reserve_payload["reserve_status"] == "active"

            refreshed_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=maker_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert refreshed_statement_response.status_code == 201
            refreshed_statement = refreshed_statement_response.json()
            assert refreshed_statement["id"] == initial_statement["id"]
            assert refreshed_statement["held_event_count"] == 0
            assert refreshed_statement["reserve_amount"] == _quantize_money(reserve_amount)
            assert refreshed_statement["available_amount"] == _quantize_money(event_total_amount - reserve_amount)

            release_reserve_response = await async_client.post(
                f"/api/v1/reserves/{reserve_payload['id']}/release",
                headers=maker_headers,
                json={"release_reason_code": "phase4_dry_run_reserve_release"},
            )
            assert release_reserve_response.status_code == 200
            assert release_reserve_response.json()["reserve_status"] == "released"

            payout_ready_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=maker_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert payout_ready_statement_response.status_code == 201
            payout_ready_statement = payout_ready_statement_response.json()
            assert payout_ready_statement["reserve_amount"] == 0.0
            assert payout_ready_statement["available_amount"] == _quantize_money(event_total_amount)

            close_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{payout_ready_statement['id']}/close",
                headers=maker_headers,
            )
            assert close_statement_response.status_code == 200
            closed_statement = close_statement_response.json()
            assert closed_statement["statement_status"] == "closed"

            payout_account_response = await async_client.post(
                "/api/v1/partner-payout-accounts/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "payout_rail": "cryptobot",
                    "display_label": "Phase4 Dry Run Primary",
                    "destination_reference": "UQA1234567890PHASE4DRY",
                    "destination_metadata": {"network": "TRC20"},
                    "make_default": True,
                },
            )
            assert payout_account_response.status_code == 201
            payout_account_id = payout_account_response.json()["id"]

            verify_payout_account_response = await async_client.post(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/verify",
                headers=maker_headers,
            )
            assert verify_payout_account_response.status_code == 200

            create_instruction_response = await async_client.post(
                "/api/v1/payouts/instructions",
                headers=maker_headers,
                json={
                    "partner_statement_id": closed_statement["id"],
                    "partner_payout_account_id": payout_account_id,
                },
            )
            assert create_instruction_response.status_code == 201
            instruction_payload = create_instruction_response.json()
            assert instruction_payload["instruction_status"] == "pending_approval"

            approve_instruction_response = await async_client.post(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}/approve",
                headers=checker_headers,
            )
            assert approve_instruction_response.status_code == 200
            approved_instruction = approve_instruction_response.json()
            assert approved_instruction["instruction_status"] == "approved"

            dry_run_execution_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-dry-run-execution-1"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "dry_run",
                    "execution_payload": {"batch": "phase4-dry-run-1"},
                },
            )
            assert dry_run_execution_response.status_code == 201
            dry_run_execution = dry_run_execution_response.json()
            assert dry_run_execution["execution_status"] == "requested"

            complete_dry_run_response = await async_client.post(
                f"/api/v1/payouts/executions/{dry_run_execution['id']}/complete",
                headers=maker_headers,
                json={"completion_payload": {"result": "dry_run_passed"}},
            )
            assert complete_dry_run_response.status_code == 200
            assert complete_dry_run_response.json()["execution_status"] == "succeeded"

            reconcile_dry_run_response = await async_client.post(
                f"/api/v1/payouts/executions/{dry_run_execution['id']}/reconcile",
                headers=maker_headers,
                json={"reconciliation_payload": {"type": "dry_run_close", "ledger_match": True}},
            )
            assert reconcile_dry_run_response.status_code == 200
            reconciled_execution = reconcile_dry_run_response.json()
            assert reconciled_execution["execution_status"] == "reconciled"

            post_dry_run_instruction_response = await async_client.get(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}",
                headers=maker_headers,
            )
            assert post_dry_run_instruction_response.status_code == 200
            assert post_dry_run_instruction_response.json()["instruction_status"] == "approved"
            assert post_dry_run_instruction_response.json()["completed_at"] is None

            list_executions_response = await async_client.get(
                f"/api/v1/payouts/executions?payout_instruction_id={instruction_payload['id']}",
                headers=maker_headers,
            )
            assert list_executions_response.status_code == 200
            executions = list_executions_response.json()
            assert len(executions) == 1
            assert executions[0]["execution_mode"] == "dry_run"
            assert executions[0]["execution_status"] == "reconciled"

            with sessionmaker() as db:
                snapshot = _serialize_phase4_snapshot(db, partner_account_id=partner_account.id)

            report = build_phase4_settlement_reconciliation_pack(snapshot)
            assert report["reconciliation"]["status"] == "green"
            assert report["liability_views"][0]["partner_account_id"] == str(partner_account.id)
            assert report["liability_views"][0]["event_status_totals"]["accrual_amount"] == _quantize_money(
                event_total_amount
            )
            assert report["liability_views"][0]["reserve_totals"]["total_active_reserve_amount"] == 0.0
            assert report["liability_views"][0]["statement_totals"]["closed_statement_available_amount"] == (
                closed_statement["available_amount"]
            )
            assert report["liability_views"][0]["payout_totals"]["completed_amount"] == 0.0
            assert report["liability_views"][0]["liability_totals"]["outstanding_statement_liability_amount"] == (
                closed_statement["available_amount"]
            )
            assert report["statement_views"][0]["statement_status"] == "closed"
            assert report["payout_views"][0]["instruction_status"] == "approved"
            assert len(report["payout_views"][0]["linked_execution_ids"]) == 1
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
