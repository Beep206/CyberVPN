from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from src.application.services.auth_service import AuthService
from src.application.use_cases.growth_codes.reporting import (
    ExportGrowthReportingOverviewUseCase,
    GetGrowthReportingOverviewUseCase,
    RefreshGrowthReportingRollupsUseCase,
)
from src.config import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeModel,
    GrowthCodeRedemptionModel,
    GrowthCodeReservationModel,
    GrowthCodeResolutionEventModel,
)
from src.infrastructure.database.models.growth_reporting_daily_rollup_model import (
    GrowthReportingDailyRollupModel,
)
from src.infrastructure.database.models.growth_reporting_refresh_run_model import (
    GrowthReportingRefreshRunModel,
)
from src.infrastructure.database.models.growth_reward_allocation_model import GrowthRewardAllocationModel
from src.main import app
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
    override_realm_test_db,
)
from tests.integration.test_quote_checkout_sessions import _seed_quote_context

pytestmark = [pytest.mark.integration]


async def _create_admin_user(sessionmaker, auth_service: AuthService) -> tuple[AdminUserModel, str]:
    password = "GrowthReportsAdmin123!"
    with sessionmaker() as db:
        user = AdminUserModel(
            id=uuid.uuid4(),
            login="growthreportsadmin",
            email="growth-reports-admin@example.test",
            password_hash=await auth_service.hash_password(password),
            role="admin",
            is_active=True,
            is_email_verified=True,
            language="en",
            timezone="UTC",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, password


def _seed_growth_reporting_fixtures(sessionmaker, seeded: dict[str, str]) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)

    with sessionmaker() as db:
        invite_code = GrowthCodeModel(
            id=uuid.uuid4(),
            code_hash="hash:invite-reporting",
            code_prefix="INVREP",
            code_type="invite",
            status="active",
            issuer_type="admin",
            owner_user_id=uuid.UUID(seeded["customer_user_id"]),
            storefront_id=uuid.UUID(seeded["storefront_id"]),
            auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
            created_at=two_days_ago,
            updated_at=two_days_ago,
        )
        promo_code = GrowthCodeModel(
            id=uuid.uuid4(),
            code_hash="hash:promo-reporting",
            code_prefix="PROREP",
            code_type="promo",
            status="active",
            issuer_type="marketing_campaign",
            storefront_id=uuid.UUID(seeded["storefront_id"]),
            auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
            created_at=yesterday,
            updated_at=now,
        )
        gift_code = GrowthCodeModel(
            id=uuid.uuid4(),
            code_hash="hash:gift-reporting",
            code_prefix="GIFREP",
            code_type="gift",
            status="redeemed",
            issuer_type="admin",
            owner_user_id=uuid.UUID(seeded["customer_user_id"]),
            storefront_id=uuid.UUID(seeded["storefront_id"]),
            auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
            created_at=now,
            updated_at=now,
            uses_count=1,
        )
        db.add_all([invite_code, promo_code, gift_code])
        db.flush()

        db.add_all(
            [
                GrowthCodeResolutionEventModel(
                    id=uuid.uuid4(),
                    growth_code_id=promo_code.id,
                    raw_code_hash="raw:promo-reporting",
                    code_type="promo",
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    surface="web",
                    action_context="checkout",
                    result="accepted",
                    created_at=yesterday + timedelta(hours=1),
                ),
                GrowthCodeResolutionEventModel(
                    id=uuid.uuid4(),
                    growth_code_id=promo_code.id,
                    raw_code_hash="raw:promo-reporting",
                    code_type="promo",
                    user_id=uuid.UUID(seeded["customer_user_id"]),
                    surface="web",
                    action_context="checkout",
                    result="conflicted",
                    reject_reason="code_conflicts_with_partner_binding",
                    created_at=now + timedelta(hours=1),
                ),
            ]
        )

        db.add(
            GrowthCodeReservationModel(
                id=uuid.uuid4(),
                growth_code_id=promo_code.id,
                user_id=uuid.UUID(seeded["customer_user_id"]),
                reserved_at=yesterday + timedelta(hours=2),
                expires_at=yesterday + timedelta(hours=3),
                status="consumed",
                updated_at=now + timedelta(hours=2),
            )
        )

        db.add(
            GrowthCodeRedemptionModel(
                id=uuid.uuid4(),
                growth_code_id=gift_code.id,
                code_type="gift",
                redeemer_user_id=uuid.UUID(seeded["customer_user_id"]),
                beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                status="redeemed",
                redeemed_at=now + timedelta(hours=3),
                created_at=now + timedelta(hours=3),
                updated_at=now + timedelta(hours=3),
            )
        )

        db.add_all(
            [
                GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="referral_credit",
                    allocation_status="available",
                    beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    quantity=Decimal("10.00"),
                    unit="credit",
                    currency_code="USD",
                    source_key="test:growth-reporting:available",
                    allocated_at=yesterday + timedelta(hours=4),
                    available_at=now + timedelta(hours=4),
                    created_at=yesterday + timedelta(hours=4),
                    updated_at=now + timedelta(hours=4),
                ),
                GrowthRewardAllocationModel(
                    id=uuid.uuid4(),
                    reward_type="referral_credit",
                    allocation_status="reversed",
                    beneficiary_user_id=uuid.UUID(seeded["customer_user_id"]),
                    auth_realm_id=uuid.UUID(seeded["customer_realm_id"]),
                    storefront_id=uuid.UUID(seeded["storefront_id"]),
                    quantity=Decimal("5.00"),
                    unit="credit",
                    currency_code="USD",
                    source_key="test:growth-reporting:reversed",
                    allocated_at=yesterday + timedelta(hours=5),
                    reversed_at=now + timedelta(hours=5),
                    created_at=yesterday + timedelta(hours=5),
                    updated_at=now + timedelta(hours=5),
                ),
            ]
        )
        db.commit()


@pytest.mark.asyncio
async def test_growth_reporting_rollups_refresh_and_overview_aggregate_canonical_lifecycle_rows() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                refresh_result = await RefreshGrowthReportingRollupsUseCase(session).execute(window_days=7)
                assert refresh_result.rows_written > 0
                assert refresh_result.trigger_kind == "manual"
                assert {"invite", "promo", "gift", "referral"}.issubset(set(refresh_result.families_updated))

                overview = await GetGrowthReportingOverviewUseCase(session).execute(window_days=7)
                summary_by_family = {item.family: item for item in overview.family_summaries}

                assert summary_by_family["invite"].issued_total == 1
                assert summary_by_family["promo"].issued_total == 1
                assert summary_by_family["promo"].resolution_attempts_total == 2
                assert summary_by_family["promo"].resolution_accepted_total == 1
                assert summary_by_family["promo"].resolution_rejected_total == 1
                assert summary_by_family["promo"].reservations_reserved_total == 1
                assert summary_by_family["promo"].reservations_consumed_total == 1
                assert summary_by_family["gift"].issued_total == 1
                assert summary_by_family["gift"].redemption_total == 1
                assert summary_by_family["referral"].rewards_created_total == 2
                assert summary_by_family["referral"].rewards_available_total == 1
                assert summary_by_family["referral"].rewards_reversed_total == 1
                assert summary_by_family["referral"].reward_created_amount_usd == 15.0
                assert summary_by_family["referral"].reward_available_amount_usd == 10.0
                assert summary_by_family["referral"].reward_reversed_amount_usd == 5.0
                assert overview.daily_points
                assert overview.health.freshness_status == "fresh"
                assert overview.health.latest_run is not None
                assert overview.health.latest_run.trigger_kind == "manual"
                assert overview.executive_summary.total_issued == 3
                assert overview.executive_summary.dominant_family is not None

                exported = await ExportGrowthReportingOverviewUseCase(session).execute(window_days=7)
                assert exported.raw_rows
                assert exported.overview.totals.reward_created_amount_usd == 15.0
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_admin_growth_reporting_endpoints_refresh_overview_and_export(
    async_client: AsyncClient,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            admin_user, admin_password = await _create_admin_user(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)

            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={
                    "login_or_email": admin_user.login,
                    "password": admin_password,
                },
                headers={"X-Auth-Realm": "admin"},
            )
            assert login_response.status_code == 200
            admin_token = login_response.json()["access_token"]
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "X-Auth-Realm": "admin",
            }

            refresh_response = await async_client.post(
                "/api/v1/admin/growth-reporting/refresh?window_days=7",
                headers=headers,
            )
            assert refresh_response.status_code == 200
            assert refresh_response.json()["rows_written"] > 0

            overview_response = await async_client.get(
                "/api/v1/admin/growth-reporting/overview?window_days=7",
                headers=headers,
            )
            assert overview_response.status_code == 200
            overview_payload = overview_response.json()
            assert overview_payload["family_summaries"]
            assert any(item["family"] == "promo" for item in overview_payload["family_summaries"])
            assert overview_payload["health"]["freshness_status"] == "fresh"
            assert overview_payload["executive_summary"]["dominant_family"] is not None

            export_response = await async_client.get(
                "/api/v1/admin/growth-reporting/export?window_days=7",
                headers=headers,
            )
            assert export_response.status_code == 200
            assert "attachment; filename=" in export_response.headers["content-disposition"]
            export_payload = export_response.json()
            assert export_payload["raw_rows"]
            assert export_payload["totals"]["reward_created_amount_usd"] == 15.0
            assert export_payload["health"]["freshness_status"] == "fresh"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_reporting_overview_marks_stale_and_failed_refresh_health() -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)

            stale_timestamp = datetime.now(UTC) - timedelta(hours=6)
            failed_timestamp = datetime.now(UTC) - timedelta(minutes=5)

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                await RefreshGrowthReportingRollupsUseCase(session).execute(window_days=7)
                db.commit()

            with sessionmaker() as db:
                success_run = db.query(GrowthReportingRefreshRunModel).order_by(
                    GrowthReportingRefreshRunModel.finished_at.desc(),
                ).first()
                assert success_run is not None
                success_run.started_at = stale_timestamp - timedelta(seconds=10)
                success_run.finished_at = stale_timestamp
                success_run.refreshed_at = stale_timestamp
                for rollup in db.query(GrowthReportingDailyRollupModel).all():
                    rollup.refreshed_at = stale_timestamp

                db.add(
                    GrowthReportingRefreshRunModel(
                        id=uuid.uuid4(),
                        trigger_kind="worker",
                        refresh_status="failed",
                        requested_window_days=30,
                        window_start=stale_timestamp.date() - timedelta(days=29),
                        window_end=stale_timestamp.date(),
                        latest_rollup_date=stale_timestamp.date(),
                        rows_written=0,
                        families_updated=[],
                        error_message="backend refresh failed",
                        started_at=failed_timestamp - timedelta(seconds=5),
                        finished_at=failed_timestamp,
                        refreshed_at=None,
                    )
                )
                db.commit()

            with sessionmaker() as db:
                session = SyncSessionAdapter(db)
                overview = await GetGrowthReportingOverviewUseCase(session).execute(window_days=7)
                assert overview.health.freshness_status == "failed"
                assert overview.health.latest_failure_message == "backend refresh failed"
                assert overview.health.refresh_age_seconds is not None
                assert overview.health.refresh_age_seconds > 3 * 60 * 60
                assert overview.health.latest_success_at is not None
                assert overview.health.latest_run is not None
                assert overview.health.latest_run.refresh_status == "failed"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_internal_growth_reporting_refresh_endpoint_accepts_worker_secret(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_service = AuthService()
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    original_secret = settings.telegram_bot_internal_secret
    monkeypatch.setattr(settings, "telegram_bot_internal_secret", SecretStr("worker-secret"))

    try:
        async with override_realm_test_db(sessionmaker):
            seeded = await _seed_quote_context(sessionmaker, auth_service)
            _seed_growth_reporting_fixtures(sessionmaker, seeded)

            response = await async_client.post(
                "/api/v1/admin/growth-reporting/internal/refresh?window_days=7",
                headers={"X-Telegram-Bot-Secret": "worker-secret"},
            )
            assert response.status_code == 200
            assert response.json()["trigger_kind"] == "worker"
            assert response.json()["rows_written"] > 0
    finally:
        monkeypatch.setattr(settings, "telegram_bot_internal_secret", original_secret)
        app.dependency_overrides.clear()
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
