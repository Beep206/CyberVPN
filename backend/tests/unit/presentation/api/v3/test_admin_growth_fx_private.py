from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

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
from src.infrastructure.database.models.growth_risk_fx_model import FxRateSnapshotModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.models.subscription_plan_model import SubscriptionPlanModel
from src.presentation.api.v3.admin_growth_fx import (
    AdminGrowthFxConfiguredRateRequest,
    AdminGrowthFxProviderActionRequest,
    AdminGrowthFxSimulateRequest,
    AdminGrowthFxXtrTableRequest,
    approve_growth_fx_rate,
    create_configured_growth_fx_rate,
    create_growth_fx_xtr_table,
    disable_growth_fx_provider,
    enable_growth_fx_provider,
    get_growth_fx_status,
    list_growth_fx_rates,
    simulate_growth_fx_conversion,
)
from src.presentation.api.v3.admin_growth_private_catalog import (
    AdminGrowthPrivateGrantRevokeRequest,
    get_private_catalog_grant,
    list_private_catalog_grants,
    list_private_catalog_targets,
    revoke_private_catalog_grant,
)

pytestmark = [pytest.mark.asyncio]


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
