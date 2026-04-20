from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
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

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_payout_instruction_maker_checker_and_execution_workflow(async_client: AsyncClient) -> None:
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
                    email="payout-workflow-owner@example.test",
                    password_hash=await auth_service.hash_password("PayoutWorkflowOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="payout-workflow-workspace",
                    display_name="Payout Workflow Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PAYOUTFLOW01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=20,
                    is_active=True,
                )
                maker_admin = AdminUserModel(
                    login="payout_maker",
                    email="payout-maker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PayoutMaker123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                checker_admin = AdminUserModel(
                    login="payout_checker",
                    email="payout-checker@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("PayoutChecker123!"),
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
                idempotency_key="phase4-payout-order",
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
                    idempotency_key="phase4-payout-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()
                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id)
                db.commit()
                assert results["settlement_earning_event_id"] is not None
                earning_event_id = results["settlement_earning_event_id"]

            active_holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={earning_event_id}&hold_status=active",
                headers=maker_headers,
            )
            assert active_holds_response.status_code == 200
            active_holds = active_holds_response.json()
            assert len(active_holds) == 1

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{active_holds[0]['id']}/release",
                headers=maker_headers,
                json={"release_reason_code": "payout_instruction_ready", "force": True},
            )
            assert release_hold_response.status_code == 200

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-payout-workflow",
                    "currency_code": "usd",
                    "window_start": "2026-04-01T00:00:00Z",
                    "window_end": "2026-05-01T00:00:00Z",
                },
            )
            assert period_response.status_code == 201
            period_payload = period_response.json()

            statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=maker_headers,
                json={"settlement_period_id": period_payload["id"]},
            )
            assert statement_response.status_code == 201
            statement_payload = statement_response.json()

            close_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_payload['id']}/close",
                headers=maker_headers,
            )
            assert close_statement_response.status_code == 200
            closed_statement = close_statement_response.json()
            assert closed_statement["statement_status"] == "closed"
            assert closed_statement["available_amount"] > 0

            payout_account_response = await async_client.post(
                "/api/v1/partner-payout-accounts/",
                headers=maker_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "payout_rail": "cryptobot",
                    "display_label": "Finance Primary",
                    "destination_reference": "UQA1234567890PAYOUT",
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

            repeat_instruction_response = await async_client.post(
                "/api/v1/payouts/instructions",
                headers=maker_headers,
                json={
                    "partner_statement_id": closed_statement["id"],
                    "partner_payout_account_id": payout_account_id,
                },
            )
            assert repeat_instruction_response.status_code == 200
            assert repeat_instruction_response.json()["id"] == instruction_payload["id"]

            maker_approval_response = await async_client.post(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}/approve",
                headers=maker_headers,
            )
            assert maker_approval_response.status_code == 409

            approve_instruction_response = await async_client.post(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}/approve",
                headers=checker_headers,
            )
            assert approve_instruction_response.status_code == 200
            approved_instruction = approve_instruction_response.json()
            assert approved_instruction["instruction_status"] == "approved"

            dry_run_execution_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-payout-dry-run-1"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "dry_run",
                    "execution_payload": {"batch": "dry-run-1"},
                },
            )
            assert dry_run_execution_response.status_code == 201
            dry_run_execution = dry_run_execution_response.json()
            assert dry_run_execution["execution_status"] == "requested"

            repeat_dry_run_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-payout-dry-run-1"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "dry_run",
                    "execution_payload": {"batch": "dry-run-1"},
                },
            )
            assert repeat_dry_run_response.status_code == 200
            assert repeat_dry_run_response.json()["id"] == dry_run_execution["id"]

            active_execution_conflict_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-payout-live-conflict"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "live",
                    "execution_payload": {"batch": "live-conflict"},
                },
            )
            assert active_execution_conflict_response.status_code == 409

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
                json={"reconciliation_payload": {"type": "dry_run_close"}},
            )
            assert reconcile_dry_run_response.status_code == 200
            assert reconcile_dry_run_response.json()["execution_status"] == "reconciled"

            post_dry_run_instruction_response = await async_client.get(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}",
                headers=maker_headers,
            )
            assert post_dry_run_instruction_response.status_code == 200
            assert post_dry_run_instruction_response.json()["instruction_status"] == "approved"
            assert post_dry_run_instruction_response.json()["completed_at"] is None

            live_execution_response = await async_client.post(
                "/api/v1/payouts/executions",
                headers={**maker_headers, "Idempotency-Key": "phase4-payout-live-1"},
                json={
                    "payout_instruction_id": instruction_payload["id"],
                    "execution_mode": "live",
                    "execution_payload": {"batch": "live-1"},
                },
            )
            assert live_execution_response.status_code == 201
            live_execution = live_execution_response.json()
            assert live_execution["execution_status"] == "requested"

            submit_live_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{live_execution['id']}/submit",
                headers=maker_headers,
                json={
                    "external_reference": "provider-payout-001",
                    "submission_payload": {"rail_status": "submitted"},
                },
            )
            assert submit_live_execution_response.status_code == 200
            assert submit_live_execution_response.json()["execution_status"] == "submitted"

            complete_live_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{live_execution['id']}/complete",
                headers=maker_headers,
                json={
                    "external_reference": "provider-payout-001",
                    "completion_payload": {"rail_status": "settled"},
                },
            )
            assert complete_live_execution_response.status_code == 200
            assert complete_live_execution_response.json()["execution_status"] == "succeeded"

            reconcile_live_execution_response = await async_client.post(
                f"/api/v1/payouts/executions/{live_execution['id']}/reconcile",
                headers=maker_headers,
                json={"reconciliation_payload": {"ledger_match": True}},
            )
            assert reconcile_live_execution_response.status_code == 200
            reconciled_live_execution = reconcile_live_execution_response.json()
            assert reconciled_live_execution["execution_status"] == "reconciled"

            final_instruction_response = await async_client.get(
                f"/api/v1/payouts/instructions/{instruction_payload['id']}",
                headers=maker_headers,
            )
            assert final_instruction_response.status_code == 200
            final_instruction = final_instruction_response.json()
            assert final_instruction["instruction_status"] == "completed"
            assert final_instruction["completed_at"] is not None

            list_instructions_response = await async_client.get(
                f"/api/v1/payouts/instructions?partner_account_id={partner_account.id}",
                headers=maker_headers,
            )
            assert list_instructions_response.status_code == 200
            assert len(list_instructions_response.json()) == 1

            list_executions_response = await async_client.get(
                f"/api/v1/payouts/executions?payout_instruction_id={instruction_payload['id']}",
                headers=maker_headers,
            )
            assert list_executions_response.status_code == 200
            executions = list_executions_response.json()
            assert len(executions) == 2
            assert {item["execution_mode"] for item in executions} == {"dry_run", "live"}
            assert {item["execution_status"] for item in executions} == {"reconciled"}
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
