from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from prometheus_client import REGISTRY, generate_latest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.application.use_cases.growth_code_sets import fx_refresh as fx_refresh_module
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.brand_model import BrandModel
from src.infrastructure.database.models.growth_code_model import GrowthCodeModel
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthPrivateCatalogPolicyModel,
    PrivateCatalogAccessGrantModel,
)
from src.infrastructure.database.models.growth_risk_fx_model import (
    FxProviderConfigModel,
    FxProviderRefreshRunModel,
    FxRateSnapshotModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.main import app
from src.presentation.api.v1.admin import growth as admin_growth_v1
from src.presentation.api.v3.admin_growth_fx import (
    AdminGrowthFxConfiguredRateRequest,
    AdminGrowthFxProviderActionRequest,
    AdminGrowthFxRefreshRequest,
    AdminGrowthFxSimulateRequest,
    AdminGrowthFxXtrTableRequest,
    approve_growth_fx_rate,
    create_configured_growth_fx_rate,
    create_growth_fx_xtr_table,
    disable_growth_fx_provider,
    enable_growth_fx_provider,
    get_growth_fx_status,
    list_growth_fx_rates,
    refresh_growth_fx_rates,
    reject_growth_fx_rate,
    simulate_growth_fx_conversion,
)
from src.presentation.api.v3.admin_growth_private_catalog import (
    AdminGrowthPrivateGrantRevokeRequest,
    get_private_catalog_grant,
    list_private_catalog_grants,
    list_private_catalog_targets,
    revoke_private_catalog_grant,
)
from src.presentation.dependencies.database import get_db

pytestmark = [pytest.mark.asyncio]

_SENSITIVE_REASON = (
    "rotate Bearer eyJaaaaaaaa.bbbbbbbb.cccccccc "
    "vless://secret.example/config sensitive@example.test "
    "provider_secret=provider-secret-value PROMOAA-123456"
)
_SENSITIVE_FRAGMENTS = (
    "Bearer eyJaaaaaaaa.bbbbbbbb.cccccccc",
    "vless://secret.example/config",
    "sensitive@example.test",
    "provider-secret-value",
    "PROMOAA-123456",
)


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"host", b"admin.cyber-vpn.net"), (b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )


async def _admin_user(db: AsyncSession) -> AdminUserModel:
    suffix = uuid4().hex[:8]
    user = AdminUserModel(
        id=uuid4(),
        login=f"growth-fx-admin-{suffix}",
        email=f"growth-fx-admin-{suffix}@example.test",
        role=AdminRole.ADMIN.value,
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.flush()
    return user


async def _fx_snapshot_count(db: AsyncSession, provider_key: str) -> int:
    snapshots = (
        (await db.execute(select(FxRateSnapshotModel).where(FxRateSnapshotModel.provider_key == provider_key)))
        .scalars()
        .all()
    )
    return len(snapshots)


def _assert_no_sensitive_fragments(payload: object) -> None:
    serialized = str(payload)
    for fragment in _SENSITIVE_FRAGMENTS:
        assert fragment not in serialized


async def _private_grant_fixture(
    db: AsyncSession,
) -> tuple[SubscriptionPlanModel, PrivateCatalogAccessGrantModel]:
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    realm = AuthRealmModel(
        id=uuid4(),
        realm_key=f"private-realm-{suffix}",
        realm_type="customer",
        display_name="Private Test Realm",
        audience=f"cybervpn:private:{suffix}",
        cookie_namespace=f"private-{suffix}",
        status="active",
    )
    brand = BrandModel(
        id=uuid4(),
        brand_key=f"private-brand-{suffix}",
        display_name="Private Brand",
        status="active",
    )
    db.add_all([realm, brand])
    await db.flush()

    storefront = StorefrontModel(
        id=uuid4(),
        storefront_key=f"private-storefront-{suffix}",
        brand_id=brand.id,
        display_name="Private Storefront",
        host=f"private-{suffix}.example.test",
        auth_realm_id=realm.id,
        status="active",
    )
    plan = SubscriptionPlanModel(
        id=uuid4(),
        name=f"private-plan-{suffix}",
        tier="plus",
        plan_code=f"priv{suffix[:4]}",
        display_name="Private Plus",
        catalog_visibility="hidden",
        catalog_access_class="private_code_gated",
        duration_days=90,
        traffic_limit_bytes=None,
        device_limit=5,
        price_usd=Decimal("49.00"),
        price_rub=Decimal("4490.00"),
        sale_channels=["miniapp", "web"],
        traffic_policy={},
        connection_modes=["standard"],
        server_pool=["shared_plus"],
        support_sla="standard",
        dedicated_ip={},
        invite_bundle={},
        trial_eligible=False,
        features={},
        is_active=True,
        sort_order=10,
    )
    db.add_all([storefront, plan])
    await db.flush()

    policy_version = PolicyVersionModel(
        id=uuid4(),
        policy_family="growth_private_catalog",
        policy_key=f"private-policy-{suffix}",
        subject_type="global",
        version_number=1,
        payload={"target_plan_ids": [str(plan.id)]},
        approval_state="approved",
        version_status="active",
        effective_from=now - timedelta(minutes=1),
    )
    db.add(policy_version)
    await db.flush()

    growth_code = GrowthCodeModel(
        id=uuid4(),
        code_hash=f"private-hash-{suffix}",
        code_prefix="PRIV",
        code_type="promo",
        status="active",
        issuer_type="admin",
        code_namespace="customer_input",
        policy_version_id=policy_version.id,
    )
    db.add(growth_code)
    await db.flush()

    policy = GrowthPrivateCatalogPolicyModel(
        id=uuid4(),
        policy_version_id=policy_version.id,
        growth_code_id=growth_code.id,
        unlock_mode="grant_private_plan",
        target_plan_ids=[str(plan.id)],
        target_offer_ids=[],
        target_offer_keys=[],
        allowed_storefront_ids=[str(storefront.id)],
        allowed_channels=["miniapp"],
        grant_ttl_seconds=3600,
        max_quote_conversions=2,
        consume_mode="checkout",
        requires_auth=False,
        is_active=True,
    )
    db.add(policy)
    await db.flush()

    grant = PrivateCatalogAccessGrantModel(
        id=uuid4(),
        policy_id=policy.id,
        policy_version_id=policy_version.id,
        growth_code_id=growth_code.id,
        code_set_hash=f"code-set-{suffix}",
        grant_token_hash=f"grant-token-{suffix}",
        anonymous_session_id=f"anon-{suffix}",
        auth_realm_id=realm.id,
        storefront_id=storefront.id,
        sale_channel="miniapp",
        allowed_plan_ids=[str(plan.id)],
        allowed_offer_ids=[],
        status="issued",
        max_quote_conversions=2,
        quote_conversions_count=0,
        issued_at=now,
        expires_at=now + timedelta(hours=1),
        metadata_={"matched_prefixes": ["PRIV"]},
    )
    db.add(grant)
    await db.flush()
    return plan, grant


async def test_admin_growth_fx_operations_create_simulate_toggle_and_audit(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    approver = await _admin_user(db)
    rate = await create_configured_growth_fx_rate(
        AdminGrowthFxConfiguredRateRequest(
            base_currency="EUR",
            quote_currency="USD",
            rate="1.1000",
            configured_rate_version="manual-eur-usd-1",
            valid_for_seconds=3600,
            change_reason="seed configured rate for support preview",
        ),
        _request("/api/v3/admin/growth/fx/configured-rates"),
        current_user=admin,
        db=db,
    )
    assert rate.source_type == "configured"
    assert rate.provider_key == "admin_configured"
    assert rate.status == "pending_approval"

    with pytest.raises(HTTPException) as pending_simulation:
        await simulate_growth_fx_conversion(
            AdminGrowthFxSimulateRequest(
                source_amount="5",
                source_currency="EUR",
                target_currency="USD",
                eligible_discount_base="99",
                conversion_mode="configured",
                provider_key="admin_configured",
            ),
            _current_user=admin,
            db=db,
        )
    assert pending_simulation.value.status_code == 409
    assert pending_simulation.value.detail["code"] == "FX_RATE_UNAVAILABLE"

    with pytest.raises(HTTPException) as self_approval:
        await approve_growth_fx_rate(
            rate.id,
            AdminGrowthFxProviderActionRequest(change_reason="self approval must fail"),
            _request(f"/api/v3/admin/growth/fx/rates/{rate.id}/approve"),
            current_user=admin,
            db=db,
        )
    assert self_approval.value.status_code == 409
    assert self_approval.value.detail["code"] == "FX_RATE_SELF_APPROVAL_FORBIDDEN"

    approved_rate = await approve_growth_fx_rate(
        rate.id,
        AdminGrowthFxProviderActionRequest(change_reason="checker approves support FX override"),
        _request(f"/api/v3/admin/growth/fx/rates/{rate.id}/approve"),
        current_user=approver,
        db=db,
    )
    assert approved_rate.status == "active"
    assert approved_rate.metadata["approved_by_admin_user_id"] == str(approver.id)

    simulation = await simulate_growth_fx_conversion(
        AdminGrowthFxSimulateRequest(
            source_amount="5",
            source_currency="EUR",
            target_currency="USD",
            eligible_discount_base="99",
            conversion_mode="configured",
            provider_key="admin_configured",
        ),
        _current_user=admin,
        db=db,
    )
    assert simulation.applied_amount == "5.50"
    assert simulation.no_rerate is True
    assert simulation.rate_snapshot["configured_rate_version"] == "manual-eur-usd-1"

    xtr = await create_growth_fx_xtr_table(
        AdminGrowthFxXtrTableRequest(
            fiat_currency="USD",
            xtr_per_unit="50",
            table_version="xtr-2026-06",
            change_reason="seed managed xtr table",
        ),
        _request("/api/v3/admin/growth/fx/xtr-tables"),
        current_user=admin,
        db=db,
    )
    assert xtr.source_type == "managed_xtr"
    assert xtr.status == "pending_approval"
    assert xtr.metadata["managed_xtr"] is True
    approved_xtr = await approve_growth_fx_rate(
        xtr.id,
        AdminGrowthFxProviderActionRequest(change_reason="checker approves XTR table"),
        _request(f"/api/v3/admin/growth/fx/rates/{xtr.id}/approve"),
        current_user=approver,
        db=db,
    )
    assert approved_xtr.status == "active"

    rates = await list_growth_fx_rates(
        base_currency="EUR",
        quote_currency="USD",
        provider_key="admin_configured",
        source_type=None,
        status_filter="active",
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert rates.total >= 1
    assert rate.id in {item.id for item in rates.items}

    disabled = await disable_growth_fx_provider(
        "admin_configured",
        AdminGrowthFxProviderActionRequest(change_reason="test disable provider"),
        _request("/api/v3/admin/growth/fx/providers/admin_configured/disable"),
        current_user=admin,
        db=db,
    )
    assert disabled.disabled_rate_count >= 1

    pending_rate = await create_configured_growth_fx_rate(
        AdminGrowthFxConfiguredRateRequest(
            base_currency="GBP",
            quote_currency="USD",
            rate="1.2500",
            configured_rate_version="manual-gbp-usd-pending",
            valid_for_seconds=3600,
            change_reason="pending rate must stay pending during provider enable",
        ),
        _request("/api/v3/admin/growth/fx/configured-rates"),
        current_user=admin,
        db=db,
    )
    enabled = await enable_growth_fx_provider(
        "admin_configured",
        AdminGrowthFxProviderActionRequest(change_reason="test enable provider"),
        _request("/api/v3/admin/growth/fx/providers/admin_configured/enable"),
        current_user=admin,
        db=db,
    )
    assert enabled.active_rate_count >= 1
    persisted_pending_rate = await db.get(FxRateSnapshotModel, pending_rate.id)
    assert persisted_pending_rate is not None
    assert persisted_pending_rate.status == "pending_approval"

    status_response = await get_growth_fx_status(_current_user=admin, db=db)
    assert status_response.active_rate_count >= 1
    audit_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id == admin.id,
                    AuditLog.entity_type.in_(["fx_rate_snapshot", "fx_provider"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert "growth_fx.configured_rate.created" in audit_actions
    assert "growth_fx.xtr_table.created" in audit_actions
    assert "growth_fx.provider.disabled" in audit_actions
    assert "growth_fx.provider.enabled" in audit_actions
    approver_audit_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id == approver.id,
                    AuditLog.entity_type == "fx_rate_snapshot",
                )
            )
        )
        .scalars()
        .all()
    )
    assert approver_audit_actions.count("growth_fx.rate.approved") == 2


async def test_admin_growth_fx_provider_disable_blocks_approval_and_simulation(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    approver = await _admin_user(db)
    now = datetime.now(UTC)
    provider_key = f"provider-disable-{uuid4().hex[:8]}"
    config = FxProviderConfigModel(
        id=uuid4(),
        provider_key=provider_key,
        priority=1,
        enabled=True,
        supported_pairs=[{"source_currency": "EUR", "target_currency": "USD"}],
        stale_after_seconds=60,
        rate_ttl_seconds=3600,
        requires_admin_approval=True,
        metadata_={},
    )
    active_snapshot = FxRateSnapshotModel(
        id=uuid4(),
        provider_config_id=config.id,
        base_currency="EUR",
        quote_currency="USD",
        rate=Decimal("1.1000"),
        inverse_rate=Decimal("0.9090909091"),
        source_type="provider",
        provider_key=provider_key,
        provider_priority=1,
        provider_rate_id="provider-disable-active",
        observed_at=now,
        fetched_at=now,
        valid_until=now + timedelta(hours=1),
        status="active",
        approval_state="approved",
        metadata_={"provider_enabled": True},
    )
    pending_snapshot = FxRateSnapshotModel(
        id=uuid4(),
        provider_config_id=config.id,
        base_currency="EUR",
        quote_currency="USD",
        rate=Decimal("1.1200"),
        inverse_rate=Decimal("0.8928571429"),
        source_type="provider",
        provider_key=provider_key,
        provider_priority=1,
        provider_rate_id="provider-disable-pending",
        observed_at=now + timedelta(seconds=1),
        fetched_at=now + timedelta(seconds=1),
        valid_until=now + timedelta(hours=1),
        status="pending_approval",
        approval_state="pending",
        metadata_={},
    )
    db.add_all([config, active_snapshot, pending_snapshot])
    await db.flush()

    simulation = await simulate_growth_fx_conversion(
        AdminGrowthFxSimulateRequest(
            source_amount="5",
            source_currency="EUR",
            target_currency="USD",
            eligible_discount_base="99",
            conversion_mode="market",
            provider_key=provider_key,
        ),
        _current_user=admin,
        db=db,
    )
    assert simulation.applied_amount == "5.50"
    assert simulation.rate_snapshot["provider"] == provider_key

    await disable_growth_fx_provider(
        provider_key,
        AdminGrowthFxProviderActionRequest(change_reason="provider disabled after compromise"),
        _request(f"/api/v3/admin/growth/fx/providers/{provider_key}/disable"),
        current_user=admin,
        db=db,
    )
    await db.refresh(config)
    await db.refresh(active_snapshot)
    assert config.enabled is False
    assert active_snapshot.status == "disabled"

    with pytest.raises(HTTPException) as simulation_error:
        await simulate_growth_fx_conversion(
            AdminGrowthFxSimulateRequest(
                source_amount="5",
                source_currency="EUR",
                target_currency="USD",
                eligible_discount_base="99",
                conversion_mode="market",
                provider_key=provider_key,
            ),
            _current_user=admin,
            db=db,
        )
    assert simulation_error.value.status_code == 409
    assert simulation_error.value.detail["code"] == "FX_RATE_UNAVAILABLE"

    with pytest.raises(HTTPException) as approval_error:
        await approve_growth_fx_rate(
            pending_snapshot.id,
            AdminGrowthFxProviderActionRequest(change_reason="approve after provider disable"),
            _request(f"/api/v3/admin/growth/fx/rates/{pending_snapshot.id}/approve"),
            current_user=approver,
            db=db,
        )
    assert approval_error.value.status_code == 409
    assert approval_error.value.detail["code"] == "FX_PROVIDER_DISABLED"


async def test_admin_growth_fx_refresh_reject_approve_and_metrics(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = await _admin_user(db)
    approver = await _admin_user(db)
    config = FxProviderConfigModel(
        id=uuid4(),
        provider_key="ecb-refresh-test",
        priority=4,
        enabled=True,
        supported_pairs=[{"source_currency": "EUR", "target_currency": "USD"}],
        stale_after_seconds=60,
        rate_ttl_seconds=3600,
        requires_admin_approval=True,
        metadata_={
            "provider_rates": [
                {
                    "source_currency": "EUR",
                    "target_currency": "USD",
                    "rate": "1.1100",
                    "provider_rate_id": "ecb-eur-usd-1",
                    "observed_at": "2026-06-27T00:00:00+00:00",
                    "fetched_at": "2026-06-27T00:00:00+00:00",
                    "valid_until": "2026-06-27T01:00:00+00:00",
                }
            ]
        },
    )
    db.add(config)
    await db.flush()

    refresh = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="ecb-refresh-test",
            base_currency="eur",
            quote_currency="usd",
            idempotency_key="ecb-refresh-test-key-1",
            change_reason="operator refreshes provider rates",
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    assert [run.status for run in refresh.runs] == ["succeeded"]
    assert len(refresh.created_snapshots) == 1
    pending = refresh.created_snapshots[0]
    assert pending.provider_key == "ecb-refresh-test"
    assert pending.provider_priority == 4
    assert pending.status == "pending_approval"
    assert pending.approval_state == "pending"
    assert pending.checksum and len(pending.checksum) == 64
    assert pending.raw_provider_payload_hash and len(pending.raw_provider_payload_hash) == 64

    retry = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="ecb-refresh-test",
            base_currency="EUR",
            quote_currency="USD",
            idempotency_key="ecb-refresh-test-key-1",
            change_reason="operator refreshes provider rates",
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    assert retry.runs[0].id == refresh.runs[0].id
    assert retry.created_snapshots == []

    rejected = await reject_growth_fx_rate(
        pending.id,
        AdminGrowthFxProviderActionRequest(change_reason="provider payload failed review"),
        _request(f"/api/v3/admin/growth/fx/rates/{pending.id}/reject"),
        current_user=approver,
        db=db,
    )
    assert rejected.status == "rejected"
    assert rejected.approval_state == "rejected"
    assert rejected.rejection_reason == "provider payload failed review"

    snapshot_count_after_reject = await _fx_snapshot_count(db, "ecb-refresh-test")
    await disable_growth_fx_provider(
        "ecb-refresh-test",
        AdminGrowthFxProviderActionRequest(change_reason="disable provider after failed review"),
        _request("/api/v3/admin/growth/fx/providers/ecb-refresh-test/disable"),
        current_user=admin,
        db=db,
    )
    await db.refresh(config)
    assert config.enabled is False

    with pytest.raises(HTTPException) as disabled_refresh:
        await refresh_growth_fx_rates(
            AdminGrowthFxRefreshRequest(
                provider_key="ecb-refresh-test",
                base_currency="EUR",
                quote_currency="USD",
                idempotency_key="ecb-refresh-disabled-key",
                change_reason="disabled provider must not refresh",
            ),
            _request("/api/v3/admin/growth/fx/rates/refresh"),
            current_user=admin,
            db=db,
        )
    assert disabled_refresh.value.status_code == 404
    assert disabled_refresh.value.detail["code"] == "FX_PROVIDER_CONFIG_NOT_FOUND"
    assert await _fx_snapshot_count(db, "ecb-refresh-test") == snapshot_count_after_reject

    await enable_growth_fx_provider(
        "ecb-refresh-test",
        AdminGrowthFxProviderActionRequest(change_reason="enable provider for corrected refresh"),
        _request("/api/v3/admin/growth/fx/providers/ecb-refresh-test/enable"),
        current_user=admin,
        db=db,
    )
    await db.refresh(config)
    rejected_model = await db.get(FxRateSnapshotModel, rejected.id)
    assert rejected_model is not None
    assert config.enabled is True
    assert rejected_model.approval_state == "rejected"
    assert rejected_model.status == "rejected"

    with pytest.raises(HTTPException) as no_approved_snapshot:
        await simulate_growth_fx_conversion(
            AdminGrowthFxSimulateRequest(
                source_amount="5",
                source_currency="EUR",
                target_currency="USD",
                eligible_discount_base="99",
                conversion_mode="market",
                provider_key="ecb-refresh-test",
            ),
            _current_user=admin,
            db=db,
        )
    assert no_approved_snapshot.value.status_code == 409
    assert no_approved_snapshot.value.detail["code"] == "FX_RATE_UNAVAILABLE"

    config.metadata_ = {
        "provider_rates": [
            {
                "source_currency": "EUR",
                "target_currency": "USD",
                "rate": "1.1150",
                "provider_rate_id": "ecb-eur-usd-implicit",
                "observed_at": "2026-06-27T04:00:00+00:00",
                "fetched_at": "2026-06-27T04:00:00+00:00",
                "valid_until": "2030-06-27T05:00:00+00:00",
            }
        ]
    }
    await db.flush()

    class FrozenFxRefreshDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            del tz
            return datetime(2026, 6, 27, 4, 30, tzinfo=UTC)

    monkeypatch.setattr(fx_refresh_module, "datetime", FrozenFxRefreshDateTime)
    implicit_refresh = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="ecb-refresh-test",
            base_currency="EUR",
            quote_currency="USD",
            change_reason="implicit retry-safe refresh",
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    implicit_retry = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="ecb-refresh-test",
            base_currency="EUR",
            quote_currency="USD",
            change_reason="implicit retry-safe refresh",
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    assert implicit_refresh.runs[0].id == implicit_retry.runs[0].id
    assert len(implicit_refresh.created_snapshots) == 1
    assert implicit_retry.created_snapshots == []

    config.metadata_ = {
        "provider_rates": [
            {
                "source_currency": "EUR",
                "target_currency": "USD",
                "rate": "1.1200",
                "provider_rate_id": "ecb-eur-usd-2",
                "observed_at": "2026-06-27T02:00:00+00:00",
                "fetched_at": "2026-06-27T02:00:00+00:00",
                "valid_until": "2030-06-27T03:00:00+00:00",
            }
        ]
    }
    await db.flush()
    second_refresh = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="ecb-refresh-test",
            idempotency_key="ecb-refresh-test-key-2",
            change_reason="operator refreshes corrected provider rates",
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    approved = await approve_growth_fx_rate(
        second_refresh.created_snapshots[0].id,
        AdminGrowthFxProviderActionRequest(change_reason="checker approves provider snapshot"),
        _request(f"/api/v3/admin/growth/fx/rates/{second_refresh.created_snapshots[0].id}/approve"),
        current_user=approver,
        db=db,
    )
    assert approved.status == "active"
    assert approved.approval_state == "approved"
    assert approved.approved_by_admin_id == approver.id

    simulation = await simulate_growth_fx_conversion(
        AdminGrowthFxSimulateRequest(
            source_amount="5",
            source_currency="EUR",
            target_currency="USD",
            eligible_discount_base="99",
            conversion_mode="market",
            provider_key="ecb-refresh-test",
        ),
        _current_user=admin,
        db=db,
    )
    assert simulation.applied_amount == "5.60"
    assert simulation.rate_snapshot["provider"] == "ecb-refresh-test"

    now = datetime.now(UTC)
    stale_snapshot = FxRateSnapshotModel(
        id=uuid4(),
        base_currency="GBP",
        quote_currency="USD",
        rate=Decimal("1.2000"),
        inverse_rate=Decimal("0.83333333333333"),
        source_type="provider",
        provider_key="ecb-refresh-test",
        provider_priority=4,
        provider_rate_id="ecb-gbp-usd-stale",
        observed_at=now - timedelta(hours=3),
        fetched_at=now - timedelta(hours=3),
        valid_until=now - timedelta(hours=2),
        status="active",
        approval_state="approved",
        approved_by_admin_id=approver.id,
        approved_at=now - timedelta(hours=3),
        checksum="a" * 64,
        metadata_={},
    )
    db.add(stale_snapshot)
    await db.flush()

    status_response = await get_growth_fx_status(_current_user=admin, db=db)
    assert status_response.stale_rate_count >= 1
    metric_payload = generate_latest(REGISTRY).decode("utf-8")
    assert "growth_fx_rate_snapshot_freshness_seconds" in metric_payload
    assert "growth_fx_rate_stale_total" in metric_payload
    assert 'pair="gbp_usd"' in metric_payload
    assert 'provider="ecb-refresh-test"' in metric_payload
    assert "growth_fx_conversion_failures_total" in metric_payload

    refresh_runs = (
        (
            await db.execute(
                select(FxProviderRefreshRunModel).where(FxProviderRefreshRunModel.provider_key == "ecb-refresh-test")
            )
        )
        .scalars()
        .all()
    )
    assert {run.status for run in refresh_runs} == {"succeeded"}

    audit_actions = (
        (
            await db.execute(
                select(AuditLog.action).where(
                    AuditLog.admin_id.in_([admin.id, approver.id]),
                    AuditLog.entity_type.in_(["fx_provider_refresh_run", "fx_rate_snapshot"]),
                )
            )
        )
        .scalars()
        .all()
    )
    assert "growth_fx.rate.refresh_requested" in audit_actions
    assert "growth_fx.rate.rejected" in audit_actions
    assert "growth_fx.rate.approved" in audit_actions


async def test_admin_growth_fx_sanitizes_sensitive_change_reasons(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    approver = await _admin_user(db)

    configured = await create_configured_growth_fx_rate(
        AdminGrowthFxConfiguredRateRequest(
            base_currency="USD",
            quote_currency="RUB",
            rate="91.10",
            configured_rate_version="sensitive-configured-v1",
            valid_for_seconds=3600,
            change_reason=_SENSITIVE_REASON,
        ),
        _request("/api/v3/admin/growth/fx/configured-rates"),
        current_user=admin,
        db=db,
    )
    assert "[REDACTED]" in str(configured.metadata)
    _assert_no_sensitive_fragments(configured.metadata)

    approved = await approve_growth_fx_rate(
        configured.id,
        AdminGrowthFxProviderActionRequest(change_reason=_SENSITIVE_REASON),
        _request(f"/api/v3/admin/growth/fx/rates/{configured.id}/approve"),
        current_user=approver,
        db=db,
    )
    assert "[REDACTED]" in str(approved.metadata)
    _assert_no_sensitive_fragments(approved.metadata)

    reject_candidate = await create_configured_growth_fx_rate(
        AdminGrowthFxConfiguredRateRequest(
            base_currency="EUR",
            quote_currency="RUB",
            rate="99.50",
            configured_rate_version="sensitive-configured-v2",
            valid_for_seconds=3600,
            change_reason=_SENSITIVE_REASON,
        ),
        _request("/api/v3/admin/growth/fx/configured-rates"),
        current_user=admin,
        db=db,
    )
    rejected = await reject_growth_fx_rate(
        reject_candidate.id,
        AdminGrowthFxProviderActionRequest(change_reason=_SENSITIVE_REASON),
        _request(f"/api/v3/admin/growth/fx/rates/{reject_candidate.id}/reject"),
        current_user=approver,
        db=db,
    )
    assert rejected.rejection_reason is not None
    assert "[REDACTED]" in rejected.rejection_reason
    _assert_no_sensitive_fragments(rejected.metadata)

    config = FxProviderConfigModel(
        id=uuid4(),
        provider_key="sensitive-refresh-provider",
        priority=7,
        enabled=True,
        supported_pairs=[{"source_currency": "GBP", "target_currency": "USD"}],
        stale_after_seconds=60,
        rate_ttl_seconds=3600,
        requires_admin_approval=True,
        metadata_={
            "provider_rates": [
                {
                    "source_currency": "GBP",
                    "target_currency": "USD",
                    "rate": "1.2700",
                    "provider_rate_id": "sensitive-refresh-rate",
                    "observed_at": "2026-06-27T05:00:00+00:00",
                    "fetched_at": "2026-06-27T05:00:00+00:00",
                    "valid_until": "2030-06-27T06:00:00+00:00",
                }
            ]
        },
    )
    db.add(config)
    await db.flush()

    refresh = await refresh_growth_fx_rates(
        AdminGrowthFxRefreshRequest(
            provider_key="sensitive-refresh-provider",
            base_currency="GBP",
            quote_currency="USD",
            idempotency_key="sensitive-refresh-key",
            change_reason=_SENSITIVE_REASON,
        ),
        _request("/api/v3/admin/growth/fx/rates/refresh"),
        current_user=admin,
        db=db,
    )
    _assert_no_sensitive_fragments(refresh.runs[0].model_dump())
    _assert_no_sensitive_fragments(refresh.created_snapshots[0].metadata)
    persisted_run = await db.get(FxProviderRefreshRunModel, refresh.runs[0].id)
    persisted_snapshot = await db.get(FxRateSnapshotModel, refresh.created_snapshots[0].id)
    assert persisted_run is not None
    assert persisted_snapshot is not None
    _assert_no_sensitive_fragments(persisted_run.metadata_)
    _assert_no_sensitive_fragments(persisted_snapshot.metadata_)

    await disable_growth_fx_provider(
        "sensitive-refresh-provider",
        AdminGrowthFxProviderActionRequest(change_reason=_SENSITIVE_REASON),
        _request("/api/v3/admin/growth/fx/providers/sensitive-refresh-provider/disable"),
        current_user=admin,
        db=db,
    )
    audits = (
        (
            await db.execute(
                select(AuditLog).where(
                    AuditLog.admin_id.in_([admin.id, approver.id]),
                    AuditLog.action.like("growth_fx.%"),
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits
    for audit in audits:
        _assert_no_sensitive_fragments(audit.old_value)
        _assert_no_sensitive_fragments(audit.new_value)


async def test_internal_growth_fx_refresh_endpoint_runs_scheduled_provider_refresh(
    db: AsyncSession,
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_secret = "StrongBackendInternalCredentialForChecksOnly"
    telegram_secret = "StrongTelegramInternalCredentialForChecksOnly"
    monkeypatch.setattr(admin_growth_v1.settings, "backend_internal_secret", SecretStr(backend_secret))
    monkeypatch.setattr(admin_growth_v1.settings, "telegram_bot_internal_secret", SecretStr(telegram_secret))

    class FrozenDateTime(datetime):
        calls = [
            datetime(2026, 6, 27, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 27, 6, 13, tzinfo=UTC),
        ]
        last = calls[-1]

        @classmethod
        def now(cls, tz=None):
            value = cls.calls.pop(0) if cls.calls else cls.last
            return value.astimezone(tz) if tz is not None else value

    monkeypatch.setattr(admin_growth_v1, "datetime", FrozenDateTime)

    existing_configs = (await db.execute(select(FxProviderConfigModel))).scalars().all()
    for existing in existing_configs:
        existing.enabled = False
    await db.flush()

    provider_key = f"scheduled-refresh-provider-{uuid4().hex[:8]}"
    config = FxProviderConfigModel(
        id=uuid4(),
        provider_key=provider_key,
        priority=2,
        enabled=True,
        supported_pairs=[{"source_currency": "USD", "target_currency": "RUB"}],
        stale_after_seconds=60,
        rate_ttl_seconds=3600,
        requires_admin_approval=False,
        metadata_={
            "provider_rates": [
                {
                    "source_currency": "USD",
                    "target_currency": "RUB",
                    "rate": "90.2500",
                    "provider_rate_id": "scheduled-usd-rub",
                }
            ]
        },
    )
    db.add(config)
    await db.flush()

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        admin_host_headers = {"Host": "admin.cyber-vpn.net"}
        missing_secret = await async_client.post(
            "/api/v1/admin/growth-fx/internal/refresh",
            headers=admin_host_headers,
        )
        wrong_secret = await async_client.post(
            "/api/v1/admin/growth-fx/internal/refresh",
            headers={**admin_host_headers, "X-Backend-Internal-Secret": "wrong-secret"},
        )
        telegram_secret_response = await async_client.post(
            "/api/v1/admin/growth-fx/internal/refresh",
            headers={**admin_host_headers, "X-Telegram-Bot-Secret": telegram_secret},
        )
        first_response = await async_client.post(
            "/api/v1/admin/growth-fx/internal/refresh",
            headers={**admin_host_headers, "X-Backend-Internal-Secret": backend_secret},
        )
        retry_response = await async_client.post(
            "/api/v1/admin/growth-fx/internal/refresh",
            headers={**admin_host_headers, "X-Backend-Internal-Secret": backend_secret},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert missing_secret.status_code == 401
    assert wrong_secret.status_code == 401
    assert telegram_secret_response.status_code == 401
    assert first_response.status_code == 200, first_response.text
    assert retry_response.status_code == 200, retry_response.text
    first_payload = first_response.json()
    retry_payload = retry_response.json()
    assert first_payload["skipped"] is False
    assert first_payload["run_count"] == 1
    assert first_payload["created_snapshot_count"] == 1
    assert first_payload["run_statuses"] == {"succeeded": 1}
    assert retry_payload["run_count"] == 1
    assert retry_payload["created_snapshot_count"] == 0
    assert retry_payload["run_statuses"] == {"succeeded": 1}

    runs = (
        (
            await db.execute(
                select(FxProviderRefreshRunModel).where(FxProviderRefreshRunModel.provider_key == provider_key)
            )
        )
        .scalars()
        .all()
    )
    snapshots = (
        (await db.execute(select(FxRateSnapshotModel).where(FxRateSnapshotModel.provider_key == provider_key)))
        .scalars()
        .all()
    )
    assert len(runs) == 1
    assert len(snapshots) == 1
    assert snapshots[0].approval_state == "approved"
    assert snapshots[0].status == "active"


async def test_admin_growth_private_targets_grants_and_revoke_audit(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    plan, grant = await _private_grant_fixture(db)

    targets = await list_private_catalog_targets(
        active_only=True,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert plan.id in {item.id for item in targets.items}
    target = next(item for item in targets.items if item.id == plan.id)
    assert target.policy_count == 1

    grants = await list_private_catalog_grants(
        status_filter="issued",
        user_id=None,
        anonymous_session_id=grant.anonymous_session_id,
        storefront_id=None,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert grants.total == 1
    assert grants.items[0].id == grant.id

    detail = await get_private_catalog_grant(grant.id, _current_user=admin, db=db)
    assert detail.allowed_plan_ids == [str(plan.id)]
    assert detail.metadata["matched_prefixes"] == ["PRIV"]

    conflict_payload = AdminGrowthPrivateGrantRevokeRequest(
        expected_status="attached",
        reason="stale support screen",
    )
    with pytest.raises(HTTPException) as conflict:
        await revoke_private_catalog_grant(
            grant.id,
            conflict_payload,
            _request(f"/api/v3/admin/growth/private-grants/{grant.id}/revoke"),
            current_user=admin,
            db=db,
        )
    assert conflict.value.status_code == 409
    assert conflict.value.detail["code"] == "PRIVATE_GRANT_STATE_CONFLICT"

    revoked = await revoke_private_catalog_grant(
        grant.id,
        AdminGrowthPrivateGrantRevokeRequest(
            expected_status="issued",
            reason="support requested private grant revocation",
        ),
        _request(f"/api/v3/admin/growth/private-grants/{grant.id}/revoke"),
        current_user=admin,
        db=db,
    )
    assert revoked.status == "revoked"
    assert revoked.revoked_reason == "support requested private grant revocation"
    assert revoked.revoked_at is not None

    audit_action = await db.scalar(
        select(AuditLog.action).where(
            AuditLog.admin_id == admin.id,
            AuditLog.entity_type == "private_catalog_access_grant",
            AuditLog.entity_id == str(grant.id),
        )
    )
    assert audit_action == "growth_private_grant.revoked"
