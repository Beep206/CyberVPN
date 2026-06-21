from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from src.application.services.auth_service import AuthService
from src.application.use_cases.payments.payment_completed_earnings import (
    PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
    RunPaymentCompletedEarningOutboxUseCase,
)
from src.application.use_cases.payments.post_payment import PostPaymentProcessingUseCase
from src.application.use_cases.settlement.commission_terms import build_commission_contract_model
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.earning_hold_model import EarningHoldModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel
from src.infrastructure.database.models.outbox_consumer_receipt_model import OutboxConsumerReceiptModel
from src.infrastructure.database.models.outbox_event_model import OutboxEventModel, OutboxPublicationModel
from src.infrastructure.database.models.partner_model import (
    PartnerAccountModel,
    PartnerCodeModel,
    PartnerCommissionContractModel,
    PartnerEarningModel,
)
from src.infrastructure.database.models.payment_attempt_model import PaymentAttemptModel
from src.infrastructure.database.models.payment_model import PaymentModel
from src.infrastructure.database.models.pricebook_model import PricebookModel
from src.infrastructure.database.models.system_config_model import SystemConfigModel
from src.infrastructure.database.models.wallet_model import WalletTransactionModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from src.presentation.api.v1.webhooks import routes as webhook_routes
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
async def test_partner_settlement_foundations_dual_write_and_manual_controls(async_client: AsyncClient) -> None:
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
                    email="settlement-owner@example.test",
                    password_hash=await auth_service.hash_password("SettlementOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="settlement-workspace",
                    display_name="Settlement Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="SETTLE01",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="settlement_admin",
                    email="settlement-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SettlementAdmin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="settlement_support",
                    email="settlement-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("SettlementSupport123!"),
                    role="support",
                    is_active=True,
                    is_email_verified=True,
                )
                db.add_all([partner_owner, partner_account, partner_code, admin_user, support_user])
                db.commit()
                admin_token = _make_admin_token(auth_service, user_id=admin_user.id, realm=admin_realm)
                support_token = _make_admin_token(auth_service, user_id=support_user.id, realm=admin_realm)

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }
            admin_headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }
            support_headers = {
                "Authorization": f"Bearer {support_token}",
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
                idempotency_key="phase4-settlement-order",
            )
            with sessionmaker() as db:
                quoted_code = db.get(PartnerCodeModel, partner_code.id)
                assert quoted_code is not None
                original_commission_contract_id = quoted_code.commission_contract_id
                assert original_commission_contract_id is not None
                original_contract = db.get(PartnerCommissionContractModel, original_commission_contract_id)
                assert original_contract is not None
                assert original_contract.terms_snapshot["markup_pct"] == "15.00"

                quoted_code.markup_pct = Decimal("25")
                quoted_code.version = int(quoted_code.version or 1) + 1
                rotated_contract = build_commission_contract_model(
                    code_model=quoted_code,
                    commission_pct=Decimal("20"),
                    payout_hold_days=30,
                    source="test_rotate_after_quote_before_order",
                    contract_id=uuid.uuid4(),
                )
                db.add(rotated_contract)
                db.flush()
                quoted_code.commission_contract_id = rotated_contract.id
                db.commit()
                assert rotated_contract.id != original_commission_contract_id

            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            with sessionmaker() as db:
                attribution_result = (
                    db.query(OrderAttributionResultModel)
                    .filter(OrderAttributionResultModel.order_id == uuid.UUID(order_payload["id"]))
                    .one()
                )
                assert attribution_result.commission_contract_id is not None
                assert attribution_result.commission_contract_id == original_commission_contract_id
                commission_snapshot = attribution_result.policy_snapshot["commercial_policy_snapshot"][
                    "commission_contract_snapshot"
                ]
                assert commission_snapshot["snapshot_complete"] is True
                assert commission_snapshot["commission_contract_id"] == str(original_commission_contract_id)
                assert commission_snapshot["markup_pct"] == "15.00"
                assert commission_snapshot["commission_pct"] == "20"

                contract = db.get(PartnerCommissionContractModel, attribution_result.commission_contract_id)
                assert contract is not None
                original_contract_snapshot = dict(contract.terms_snapshot)
                mutated_contract_snapshot = dict(contract.terms_snapshot)
                mutated_contract_snapshot["markup_pct"] = "99"
                mutated_contract_snapshot["commission_pct"] = "99"
                mutated_contract_snapshot["payout_hold_days"] = 2
                contract.markup_pct = Decimal("99")
                contract.commission_pct = Decimal("99")
                contract.payout_hold_days = 2
                contract.terms_snapshot = mutated_contract_snapshot

                mutable_code = db.get(PartnerCodeModel, partner_code.id)
                assert mutable_code is not None
                mutable_code.markup_pct = Decimal("99")
                db.merge(
                    SystemConfigModel(
                        key="partner.tiers",
                        value={"tiers": [{"min_clients": 0, "commission_pct": 99}]},
                        description="mutable config changed after order commit",
                    )
                )
                db.merge(
                    SystemConfigModel(
                        key="affiliate.payout_hold_days",
                        value={"days": 2},
                        description="mutable hold changed after order commit",
                    )
                )
                db.commit()
                assert original_contract_snapshot["markup_pct"] == "15.00"

            with sessionmaker() as db:
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    external_id="4242424242",
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal(str(order_payload["displayed_price"])),
                    currency="USD",
                    status="pending",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=uuid.UUID(seeded["plan_id"]),
                    partner_code_id=partner_code.id,
                    metadata_={"commission_base_amount": "999.99"},
                )
                attempt = PaymentAttemptModel(
                    id=uuid.uuid4(),
                    order_id=uuid.UUID(order_payload["id"]),
                    payment_id=payment.id,
                    attempt_number=1,
                    provider="cryptobot",
                    sale_channel="web",
                    currency_code="USD",
                    status="pending",
                    displayed_amount=Decimal(str(order_payload["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(order_payload["gateway_amount"])),
                    idempotency_key="phase4-settlement-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()
                payment_id = payment.id
                attempt_id = attempt.id

            original_cryptobot_token = webhook_routes.settings.cryptobot_token
            webhook_routes.settings.cryptobot_token = SecretStr("settlement-webhook-route-token")
            webhook_payload = {
                "update_type": "invoice_paid",
                "payload": {"invoice_id": "4242424242", "status": "paid"},
            }
            webhook_body = json.dumps(webhook_payload, separators=(",", ":")).encode("utf-8")
            webhook_secret = hashlib.sha256(b"settlement-webhook-route-token").digest()
            webhook_signature = hmac.new(webhook_secret, webhook_body, hashlib.sha256).hexdigest()
            try:
                webhook_response = await async_client.post(
                    "/api/v1/webhooks/cryptobot",
                    content=webhook_body,
                    headers={
                        "Content-Type": "application/json",
                        "crypto-pay-api-signature": webhook_signature,
                    },
                )
                duplicate_webhook_response = await async_client.post(
                    "/api/v1/webhooks/cryptobot",
                    content=webhook_body,
                    headers={
                        "Content-Type": "application/json",
                        "crypto-pay-api-signature": webhook_signature,
                    },
                )
            finally:
                webhook_routes.settings.cryptobot_token = original_cryptobot_token

            assert webhook_response.status_code == 200
            webhook_result = webhook_response.json()
            duplicate_webhook_result = duplicate_webhook_response.json()
            deferred_results = webhook_result["post_payment"]
            assert duplicate_webhook_response.status_code == 200

            with sessionmaker() as db:
                adapter = SyncSessionAdapter(db)
                assert webhook_result["status"] == "processed"
                assert duplicate_webhook_result["status"] == "already_processed"
                assert deferred_results["cash_rewards_deferred"] is True
                payment = db.get(PaymentModel, payment_id)
                assert payment is not None
                attempt = db.get(PaymentAttemptModel, attempt_id)
                assert attempt is not None
                db.refresh(payment)
                db.refresh(attempt)
                assert payment.status == "completed"
                assert attempt.status == "succeeded"
                assert db.query(EarningEventModel).filter(EarningEventModel.payment_id == payment.id).count() == 0
                assert (
                    db.query(OutboxEventModel)
                    .filter(OutboxEventModel.event_key == f"payment.completed:{payment.id}")
                    .count()
                    == 1
                )
                assert (
                    db.query(OutboxPublicationModel)
                    .join(OutboxEventModel, OutboxEventModel.id == OutboxPublicationModel.outbox_event_id)
                    .filter(
                        OutboxEventModel.event_key == f"payment.completed:{payment.id}",
                        OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                    )
                    .count()
                    == 1
                )
                pre_worker_completed_event = (
                    db.query(OutboxEventModel)
                    .filter(OutboxEventModel.event_key == f"payment.completed:{payment.id}")
                    .one()
                )
                db.delete(pre_worker_completed_event)
                db.commit()

                worker_result = await RunPaymentCompletedEarningOutboxUseCase(adapter).execute(
                    limit=10,
                    worker_id="test-partner-earning-worker",
                )
                db.commit()
                assert worker_result["claimed"] == 1
                assert worker_result["succeeded"] == 1
                assert worker_result["retrying"] == 0
                assert worker_result["dead_letter"] == 0
                assert worker_result["backfilled"]["created_events"] == 1
                assert worker_result["backfilled"]["ensured_publications"] == 1

                persisted_event = db.query(EarningEventModel).filter(EarningEventModel.payment_id == payment.id).one()
                event_id = str(persisted_event.id)
                assert persisted_event.commission_base_amount == Decimal("75.00")
                assert persisted_event.markup_amount == Decimal("11.25")
                assert persisted_event.commission_pct == Decimal("20.00")
                assert persisted_event.commission_amount == Decimal("15.00")
                assert persisted_event.total_amount == Decimal("26.25")
                assert persisted_event.earning_component == "partner_cash"
                assert persisted_event.calculation_snapshot["calculator_version"] == "partner_earning_v3"
                assert Decimal(str(persisted_event.calculation_snapshot["markup_pct"])) == Decimal("15.00")
                assert Decimal(str(persisted_event.calculation_snapshot["commission_pct"])) == Decimal("20.00")
                assert persisted_event.calculation_snapshot["payout_hold_days"] == 30
                assert persisted_event.calculation_snapshot["commission_contract_snapshot"][
                    "commission_contract_id"
                ] == str(persisted_event.commission_contract_id)
                assert persisted_event.calculation_snapshot["commission_contract_snapshot"]["markup_pct"] == "15.00"
                assert persisted_event.calculation_snapshot["commission_contract_snapshot"]["commission_pct"] == "20"
                assert persisted_event.source_snapshot["requested_commission_base_amount"] == "75.00"
                assert persisted_event.source_snapshot["order_commission_base_amount"] == "75.00"
                completed_event = (
                    db.query(OutboxEventModel)
                    .filter(OutboxEventModel.event_key == f"payment.completed:{payment.id}")
                    .one()
                )
                completed_publication = (
                    db.query(OutboxPublicationModel)
                    .filter(
                        OutboxPublicationModel.outbox_event_id == completed_event.id,
                        OutboxPublicationModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                    )
                    .one()
                )
                assert completed_publication.publication_status == "published"
                receipt = (
                    db.query(OutboxConsumerReceiptModel)
                    .filter(
                        OutboxConsumerReceiptModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                        OutboxConsumerReceiptModel.event_key == completed_event.event_key,
                    )
                    .one()
                )
                assert receipt.status == "processed"
                assert receipt.metadata_payload["settlement_earning_event_id"] == str(persisted_event.id)
                persisted_hold = (
                    db.query(EarningHoldModel).filter(EarningHoldModel.earning_event_id == persisted_event.id).one()
                )
                assert persisted_hold.hold_payload["hold_days"] == 30

                completed_publication.publication_status = "pending"
                completed_publication.lease_owner = None
                completed_publication.leased_until = None
                completed_publication.attempts = 0
                db.commit()
                replay_result = await RunPaymentCompletedEarningOutboxUseCase(adapter).execute(
                    limit=10,
                    worker_id="test-partner-earning-worker-replay",
                )
                db.commit()
                assert replay_result["claimed"] == 1
                assert replay_result["succeeded"] == 1
                assert db.query(EarningEventModel).filter(EarningEventModel.payment_id == payment.id).count() == 1
                assert (
                    db.query(EarningHoldModel)
                    .join(EarningEventModel, EarningEventModel.id == EarningHoldModel.earning_event_id)
                    .filter(EarningEventModel.payment_id == payment.id)
                    .count()
                    == 1
                )
                assert (
                    db.query(OutboxConsumerReceiptModel)
                    .filter(
                        OutboxConsumerReceiptModel.consumer_key == PAYMENT_COMPLETED_PARTNER_EARNING_CONSUMER,
                        OutboxConsumerReceiptModel.event_key == completed_event.event_key,
                    )
                    .count()
                    == 1
                )

            event_response = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_response.status_code == 200
            event_payload = event_response.json()
            assert event_payload["order_id"] == order_payload["id"]
            assert event_payload["partner_account_id"] == str(partner_account.id)
            assert event_payload["event_status"] == "on_hold"

            holds_response = await async_client.get(
                f"/api/v1/earning-holds/?earning_event_id={event_id}&hold_status=active",
                headers=support_headers,
            )
            assert holds_response.status_code == 200
            holds_payload = holds_response.json()
            assert len(holds_payload) == 1
            hold_id = holds_payload[0]["id"]
            assert holds_payload[0]["hold_reason_type"] == "payout_hold"

            release_hold_response = await async_client.post(
                f"/api/v1/earning-holds/{hold_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "manual_internal_release", "force": True},
            )
            assert release_hold_response.status_code == 200
            assert release_hold_response.json()["hold_status"] == "released"

            event_after_hold_release = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_after_hold_release.status_code == 200
            assert event_after_hold_release.json()["event_status"] == "available"
            assert event_after_hold_release.json()["available_at"] is not None

            reserve_response = await async_client.post(
                "/api/v1/reserves/",
                headers=admin_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "amount": 5,
                    "currency_code": "USD",
                    "reserve_scope": "earning_event",
                    "reserve_reason_type": "manual",
                    "source_earning_event_id": event_id,
                    "reason_code": "manual_review_buffer",
                    "reserve_payload": {"source": "phase4-test"},
                },
            )
            assert reserve_response.status_code == 201
            reserve_id = reserve_response.json()["id"]

            event_after_reserve = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert event_after_reserve.status_code == 200
            assert event_after_reserve.json()["event_status"] == "blocked"

            release_reserve_response = await async_client.post(
                f"/api/v1/reserves/{reserve_id}/release",
                headers=admin_headers,
                json={"release_reason_code": "buffer_cleared"},
            )
            assert release_reserve_response.status_code == 200
            assert release_reserve_response.json()["reserve_status"] == "released"

            final_event_response = await async_client.get(
                f"/api/v1/earning-events/{event_id}",
                headers=support_headers,
            )
            assert final_event_response.status_code == 200
            assert final_event_response.json()["event_status"] == "available"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_settlement_uses_order_currency_for_commission_snapshot(
    async_client: AsyncClient,
) -> None:
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
                pricebook = db.get(PricebookModel, uuid.UUID(seeded["pricebook_id"]))
                assert pricebook is not None
                pricebook.currency_code = "XTR"

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="settlement-xtr-owner@example.test",
                    password_hash=await auth_service.hash_password("SettlementXtrOwner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="settlement-xtr-workspace",
                    display_name="Settlement XTR Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="SETTLEXTR",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                db.add_all([partner_owner, partner_account, partner_code])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="xtr-settlement-order",
                currency="XTR",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()
            assert order_payload["currency_code"] == "XTR"

            with sessionmaker() as db:
                attribution_result = (
                    db.query(OrderAttributionResultModel)
                    .filter(OrderAttributionResultModel.order_id == uuid.UUID(order_payload["id"]))
                    .one()
                )
                commission_snapshot = attribution_result.policy_snapshot["commercial_policy_snapshot"][
                    "commission_contract_snapshot"
                ]
                assert commission_snapshot["currency_code"] == "XTR"
                assert commission_snapshot["currency_policy"]["minor_unit"] == 0

                adapter = SyncSessionAdapter(db)
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal(str(order_payload["displayed_price"])),
                    currency="XTR",
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
                    currency_code="XTR",
                    status="succeeded",
                    displayed_amount=Decimal(str(order_payload["displayed_price"])),
                    wallet_amount=Decimal("0"),
                    gateway_amount=Decimal(str(order_payload["gateway_amount"])),
                    idempotency_key="xtr-settlement-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id, process_cash_rewards=True)
                db.commit()

                assert results["partner_earning"] is not None
                assert results.get("partner_policy_block_reasons") in (None, [])
                persisted_event = db.get(EarningEventModel, uuid.UUID(results["settlement_earning_event_id"]))
                assert persisted_event is not None
                assert persisted_event.currency_code == "XTR"
                assert persisted_event.commission_base_amount == Decimal("75")
                assert persisted_event.markup_amount == Decimal("11")
                assert persisted_event.commission_amount == Decimal("15")
                assert persisted_event.total_amount == Decimal("26")
                event_snapshot = persisted_event.calculation_snapshot["commission_contract_snapshot"]
                assert event_snapshot["currency_code"] == "XTR"
                assert event_snapshot["currency_policy"]["minor_unit"] == 0
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_settlement_missing_commission_snapshot_fails_closed(
    async_client: AsyncClient,
) -> None:
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
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="snapshot-missing-owner@example.test",
                    password_hash=await auth_service.hash_password("SnapshotMissing123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="snapshot-missing-workspace",
                    display_name="Snapshot Missing Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="MISSNAP1",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=15,
                    is_active=True,
                )
                db.add_all([partner_owner, partner_account, partner_code])
                db.commit()

            customer_token = _make_customer_access_token(
                auth_service,
                user_id=seeded["customer_user_id"],
                customer_realm=customer_realm,
            )
            customer_headers = {
                "Authorization": f"Bearer {customer_token}",
                "X-Auth-Realm": "customer",
            }

            _, checkout_payload = await _create_quote_checkout(
                async_client=async_client,
                headers=customer_headers,
                storefront_key=seeded["storefront_key"],
                pricebook_key=seeded["pricebook_key"],
                offer_key=seeded["offer_key"],
                plan_id=seeded["plan_id"],
                partner_code=partner_code.code,
                idempotency_key="missing-snapshot-checkout",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            with sessionmaker() as db:
                attribution_result = (
                    db.query(OrderAttributionResultModel)
                    .filter(OrderAttributionResultModel.order_id == uuid.UUID(order_payload["id"]))
                    .one()
                )
                corrupted_snapshot = dict(attribution_result.policy_snapshot or {})
                corrupted_snapshot["commercial_policy_snapshot"] = {}
                attribution_result.policy_snapshot = corrupted_snapshot
                db.commit()

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
                    idempotency_key="missing-snapshot-attempt",
                    provider_snapshot={},
                    request_snapshot={},
                )
                db.add_all([payment, attempt])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id, process_cash_rewards=True)
                db.commit()

                assert results["partner_earning"] is None
                assert results["settlement_earning_event_id"] is None
                assert results["partner_earning_manual_review_event_id"] is not None
                assert results["partner_policy_block_reasons"] == ["PARTNER_EARNING_SNAPSHOT_INCOMPLETE"]
                assert "commission_contract_snapshot" in results["partner_earning_snapshot_missing_terms"]
                manual_review_event = db.get(
                    OutboxEventModel,
                    uuid.UUID(results["partner_earning_manual_review_event_id"]),
                )
                assert manual_review_event is not None
                assert manual_review_event.event_name == "settlement.earning.snapshot_incomplete"
                assert manual_review_event.event_key == (
                    f"settlement.earning.snapshot_incomplete:{payment.id}:{order_payload['id']}"
                )
                assert manual_review_event.event_payload["reason_code"] == "PARTNER_EARNING_SNAPSHOT_INCOMPLETE"
                assert manual_review_event.event_payload["manual_review_required"] is True
                assert manual_review_event.event_payload["retryable"] is True
                assert manual_review_event.event_payload["cash_payout_created"] is False
                assert "commission_contract_snapshot" in manual_review_event.event_payload["missing_terms"]
                assert (
                    db.query(EarningEventModel)
                    .filter(EarningEventModel.order_id == uuid.UUID(order_payload["id"]))
                    .count()
                    == 0
                )
                assert (
                    db.query(EarningHoldModel)
                    .join(EarningEventModel, EarningHoldModel.earning_event_id == EarningEventModel.id)
                    .filter(EarningEventModel.order_id == uuid.UUID(order_payload["id"]))
                    .count()
                    == 0
                )
                assert db.query(PartnerEarningModel).filter(PartnerEarningModel.payment_id == payment.id).count() == 0

                replay_results = await PostPaymentProcessingUseCase(adapter).execute(
                    payment.id,
                    process_cash_rewards=True,
                )
                db.commit()
                assert replay_results["partner_earning_manual_review_event_id"] == str(manual_review_event.id)
                assert (
                    db.query(OutboxEventModel)
                    .filter(OutboxEventModel.event_key == manual_review_event.event_key)
                    .count()
                    == 1
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_legacy_partner_payment_without_order_snapshot_fails_closed(
    async_client: AsyncClient,
) -> None:
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
                adapter = SyncSessionAdapter(db)
                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="legacy-block-owner@example.test",
                    password_hash=await auth_service.hash_password("LegacyBlock123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="legacy-block-workspace",
                    display_name="Legacy Block Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="LEGBLOCK1",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=Decimal("15"),
                    is_active=True,
                )
                payment = PaymentModel(
                    id=uuid.uuid4(),
                    user_uuid=uuid.UUID(seeded["customer_user_id"]),
                    amount=Decimal("100.00"),
                    currency="USD",
                    status="completed",
                    provider="cryptobot",
                    subscription_days=365,
                    plan_id=None,
                    partner_code_id=partner_code.id,
                    metadata_={"commission_base_amount": "100.00"},
                )
                db.add_all([partner_owner, partner_account, partner_code, payment])
                db.commit()

                results = await PostPaymentProcessingUseCase(adapter).execute(payment.id, process_cash_rewards=True)
                db.commit()

                assert results["partner_earning"] is None
                assert results["settlement_earning_event_id"] is None
                assert results["partner_policy_block_reasons"] == ["PARTNER_EARNING_SNAPSHOT_INCOMPLETE"]
                assert results["partner_earning_snapshot_missing_terms"] == ["order_attribution_result"]
                assert db.query(PartnerEarningModel).filter(PartnerEarningModel.payment_id == payment.id).count() == 0
                assert db.query(EarningEventModel).filter(EarningEventModel.payment_id == payment.id).count() == 0
                assert db.query(EarningHoldModel).count() == 0
                assert (
                    db.query(WalletTransactionModel)
                    .filter(
                        WalletTransactionModel.user_id == partner_owner.id,
                        WalletTransactionModel.reference_id == payment.id,
                    )
                    .count()
                    == 0
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
