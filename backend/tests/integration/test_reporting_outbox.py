from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel
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
async def test_reporting_outbox_tracks_domain_events_and_publication_lifecycle(
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
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")

                partner_owner = MobileUserModel(
                    id=uuid.uuid4(),
                    auth_realm_id=customer_realm.id,
                    email="phase7-owner@example.test",
                    password_hash=await auth_service.hash_password("Phase7Owner123!"),
                    is_active=True,
                    is_partner=True,
                    status="active",
                )
                partner_account = PartnerAccountModel(
                    id=uuid.uuid4(),
                    account_key="phase7-workspace",
                    display_name="Phase 7 Workspace",
                    status="active",
                    legacy_owner_user_id=partner_owner.id,
                )
                partner_code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    code="PHASE7CODE",
                    partner_account_id=partner_account.id,
                    partner_user_id=partner_owner.id,
                    markup_pct=16,
                    is_active=True,
                )
                admin_user = AdminUserModel(
                    login="phase7_admin",
                    email="phase7-admin@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase7Admin123!"),
                    role="admin",
                    is_active=True,
                    is_email_verified=True,
                )
                support_user = AdminUserModel(
                    login="phase7_support",
                    email="phase7-support@example.com",
                    auth_realm_id=admin_realm.id,
                    password_hash=await auth_service.hash_password("Phase7Support123!"),
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
                idempotency_key="phase7-outbox-checkout",
            )
            order_response = await async_client.post(
                "/api/v1/orders/commit",
                headers=customer_headers,
                json={"checkout_session_id": checkout_payload["id"]},
            )
            assert order_response.status_code == 201
            order_payload = order_response.json()

            order_events_response = await async_client.get(
                f"/api/v1/reporting/outbox-events?aggregate_type=order&aggregate_id={order_payload['id']}",
                headers=support_headers,
            )
            assert order_events_response.status_code == 200
            order_events = order_events_response.json()
            assert {item["event_name"] for item in order_events} == {"order.created"}

            order_created_event = order_events[0]
            assert {item["consumer_key"] for item in order_created_event["publications"]} == {
                "analytics_mart",
                "operational_replay",
            }

            attribution_events_response = await async_client.get(
                "/api/v1/reporting/outbox-events?event_name=attribution.result.finalized",
                headers=support_headers,
            )
            assert attribution_events_response.status_code == 200
            assert any(
                item["event_payload"].get("order_id") == order_payload["id"]
                for item in attribution_events_response.json()
            )

            risk_subject_response = await async_client.post(
                "/api/v1/security/risk-subjects",
                headers=admin_headers,
                json={
                    "principal_class": "customer",
                    "principal_subject": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "metadata": {"source": "phase7"},
                },
            )
            assert risk_subject_response.status_code == 201
            risk_subject_payload = risk_subject_response.json()

            risk_review_response = await async_client.post(
                "/api/v1/security/risk-reviews",
                headers=admin_headers,
                json={
                    "risk_subject_id": risk_subject_payload["id"],
                    "review_type": "manual_hold",
                    "reason": "phase7 verification",
                    "decision": "hold",
                    "evidence": {"ticket_id": "PHASE7-1"},
                },
            )
            assert risk_review_response.status_code == 201
            risk_review_payload = risk_review_response.json()

            risk_events_response = await async_client.get(
                f"/api/v1/reporting/outbox-events?aggregate_type=risk_review&aggregate_id={risk_review_payload['id']}",
                headers=support_headers,
            )
            assert risk_events_response.status_code == 200
            assert [item["event_name"] for item in risk_events_response.json()] == ["risk.review.opened"]

            period_response = await async_client.post(
                "/api/v1/settlement-periods/",
                headers=admin_headers,
                json={
                    "partner_account_id": str(partner_account.id),
                    "period_key": "2026-04-phase7",
                    "currency_code": "USD",
                    "window_start": "2026-04-01T00:00:00Z",
                    "window_end": "2026-05-01T00:00:00Z",
                },
            )
            assert period_response.status_code == 201

            generate_statement_response = await async_client.post(
                "/api/v1/partner-statements/generate",
                headers=admin_headers,
                json={"settlement_period_id": period_response.json()["id"]},
            )
            assert generate_statement_response.status_code == 201
            statement_payload = generate_statement_response.json()

            close_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_payload['id']}/close",
                headers=admin_headers,
            )
            assert close_statement_response.status_code == 200

            reopen_statement_response = await async_client.post(
                f"/api/v1/partner-statements/{statement_payload['id']}/reopen",
                headers=admin_headers,
            )
            assert reopen_statement_response.status_code == 200
            reopened_statement_payload = reopen_statement_response.json()

            settlement_events_response = await async_client.get(
                "/api/v1/reporting/outbox-events?event_family=settlement",
                headers=support_headers,
            )
            assert settlement_events_response.status_code == 200
            settlement_statement_events = [
                item
                for item in settlement_events_response.json()
                if item["event_name"].startswith("settlement.statement.")
            ]
            assert {
                item["event_name"] for item in settlement_statement_events
            } >= {
                "settlement.statement.generated",
                "settlement.statement.closed",
                "settlement.statement.reopened",
            }
            assert any(
                item["event_payload"].get("partner_statement_id") == reopened_statement_payload["id"]
                and item["event_name"] == "settlement.statement.reopened"
                for item in settlement_statement_events
            )

            with sessionmaker() as db:
                order = db.get(OrderModel, uuid.UUID(order_payload["id"]))
                assert order is not None
                order.settlement_status = "paid"
                db.commit()

            service_identity_response = await async_client.post(
                "/api/v1/service-identities/",
                headers=admin_headers,
                json={
                    "customer_account_id": seeded["customer_user_id"],
                    "auth_realm_id": seeded["customer_realm_id"],
                    "provider_name": "remnawave",
                    "source_order_id": order_payload["id"],
                },
            )
            assert service_identity_response.status_code == 201
            service_identity_payload = service_identity_response.json()

            create_grant_response = await async_client.post(
                "/api/v1/entitlements/",
                headers=admin_headers,
                json={
                    "service_identity_id": service_identity_payload["id"],
                    "source_order_id": order_payload["id"],
                },
            )
            assert create_grant_response.status_code == 201
            grant_payload = create_grant_response.json()

            activate_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/activate",
                headers=admin_headers,
            )
            assert activate_response.status_code == 200

            revoke_response = await async_client.post(
                f"/api/v1/entitlements/{grant_payload['id']}/revoke",
                headers=admin_headers,
                json={"reason_code": "phase7_test_revoke"},
            )
            assert revoke_response.status_code == 200

            entitlement_events_response = await async_client.get(
                "/api/v1/reporting/outbox-events",
                headers=support_headers,
                params={
                    "aggregate_type": "entitlement_grant",
                    "aggregate_id": grant_payload["id"],
                },
            )
            assert entitlement_events_response.status_code == 200
            assert {item["event_name"] for item in entitlement_events_response.json()} == {
                "entitlement.grant.activated",
                "entitlement.grant.revoked",
            }

            event_detail_response = await async_client.get(
                f"/api/v1/reporting/outbox-events/{order_created_event['id']}",
                headers=support_headers,
            )
            assert event_detail_response.status_code == 200
            assert event_detail_response.json()["event_name"] == "order.created"

            claim_analytics_response = await async_client.post(
                "/api/v1/reporting/outbox-publications/claim",
                headers=admin_headers,
                json={
                    "consumer_key": "analytics_mart",
                    "lease_owner": "phase7-analytics-worker",
                    "batch_size": 5,
                    "lease_seconds": 120,
                },
            )
            assert claim_analytics_response.status_code == 200
            claimed_analytics = claim_analytics_response.json()["claimed_publications"]
            assert claimed_analytics
            analytics_publication = claimed_analytics[0]

            submitted_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{analytics_publication['id']}/submitted",
                headers=admin_headers,
                json={"lease_owner": "phase7-analytics-worker"},
            )
            assert submitted_response.status_code == 200
            assert submitted_response.json()["publication_status"] == "submitted"

            published_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{analytics_publication['id']}/published",
                headers=admin_headers,
                json={
                    "lease_owner": "phase7-analytics-worker",
                    "publication_payload": {"batch_key": "phase7-a"},
                },
            )
            assert published_response.status_code == 200
            assert published_response.json()["publication_status"] == "published"
            assert published_response.json()["publication_payload"]["batch_key"] == "phase7-a"

            claim_replay_response = await async_client.post(
                "/api/v1/reporting/outbox-publications/claim",
                headers=admin_headers,
                json={
                    "consumer_key": "operational_replay",
                    "lease_owner": "phase7-replay-worker",
                    "batch_size": 5,
                    "lease_seconds": 120,
                },
            )
            assert claim_replay_response.status_code == 200
            claimed_replay = claim_replay_response.json()["claimed_publications"]
            assert claimed_replay
            replay_publication = claimed_replay[0]

            failed_response = await async_client.post(
                f"/api/v1/reporting/outbox-publications/{replay_publication['id']}/failed",
                headers=admin_headers,
                json={
                    "lease_owner": "phase7-replay-worker",
                    "retry_after_seconds": 300,
                    "error_message": "phase7 replay unavailable",
                },
            )
            assert failed_response.status_code == 200
            assert failed_response.json()["publication_status"] == "failed"
            assert failed_response.json()["last_error"] == "phase7 replay unavailable"

            published_publications_response = await async_client.get(
                "/api/v1/reporting/outbox-publications?consumer_key=analytics_mart&publication_status=published",
                headers=support_headers,
            )
            assert published_publications_response.status_code == 200
            assert any(
                item["id"] == analytics_publication["id"] for item in published_publications_response.json()
            )

            failed_publications_response = await async_client.get(
                "/api/v1/reporting/outbox-publications?consumer_key=operational_replay&publication_status=failed",
                headers=support_headers,
            )
            assert failed_publications_response.status_code == 200
            assert any(item["id"] == replay_publication["id"] for item in failed_publications_response.json())

            updated_event_response = await async_client.get(
                f"/api/v1/reporting/outbox-events/{analytics_publication['outbox_event_id']}",
                headers=support_headers,
            )
            assert updated_event_response.status_code == 200
            assert updated_event_response.json()["event_status"] == "partially_published"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
