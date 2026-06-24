from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from src.application.services.auth_service import AuthService
from src.application.use_cases.settlement.commission_terms import build_commission_contract_model
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.creative_approval_model import CreativeApprovalModel
from src.infrastructure.database.models.earning_event_model import EarningEventModel
from src.infrastructure.database.models.partner_model import (
    PartnerCodeLinkModel,
    PartnerCodeModel,
    PartnerCommissionContractModel,
)
from src.infrastructure.database.models.partner_payout_account_model import PartnerPayoutAccountModel
from src.infrastructure.database.models.partner_statement_model import PartnerStatementModel
from src.infrastructure.database.models.payout_instruction_model import PayoutInstructionModel
from src.infrastructure.database.models.pilot_cohort_model import (
    PilotCohortModel,
    PilotGoNoGoDecisionModel,
    PilotOwnerAcknowledgementModel,
    PilotRollbackDrillModel,
    PilotRolloutWindowModel,
)
from src.infrastructure.database.models.reserve_model import ReserveModel
from src.infrastructure.database.models.settlement_period_model import SettlementPeriodModel
from src.infrastructure.database.models.statement_adjustment_model import StatementAdjustmentModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.main import app
from tests.helpers.realm_auth import (
    ADMIN_AUTH_REALM_HEADERS,
    PARTNER_ACCESS_COOKIE_NAME,
    PARTNER_AUTH_REALM_HEADERS,
    FakeRedis,
    SyncSessionAdapter,
    access_token_from_client_cookies,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)

pytestmark = [pytest.mark.integration]


async def _create_admin_user(
    *,
    session,
    auth_service: AuthService,
    auth_realm_id,
    login: str,
    email: str,
    password: str,
    role: str,
) -> AdminUserModel:
    user = AdminUserModel(
        login=login,
        email=email,
        auth_realm_id=auth_realm_id,
        password_hash=await auth_service.hash_password(password),
        role=role,
        is_active=True,
        is_email_verified=True,
    )
    session.add(user)
    session.commit()
    return user


async def _login(
    async_client: AsyncClient,
    login_or_email: str,
    password: str,
    *,
    headers: dict[str, str] = ADMIN_AUTH_REALM_HEADERS,
    cookie_name: str = "access_token",
) -> str:
    response = await async_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"login_or_email": login_or_email, "password": password},
    )
    assert response.status_code == 200
    return access_token_from_client_cookies(async_client, cookie_name=cookie_name, response=response)


async def _create_workspace(
    async_client: AsyncClient,
    *,
    admin_headers: dict[str, str],
    owner_admin_user_id: str,
) -> str:
    response = await async_client.post(
        "/api/v1/admin/partner-workspaces",
        headers=admin_headers,
        json={
            "display_name": "Portal Workspace",
            "owner_admin_user_id": owner_admin_user_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _seed_green_reseller_lane(
    *,
    session,
    workspace_id: uuid.UUID,
    owner_admin_user_id: uuid.UUID,
    actor_admin_user_id: uuid.UUID,
) -> None:
    activated_at = datetime(2026, 4, 19, 9, 0, tzinfo=UTC)
    cohort_id = uuid.uuid4()
    session.add(
        PilotCohortModel(
            id=cohort_id,
            cohort_key=f"reseller-{workspace_id}",
            display_name="Reseller Voucher Lane",
            lane_key="reseller_distribution",
            surface_key="partner_storefront",
            cohort_status="active",
            partner_account_id=workspace_id,
            owner_team="partner_ops",
            owner_admin_user_id=owner_admin_user_id,
            rollback_trigger_code="shadow_divergence_exceeded",
            shadow_gate_payload={
                "attribution_gate_status": "green",
                "settlement_gate_status": "green",
            },
            monitoring_payload={"max_live_orders": 50},
            notes_payload=["Reseller lane is active for voucher distribution."],
            scheduled_start_at=activated_at - timedelta(days=1),
            scheduled_end_at=activated_at + timedelta(days=7),
            activated_at=activated_at,
            created_by_admin_user_id=actor_admin_user_id,
            activated_by_admin_user_id=actor_admin_user_id,
            created_at=activated_at - timedelta(days=2),
            updated_at=activated_at,
        )
    )
    session.add(
        PilotRolloutWindowModel(
            id=uuid.uuid4(),
            pilot_cohort_id=cohort_id,
            window_kind="host",
            target_ref="reseller.partner.example",
            window_status="active",
            starts_at=activated_at - timedelta(days=1),
            ends_at=activated_at + timedelta(days=7),
            notes_payload=["Reseller rollout window"],
            created_by_admin_user_id=actor_admin_user_id,
            created_at=activated_at - timedelta(days=2),
            updated_at=activated_at,
        )
    )
    for owner_team in ("platform", "support", "qa", "partner_ops", "finance_ops"):
        session.add(
            PilotOwnerAcknowledgementModel(
                id=uuid.uuid4(),
                pilot_cohort_id=cohort_id,
                owner_team=owner_team,
                acknowledgement_status="acknowledged",
                runbook_reference=f"runbook://{owner_team}/reseller-voucher",
                notes_payload=[f"{owner_team} acknowledged reseller voucher lane readiness."],
                acknowledged_by_admin_user_id=actor_admin_user_id,
                acknowledged_at=activated_at - timedelta(hours=6),
                created_at=activated_at - timedelta(hours=6),
                updated_at=activated_at - timedelta(hours=6),
            )
        )
    session.add(
        PilotRollbackDrillModel(
            id=uuid.uuid4(),
            pilot_cohort_id=cohort_id,
            cutover_unit_key="partner_storefront",
            rollback_scope_class="workspace",
            trigger_code="shadow_divergence_exceeded",
            drill_status="passed",
            runbook_reference="runbook://rollback/reseller-voucher",
            observed_metric_payload={"orders_checked": 8},
            notes_payload=["Rollback drill passed for reseller lane."],
            executed_by_admin_user_id=actor_admin_user_id,
            executed_at=activated_at - timedelta(hours=5),
            created_at=activated_at - timedelta(hours=5),
            updated_at=activated_at - timedelta(hours=5),
        )
    )
    session.add(
        PilotGoNoGoDecisionModel(
            id=uuid.uuid4(),
            pilot_cohort_id=cohort_id,
            decision_status="approved",
            decision_reason_code=None,
            release_ring="R4",
            rollback_scope_class="workspace",
            cutover_unit_keys_payload=["partner_storefront"],
            evidence_links_payload=["evidence://reseller/voucher"],
            acknowledged_owner_teams_payload=["platform", "support", "qa", "partner_ops", "finance_ops"],
            monitoring_snapshot_payload={"shadow_status": "green"},
            notes_payload=["Reseller lane is approved for rollout."],
            decided_by_admin_user_id=actor_admin_user_id,
            decided_at=activated_at - timedelta(hours=4),
            created_at=activated_at - timedelta(hours=4),
            updated_at=activated_at - timedelta(hours=4),
        )
    )


def _create_plan(*, session, name: str, duration_days: int, price_usd: str) -> SubscriptionPlanModel:
    plan = SubscriptionPlanModel(
        id=uuid.uuid4(),
        name=name,
        tier="max",
        plan_code="max",
        display_name="Max",
        catalog_visibility="public",
        duration_days=duration_days,
        traffic_limit_bytes=None,
        device_limit=10,
        price_usd=Decimal(price_usd),
        price_rub=None,
        sale_channels=["web"],
        traffic_policy={},
        connection_modes=["standard", "stealth"],
        server_pool=["premium"],
        support_sla="priority",
        dedicated_ip={},
        invite_bundle={},
        trial_eligible=False,
        features={},
        is_active=True,
        sort_order=0,
    )
    session.add(plan)
    return plan


@pytest.mark.asyncio
async def test_partner_workspace_codes_and_statements_are_visible_to_workspace_members(
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
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="portal_admin",
                    email="portal-admin@example.com",
                    password="PortalAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="portal_owner",
                    email="portal-owner@example.com",
                    password="PortalOwner123!",
                    role="viewer",
                )
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="portal_outsider",
                    email="portal-outsider@example.com",
                    password="PortalOutsider123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "portal-admin@example.com", "PortalAdmin123!")
            owner_token = await _login(
                async_client,
                "portal-owner@example.com",
                "PortalOwner123!",
                headers=PARTNER_AUTH_REALM_HEADERS,
                cookie_name=PARTNER_ACCESS_COOKIE_NAME,
            )
            outsider_token = await _login(
                async_client,
                "portal-outsider@example.com",
                "PortalOutsider123!",
                headers=PARTNER_AUTH_REALM_HEADERS,
                cookie_name=PARTNER_ACCESS_COOKIE_NAME,
            )

            admin_headers = {"Authorization": f"Bearer {admin_token}", **ADMIN_AUTH_REALM_HEADERS}
            owner_headers = {"Authorization": f"Bearer {owner_token}", **PARTNER_AUTH_REALM_HEADERS}
            outsider_headers = {"Authorization": f"Bearer {outsider_token}", **PARTNER_AUTH_REALM_HEADERS}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            with sessionmaker() as db:
                workspace_uuid = uuid.UUID(workspace_id)
                settlement_period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    period_key="2026-04",
                    period_status="closed",
                    currency_code="USD",
                    window_start=datetime(2026, 4, 1, tzinfo=UTC),
                    window_end=datetime(2026, 5, 1, tzinfo=UTC),
                )
                eur_settlement_period = SettlementPeriodModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    period_key="2026-05-eur",
                    period_status="closed",
                    currency_code="EUR",
                    window_start=datetime(2026, 5, 1, tzinfo=UTC),
                    window_end=datetime(2026, 6, 1, tzinfo=UTC),
                )
                statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    settlement_period_id=settlement_period.id,
                    statement_key="portal-workspace-2026-04-v1",
                    statement_version=1,
                    statement_status="closed",
                    currency_code="USD",
                    accrual_amount=Decimal("125.00"),
                    on_hold_amount=Decimal("15.00"),
                    reserve_amount=Decimal("10.00"),
                    adjustment_net_amount=Decimal("0.00"),
                    available_amount=Decimal("100.00"),
                    source_event_count=4,
                    held_event_count=1,
                    active_reserve_count=1,
                    adjustment_count=0,
                    statement_snapshot={"source": "portal-test"},
                )
                eur_statement = PartnerStatementModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    settlement_period_id=eur_settlement_period.id,
                    statement_key="portal-workspace-2026-05-eur-v1",
                    statement_version=1,
                    statement_status="closed",
                    currency_code="EUR",
                    accrual_amount=Decimal("50.00"),
                    on_hold_amount=Decimal("6.00"),
                    reserve_amount=Decimal("0.00"),
                    adjustment_net_amount=Decimal("-2.00"),
                    available_amount=Decimal("42.00"),
                    source_event_count=2,
                    held_event_count=1,
                    active_reserve_count=0,
                    adjustment_count=1,
                    statement_snapshot={"source": "portal-test-eur"},
                )
                usd_on_hold_event_id = uuid.uuid4()
                earning_events = [
                    EarningEventModel(
                        id=usd_on_hold_event_id,
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="on_hold",
                        commission_base_amount=Decimal("150.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("15.00"),
                        total_amount=Decimal("15.00"),
                        currency_code="USD",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                    EarningEventModel(
                        id=uuid.uuid4(),
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="available",
                        commission_base_amount=Decimal("200.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("20.00"),
                        total_amount=Decimal("20.00"),
                        currency_code="USD",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                    EarningEventModel(
                        id=uuid.uuid4(),
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="reversed",
                        commission_base_amount=Decimal("50.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("5.00"),
                        total_amount=Decimal("5.00"),
                        currency_code="USD",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                    EarningEventModel(
                        id=uuid.uuid4(),
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="blocked",
                        commission_base_amount=Decimal("75.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("7.50"),
                        total_amount=Decimal("7.50"),
                        currency_code="USD",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                    EarningEventModel(
                        id=uuid.uuid4(),
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="available",
                        commission_base_amount=Decimal("400.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("40.00"),
                        total_amount=Decimal("40.00"),
                        currency_code="EUR",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                    EarningEventModel(
                        id=uuid.uuid4(),
                        partner_account_id=workspace_uuid,
                        client_user_id=uuid.uuid4(),
                        order_id=uuid.uuid4(),
                        owner_type="affiliate",
                        event_status="reversed",
                        commission_base_amount=Decimal("30.00"),
                        markup_amount=Decimal("0.00"),
                        commission_pct=Decimal("10.0000"),
                        commission_amount=Decimal("3.00"),
                        total_amount=Decimal("3.00"),
                        currency_code="EUR",
                        calculation_snapshot={"source": "finance-summary-test"},
                        source_snapshot={"source": "finance-summary-test"},
                    ),
                ]
                payout_account = PartnerPayoutAccountModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    payout_rail="manual",
                    display_label="Finance summary route",
                    destination_reference="finance-summary@example.test",
                    masked_destination="finance-summary@example.test",
                    verification_status="verified",
                    approval_status="approved",
                    account_status="active",
                    is_default=True,
                    created_by_admin_user_id=owner_user.id,
                )
                reserve = ReserveModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    source_earning_event_id=usd_on_hold_event_id,
                    reserve_scope="earning_event",
                    reserve_reason_type="risk_buffer",
                    reserve_status="active",
                    amount=Decimal("8.00"),
                    currency_code="USD",
                    reason_code="finance_summary_test",
                    reserve_payload={"source": "finance-summary-test"},
                    created_by_admin_user_id=owner_user.id,
                )
                usd_adjustment = StatementAdjustmentModel(
                    id=uuid.uuid4(),
                    partner_statement_id=statement.id,
                    partner_account_id=workspace_uuid,
                    adjustment_type="refund_clawback",
                    adjustment_direction="debit",
                    amount=Decimal("4.00"),
                    currency_code="USD",
                    reason_code="finance_summary_refund",
                    adjustment_payload={"source": "finance-summary-test"},
                    created_by_admin_user_id=owner_user.id,
                )
                usd_instruction = PayoutInstructionModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    partner_statement_id=statement.id,
                    partner_payout_account_id=payout_account.id,
                    instruction_key=f"statement:{statement.id}",
                    instruction_status="pending_approval",
                    payout_amount=Decimal("30.00"),
                    currency_code="USD",
                    instruction_snapshot={"source": "finance-summary-test"},
                    created_by_admin_user_id=owner_user.id,
                )
                eur_instruction = PayoutInstructionModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    partner_statement_id=eur_statement.id,
                    partner_payout_account_id=payout_account.id,
                    instruction_key=f"statement:{eur_statement.id}",
                    instruction_status="completed",
                    payout_amount=Decimal("12.00"),
                    currency_code="EUR",
                    instruction_snapshot={"source": "finance-summary-test"},
                    created_by_admin_user_id=owner_user.id,
                    completed_at=datetime(2026, 5, 20, tzinfo=UTC),
                )
                code = PartnerCodeModel(
                    id=uuid.uuid4(),
                    partner_account_id=workspace_uuid,
                    partner_user_id=uuid.uuid4(),
                    code="PORTAL42",
                    markup_pct=Decimal("15.00"),
                    is_active=True,
                )
                code_id = code.id
                db.add_all(
                    [
                        settlement_period,
                        eur_settlement_period,
                        statement,
                        eur_statement,
                        *earning_events,
                        payout_account,
                        reserve,
                        usd_adjustment,
                        usd_instruction,
                        eur_instruction,
                        code,
                    ]
                )
                db.commit()

            workspace_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}",
                headers=owner_headers,
            )
            assert workspace_response.status_code == 200
            assert workspace_response.json()["current_role_key"] == "owner"

            codes_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=owner_headers,
            )
            assert codes_response.status_code == 200
            codes_payload = codes_response.json()
            assert len(codes_payload) == 1
            assert codes_payload[0]["code"] == "PORTAL42"
            assert codes_payload[0]["partner_account_id"] == workspace_id

            link_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}/links",
                headers=owner_headers,
                json={
                    "destination_path": "/pricing",
                    "campaign_params": {"utm_source": "portal"},
                    "sub_ids": {"creator": "portal42"},
                },
            )
            assert link_response.status_code == 200
            link_payload = link_response.json()
            assert link_payload["code_id"] == str(code_id)
            assert link_payload["destination_key"] == "pricing"
            assert link_payload["destination_path"] == "/pricing"
            assert link_payload["campaign_params"] == {"utm_source": "portal"}
            assert link_payload["sub_ids"] == {"creator": "portal42"}
            assert link_payload["share_url"].endswith(f"/p/{link_payload['public_slug']}")
            assert "to=" not in link_payload["share_url"]

            with sessionmaker() as db:
                stored_link = db.get(PartnerCodeLinkModel, uuid.UUID(link_payload["link_id"]))
                assert stored_link is not None
                assert stored_link.partner_code_id == code_id
                assert stored_link.partner_account_id == uuid.UUID(workspace_id)
                assert stored_link.destination_path == "/pricing"

            qr_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}/qr",
                headers=owner_headers,
                json={"link_id": link_payload["link_id"], "size": 128},
            )
            assert qr_response.status_code == 200
            qr_payload = qr_response.json()
            assert qr_payload["link_id"] == link_payload["link_id"]
            assert qr_payload["public_slug"] == link_payload["public_slug"]
            assert qr_payload["share_url"] == link_payload["share_url"]
            assert "<svg" in qr_payload["qr_svg"]

            statements_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/statements",
                headers=owner_headers,
            )
            assert statements_response.status_code == 200
            statements_payload = statements_response.json()
            assert len(statements_payload) == 2
            statements_by_key = {item["statement_key"]: item for item in statements_payload}
            assert statements_by_key["portal-workspace-2026-04-v1"]["partner_account_id"] == workspace_id
            assert statements_by_key["portal-workspace-2026-04-v1"]["available_amount"] == 100.0
            assert statements_by_key["portal-workspace-2026-05-eur-v1"]["currency_code"] == "EUR"

            finance_summary_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/finance-summary",
                headers=owner_headers,
            )
            assert finance_summary_response.status_code == 200
            finance_summary = finance_summary_response.json()
            assert "partner_statements" in finance_summary["source_of_truth"]
            assert "payout_instructions" in finance_summary["source_of_truth"]
            currency_summary = {item["currency_code"]: item for item in finance_summary["currencies"]}
            assert set(currency_summary) == {"EUR", "USD"}

            usd_summary = currency_summary["USD"]
            assert usd_summary["event_count"] == 4
            assert usd_summary["pending_amount"] == "7.50"
            assert usd_summary["on_hold_amount"] == "15.00"
            assert usd_summary["available_amount"] == "20.00"
            assert usd_summary["reserved_amount"] == "8.00"
            assert usd_summary["statement_reserved_amount"] == "10.00"
            assert usd_summary["reversed_amount"] == "5.00"
            assert usd_summary["adjustment_amount"] == "-4.00"
            assert usd_summary["statement_count"] == 1
            assert usd_summary["statement_event_count"] == 4
            assert usd_summary["statement_included_amount"] == "125.00"
            assert usd_summary["statement_available_amount"] == "100.00"
            assert usd_summary["payout_instruction_count"] == 1
            assert usd_summary["payout_instruction_amount"] == "30.00"
            assert usd_summary["payout_pending_amount"] == "30.00"
            assert usd_summary["payout_completed_amount"] == "0.00"
            assert usd_summary["next_payout_forecast_amount"] == "100.00"

            eur_summary = currency_summary["EUR"]
            assert eur_summary["event_count"] == 2
            assert eur_summary["pending_amount"] == "0.00"
            assert eur_summary["available_amount"] == "40.00"
            assert eur_summary["paid_amount"] == "12.00"
            assert eur_summary["reversed_amount"] == "3.00"
            assert eur_summary["adjustment_amount"] == "-2.00"
            assert eur_summary["statement_count"] == 1
            assert eur_summary["statement_included_amount"] == "50.00"
            assert eur_summary["statement_available_amount"] == "42.00"
            assert eur_summary["payout_instruction_amount"] == "12.00"
            assert eur_summary["payout_completed_amount"] == "12.00"
            assert eur_summary["next_payout_forecast_amount"] == "30.00"

            outsider_codes_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/codes",
                headers=outsider_headers,
            )
            assert outsider_codes_response.status_code == 403

            outsider_link_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}/links",
                headers=outsider_headers,
                json={"destination_path": "/pricing"},
            )
            assert outsider_link_response.status_code == 403

            outsider_statements_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/statements",
                headers=outsider_headers,
            )
            assert outsider_statements_response.status_code == 403

            outsider_finance_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/finance-summary",
                headers=outsider_headers,
            )
            assert outsider_finance_response.status_code == 403
            assert "currencies" not in outsider_finance_response.json()
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_workspace_code_markup_update_rotates_commission_contract(
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
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                partner_realm = await realm_repo.get_or_create_default_realm("partner")
                await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="contract_admin",
                    email="contract-admin@example.com",
                    password="ContractAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="contract_owner",
                    email="contract-owner@example.com",
                    password="ContractOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "contract-admin@example.com", "ContractAdmin123!")
            owner_token = await _login(
                async_client,
                "contract-owner@example.com",
                "ContractOwner123!",
                headers=PARTNER_AUTH_REALM_HEADERS,
                cookie_name=PARTNER_ACCESS_COOKIE_NAME,
            )
            admin_headers = {"Authorization": f"Bearer {admin_token}", **ADMIN_AUTH_REALM_HEADERS}
            owner_headers = {"Authorization": f"Bearer {owner_token}", **PARTNER_AUTH_REALM_HEADERS}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            with sessionmaker() as db:
                code_model = PartnerCodeModel(
                    id=uuid.uuid4(),
                    partner_account_id=uuid.UUID(workspace_id),
                    partner_user_id=owner_user.id,
                    code="CONTRACT42",
                    code_normalized="CONTRACT42",
                    markup_pct=Decimal("10.00"),
                    is_active=True,
                    version=1,
                )
                db.add(code_model)
                db.flush()
                first_contract = build_commission_contract_model(
                    code_model=code_model,
                    commission_pct=Decimal("20.00"),
                    payout_hold_days=30,
                    source="test_seed",
                    contract_id=uuid.uuid4(),
                )
                db.add(first_contract)
                db.flush()
                code_model.commission_contract_id = first_contract.id
                first_contract_id = first_contract.id
                code_id = code_model.id
                db.commit()
                assert first_contract.terms_snapshot["markup_pct"] == "10.00"
                assert first_contract.terms_snapshot["contract_version"] == 1

            destination_response = await async_client.patch(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}",
                headers={**owner_headers, "If-Match": '"1"'},
                json={"destination_path": "/pricing"},
            )
            assert destination_response.status_code == 200
            destination_payload = destination_response.json()
            assert destination_payload["commission_contract_id"] == str(first_contract_id)
            assert destination_payload["version"] == 2

            markup_response = await async_client.patch(
                f"/api/v1/partner-workspaces/{workspace_id}/codes/{code_id}",
                headers={**owner_headers, "If-Match": '"2"'},
                json={"markup_pct": 25},
            )
            assert markup_response.status_code == 200, markup_response.text
            markup_payload = markup_response.json()
            second_contract_id = uuid.UUID(markup_payload["commission_contract_id"])
            assert second_contract_id != first_contract_id
            assert markup_payload["version"] == 3

            with sessionmaker() as db:
                code_model = db.get(PartnerCodeModel, code_id)
                assert code_model is not None
                assert code_model.commission_contract_id == second_contract_id
                old_contract = db.get(PartnerCommissionContractModel, first_contract_id)
                new_contract = db.get(PartnerCommissionContractModel, second_contract_id)
                assert old_contract is not None
                assert new_contract is not None
                assert old_contract.terms_snapshot["markup_pct"] == "10.00"
                assert old_contract.terms_snapshot["contract_version"] == 1
                assert new_contract.terms_snapshot["markup_pct"] == "25.0"
                assert new_contract.terms_snapshot["contract_version"] == 3
                assert (
                    db.query(PartnerCommissionContractModel)
                    .filter(PartnerCommissionContractModel.partner_code_id == code_model.id)
                    .count()
                    == 2
                )
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_partner_workspace_campaign_assets_and_reseller_voucher_batches_are_runtime_visible(
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
            with sessionmaker() as db:
                realm_repo = AuthRealmRepository(SyncSessionAdapter(db))
                admin_realm = await realm_repo.get_or_create_default_realm("admin")
                partner_realm = await realm_repo.get_or_create_default_realm("partner")

                admin_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=admin_realm.id,
                    login="voucher_admin",
                    email="voucher-admin@example.com",
                    password="VoucherAdmin123!",
                    role="admin",
                )
                owner_user = await _create_admin_user(
                    session=db,
                    auth_service=auth_service,
                    auth_realm_id=partner_realm.id,
                    login="voucher_owner",
                    email="voucher-owner@example.com",
                    password="VoucherOwner123!",
                    role="viewer",
                )

            admin_token = await _login(async_client, "voucher-admin@example.com", "VoucherAdmin123!")
            owner_token = await _login(
                async_client,
                "voucher-owner@example.com",
                "VoucherOwner123!",
                headers=PARTNER_AUTH_REALM_HEADERS,
                cookie_name=PARTNER_ACCESS_COOKIE_NAME,
            )

            admin_headers = {"Authorization": f"Bearer {admin_token}", **ADMIN_AUTH_REALM_HEADERS}
            owner_headers = {"Authorization": f"Bearer {owner_token}", **PARTNER_AUTH_REALM_HEADERS}

            workspace_id = await _create_workspace(
                async_client,
                admin_headers=admin_headers,
                owner_admin_user_id=str(owner_user.id),
            )

            with sessionmaker() as db:
                _seed_green_reseller_lane(
                    session=db,
                    workspace_id=uuid.UUID(workspace_id),
                    owner_admin_user_id=owner_user.id,
                    actor_admin_user_id=admin_user.id,
                )
                plan = _create_plan(
                    session=db,
                    name="Voucher Max 365",
                    duration_days=365,
                    price_usd="99.00",
                )
                db.add(
                    CreativeApprovalModel(
                        id=uuid.uuid4(),
                        partner_account_id=uuid.UUID(workspace_id),
                        approval_kind="creative_approval",
                        approval_status="complete",
                        scope_label="Telegram seasonal pack",
                        creative_ref="tg-pack-2026",
                        approval_payload={
                            "channel": "telegram",
                            "approval_owner": "Partner Ops",
                            "promo_reference": "SPRING-TELEGRAM-2026",
                            "disclosure_text": "#ad · CyberVPN seasonal launch copy only",
                            "allowed_claims": ["Seasonal onboarding bonus"],
                            "banned_claims": ["Guaranteed earnings"],
                            "allowed_geographies": ["DE", "PL"],
                            "destination_urls": ["https://offers.cybervpn.example/spring"],
                            "valid_until": "2026-05-01T00:00:00Z",
                        },
                        notes_payload=["Creative ref: tg-pack-2026"],
                        submitted_by_admin_user_id=admin_user.id,
                        reviewed_by_admin_user_id=admin_user.id,
                        reviewed_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
                        created_at=datetime(2026, 4, 19, 9, 0, tzinfo=UTC),
                        updated_at=datetime(2026, 4, 19, 10, 0, tzinfo=UTC),
                    )
                )
                db.commit()
                plan_id = str(plan.id)

            assets_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/campaign-assets",
                headers=owner_headers,
            )
            assert assets_response.status_code == 200
            asset = assets_response.json()[0]
            assert asset["promo_reference"] == "SPRING-TELEGRAM-2026"
            assert asset["allowed_geographies"] == ["DE", "PL"]
            assert asset["destination_urls"] == ["https://offers.cybervpn.example/spring"]

            request_response = await async_client.post(
                f"/api/v1/partner-workspaces/{workspace_id}/reseller-voucher-batches/request",
                headers=owner_headers,
                json={
                    "plan_id": plan_id,
                    "count": 3,
                    "recipient_hint": "Spring reseller pack",
                    "gift_message": "Priority storefront batch",
                },
            )
            assert request_response.status_code == 201
            request_payload = request_response.json()
            assert request_payload["batch"]["plan_family"] == "max"
            assert request_payload["batch"]["issued_count"] == 3
            assert len(request_payload["issued_codes"]) == 3

            batches_response = await async_client.get(
                f"/api/v1/partner-workspaces/{workspace_id}/reseller-voucher-batches",
                headers=owner_headers,
            )
            assert batches_response.status_code == 200
            batches_payload = batches_response.json()
            assert len(batches_payload) == 1
            assert batches_payload[0]["issued_count"] == 3
            assert batches_payload[0]["available_count"] == 3
            assert batches_payload[0]["status"] == "active"
    finally:
        app.dependency_overrides.pop(get_redis, None)
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
