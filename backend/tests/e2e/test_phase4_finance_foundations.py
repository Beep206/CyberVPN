from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.services.phase4_reconciliation import build_phase4_settlement_reconciliation_pack
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.e2e.test_phase4_settlement_foundations import (
    _quantize_money,
    _reserve_amount_for_event,
    _serialize_phase4_snapshot,
)
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


@pytest.mark.asyncio
async def test_phase4_finance_foundations_surface_and_reconciliation_gate(async_client: AsyncClient) -> None:
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
                    email="phase4-finance-owner@example.test",
                    password_hash=await auth_service.hash_password("Phase4FinanceOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="phase4-finance-workspace",
                    display_name="Phase4 Finance Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PH4FIN01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=12,
                    is_active=True,
                )
                maker_admin = AdminUserModel(
                    login="phase4_finance_maker",
                    email="phase4-finance-maker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase4FinanceMaker123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                checker_admin = AdminUserModel(
                    login="phase4_finance_checker",
                    email="phase4-finance-checker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase4FinanceChecker123!"),
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
                idempotency_key="phase4-finance-order",
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
                    idempotency_key="phase4-finance-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()
                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()
                earning_event_id = results["settlement_earning_event_id"]
                assert earning_event_id is not None

            earning_events_response = await async_client.get(
                f"/api/v1/earning-events/?partner_account_id={partner_account.id}",
                headers=maker_headers,
            )
            assert earning_events_response.status_code == 200
            earning_events = earning_events_response.json()
            assert len(earning_events) == 1
            assert earning_events[0]["order_id"] == order_payload["id"]

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
            hold_id = active_holds[0]["id"]

            hold_response = await async_client.get(
                f"/api/v1/earning-holds/{hold_id}",
                headers=maker_headers,
            )
            assert hold_response.status_code == 200
            assert hold_response.json()["hold_status"] == "active"

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-phase4-finance",
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
            assert initial_statement["on_hold_amount"] == _quantize_money(event_total_amount)
            assert initial_statement["available_amount"] == 0.0

            list_statements_response = await async_client.get(
                f"/api/v1/partner-statements/?partner_account_id={partner_account.id}",
                headers=maker_headers,
            )
            assert list_statements_response.status_code == 200
            statements = list_statements_response.json()
            assert len(statements) == 1
            assert statements[0]["id"] == initial_statement["id"]

            get_statement_response = await async_client.get(
                f"/api/v1/partner-statements/{initial_statement['id']}",
                headers=maker_headers,
            )
            assert get_statement_response.status_code == 200
            assert get_statement_response.json()["statement_status"] == "open"

            statement_adjustments_response = await async_client.get(
                f"/api/v1/partner-statements/{initial_statement['id']}/adjustments",
                headers=maker_headers,
            )
            assert statement_adjustments_response.status_code == 200
            assert statement_adjustments_response.json() == []

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{hold_id}/release",
                headers=maker_headers,
                json={"release_reason_code": "phase4_finance_ready", "force": True},
            )
            assert release_hold_response.status_code == 200
            assert release_hold_response.json()["hold_status"] == "released"

            reserve_response = await async_client.post(
                "/api/v1/reserves/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "amount": _quantize_money(reserve_amount),
                    "currency_code": "usd",
                    "reserve_scope": "partner_account",
                    "reserve_reason_type": "manual",
                    "reason_code": "phase4_finance_buffer",
                    "reserve_payload": {"source": "phase4-finance-e2e"},
                },
            )
            assert reserve_response.status_code == 201
            reserve_payload = reserve_response.json()
            assert reserve_payload["reserve_status"] == "active"

            list_reserves_response = await async_client.get(
                f"/api/v1/reserves/?partner_account_id={partner_account.id}&reserve_status=active",
                headers=maker_headers,
            )
            assert list_reserves_response.status_code == 200
            reserves = list_reserves_response.json()
            assert len(reserves) == 1
            assert reserves[0]["id"] == reserve_payload["id"]

            get_reserve_response = await async_client.get(
                f"/api/v1/reserves/{reserve_payload['id']}",
                headers=maker_headers,
            )
            assert get_reserve_response.status_code == 200
            assert get_reserve_response.json()["amount"] == _quantize_money(reserve_amount)

            refreshed_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=maker_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert refreshed_statement_response.status_code == 201
            refreshed_statement = refreshed_statement_response.json()
            assert refreshed_statement["reserve_amount"] == _quantize_money(reserve_amount)
            assert refreshed_statement["available_amount"] == _quantize_money(event_total_amount - reserve_amount)

            release_reserve_response = await async_client.post(
                f"/api/v1/reserves/{reserve_payload['id']}/release",
                headers=maker_headers,
                json={"release_reason_code": "phase4_finance_reserve_release"},
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
                    "display_label": "Phase4 Finance Primary",
                    "destination_reference": "UQA1234567890PHASE4FIN",
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

            payout_account_eligibility_response = await async_client.get(
                f"/api/v1/partner-payout-accounts/{payout_account_id}/eligibility",
                headers=maker_headers,
            )
            assert payout_account_eligibility_response.status_code == 200
            assert payout_account_eligibility_response.json()["eligible"] is True

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

            list_instructions_response = await async_client.get(
                f"/api/v1/payouts/instructions?partner_statement_id={closed_statement['id']}",
                headers=maker_headers,
            )
            assert list_instructions_response.status_code == 200
            instructions = list_instructions_response.json()
            assert len(instructions) == 1
            assert instructions[0]["id"] == instruction_payload["id"]

            approve_instruction_response = await async_client.post(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}/approve",
                headers=checker_headers,
            )
            assert approve_instruction_response.status_code == 200
            approved_instruction = approve_instruction_response.json()
            assert approved_instruction["instruction_status"] == "approved"

            get_instruction_response = await async_client.get(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}",
                headers=maker_headers,
            )
            assert get_instruction_response.status_code == 200
            assert get_instruction_response.json()["instruction_status"] == "approved"

            dry_run_execution_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-finance-execution-1"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "dry_run",
                    "execution_payload": {"batch": "phase4-finance-1"},
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
            assert reconcile_dry_run_response.json()["execution_status"] == "reconciled"

            list_executions_response = await async_client.get(
                f"/api/v1/payouts/executions?payout_instruction_id={instruction_payload['id']}",
                headers=maker_headers,
            )
            assert list_executions_response.status_code == 200
            executions = list_executions_response.json()
            assert len(executions) == 1
            assert executions[0]["execution_mode"] == "dry_run"
            assert executions[0]["execution_status"] == "reconciled"

            get_execution_response = await async_client.get(
                f"/api/v1/payouts/executions/{dry_run_execution['id']}",
                headers=maker_headers,
            )
            assert get_execution_response.status_code == 200
            assert get_execution_response.json()["execution_status"] == "reconciled"

            with sessionmaker() as db:
                snapshot = _serialize_phase4_snapshot(db, partner_account_id=partner_account.id)

            report = build_phase4_settlement_reconciliation_pack(snapshot)
            assert report["reconciliation"]["status"] == "green"
            assert report["liability_views"][0]["partner_account_id"] == str(partner_account.id)
            assert report["liability_views"][0]["statement_totals"]["closed_statement_available_amount"] == (
                closed_statement["available_amount"]
            )
            assert report["payout_views"][0]["instruction_status"] == "approved"
            assert report["payout_views"][0]["linked_execution_ids"] == [dry_run_execution["id"]]
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
