from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.application.services.config_service import CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.customer_onboarding_model import (
    CustomerOnboardingCodeApplicationModel,
    CustomerOnboardingStateModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.system_config_model import SystemConfigModel
from src.presentation.api.v3.admin_growth_onboarding import (
    AdminGrowthOnboardingRuntimeUpdateRequest,
    AdminGrowthOnboardingStateResetRequest,
    get_growth_onboarding_settings,
    get_growth_onboarding_state,
    list_growth_onboarding_applications,
    list_growth_onboarding_states,
    reset_growth_onboarding_state,
    update_growth_onboarding_settings,
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
        login=f"growth-onboarding-admin-{suffix}",
        email=f"growth-onboarding-admin-{suffix}@example.test",
        role=AdminRole.ADMIN.value,
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.flush()
    return user


async def _onboarding_fixture(
    db: AsyncSession,
    admin: AdminUserModel,
) -> tuple[MobileUserModel, CustomerOnboardingStateModel, CustomerOnboardingCodeApplicationModel]:
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    db.add(
        SystemConfigModel(
            key=CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
            value={
                "post_registration_code_prompt_enabled": True,
                "web_otp_enabled": True,
                "telegram_miniapp_enabled": False,
                "state_store_ready": True,
                "flow_key": "post_registration_growth_code_v1",
                "version": 7,
                "allowed_code_types": ["promo", "invite", "gift"],
                "allow_referral_input": False,
                "allow_partner_input": False,
            },
            description="test onboarding runtime",
            updated_by=admin.id,
        )
    )
    mobile_user = MobileUserModel(
        id=uuid4(),
        email=f"growth-onboarding-{suffix}@example.test",
        password_hash="not-a-real-password",
        username=f"growth_onboarding_{suffix}",
        notification_prefs={},
        is_active=True,
        status="active",
    )
    db.add(mobile_user)
    await db.flush()

    state = CustomerOnboardingStateModel(
        id=uuid4(),
        mobile_user_id=mobile_user.id,
        flow_key="post_registration_growth_code_v1",
        flow_version=7,
        source_channel="web",
        status="completed",
        skippable=True,
        first_eligible_at=now - timedelta(minutes=5),
        first_shown_at=now - timedelta(minutes=4),
        last_shown_at=now - timedelta(minutes=3),
        display_count=2,
        submitted_at=now - timedelta(minutes=2),
        completed_at=now - timedelta(minutes=2),
        result_payload={
            "message_key": "onboarding.code.accepted",
            "masked_code": "PROM••••",
            "next_destination": "/subscriptions",
        },
        referral_terminal_state="claimed",
        auth_channel="web_otp",
        return_route_key="subscriptions",
    )
    db.add(state)
    await db.flush()

    application = CustomerOnboardingCodeApplicationModel(
        id=uuid4(),
        onboarding_state_id=state.id,
        mobile_user_id=mobile_user.id,
        resolved_code_type="promo",
        action_context="post_registration",
        result="accepted",
        idempotency_key="onboarding-idem-secret",
        code_hash="c" * 64,
        code_prefix="PROM••••",
        safe_result_snapshot={
            "message_key": "onboarding.code.accepted",
            "masked_code": "PROM••••",
            "next_destination": "/subscriptions",
        },
        referral_terminal_state="claimed",
        auth_channel="web_otp",
        return_route_key="subscriptions",
    )
    db.add(application)
    await db.flush()
    state.result_code_application_id = application.id
    await db.flush()
    return mobile_user, state, application


async def test_admin_growth_onboarding_settings_inspector_reset_and_audit(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    mobile_user, state, application = await _onboarding_fixture(db, admin)

    settings = await get_growth_onboarding_settings(_current_user=admin, db=db)
    assert settings.available is True
    assert settings.flow_key == "post_registration_growth_code_v1"
    assert settings.version == 7
    assert settings.updated_by_admin_user_id == admin.id

    updated_settings = await update_growth_onboarding_settings(
        AdminGrowthOnboardingRuntimeUpdateRequest(
            allow_referral_input=True,
            version=8,
            change_reason="enable referral input for support validation",
        ),
        _request("/api/v3/admin/growth/onboarding/settings"),
        current_user=admin,
        db=db,
    )
    assert updated_settings.allow_referral_input is True
    assert updated_settings.allow_partner_input is False
    assert updated_settings.version == 8
    persisted_config = await db.get(SystemConfigModel, CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY)
    assert persisted_config is not None
    assert persisted_config.value["allow_referral_input"] is True
    assert persisted_config.value["allow_partner_input"] is False
    assert persisted_config.value["version"] == 8
    assert "change_reason" not in persisted_config.value

    settings_audit = await db.scalar(
        select(AuditLog).where(
            AuditLog.admin_id == admin.id,
            AuditLog.action == "growth_onboarding_settings.updated",
            AuditLog.entity_id == CUSTOMER_ONBOARDING_RUNTIME_CONFIG_KEY,
        )
    )
    assert settings_audit is not None
    assert settings_audit.old_value["allow_referral_input"] is False
    assert settings_audit.new_value["allow_referral_input"] is True
    assert settings_audit.new_value["reason"] == "enable referral input for support validation"

    states = await list_growth_onboarding_states(
        mobile_user_id=mobile_user.id,
        status_filter="completed",
        flow_key=None,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert states.total == 1
    assert states.items[0].id == state.id
    assert states.items[0].application_count == 1
    assert states.items[0].result_payload["masked_code"] == "PROM••••"

    applications = await list_growth_onboarding_applications(
        onboarding_state_id=state.id,
        mobile_user_id=None,
        result_filter="accepted",
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert applications.total == 1
    assert applications.items[0].id == application.id
    assert applications.items[0].idempotency_key_hash == hashlib.sha256(b"onboarding-idem-secret").hexdigest()
    assert "onboarding-idem-secret" not in applications.items[0].model_dump_json()
    assert "PROMO-RAW" not in applications.items[0].model_dump_json()

    detail = await get_growth_onboarding_state(state.id, _current_user=admin, db=db)
    assert detail.status == "completed"
    assert detail.application_count == 1

    with pytest.raises(HTTPException) as conflict:
        await reset_growth_onboarding_state(
            state.id,
            AdminGrowthOnboardingStateResetRequest(
                expected_status="pending",
                reason="operator stale support screen",
            ),
            _request(f"/api/v3/admin/growth/onboarding/states/{state.id}/reset"),
            current_user=admin,
            db=db,
        )
    assert conflict.value.status_code == 409
    assert conflict.value.detail["code"] == "ONBOARDING_STATE_CONFLICT"

    reset = await reset_growth_onboarding_state(
        state.id,
        AdminGrowthOnboardingStateResetRequest(
            expected_status="completed",
            reason="support requested onboarding retry",
        ),
        _request(f"/api/v3/admin/growth/onboarding/states/{state.id}/reset"),
        current_user=admin,
        db=db,
    )
    assert reset.status == "pending"
    assert reset.display_count == 0
    assert reset.result_code_application_id is None
    assert reset.result_payload["message_key"] == "onboarding.reset_by_admin"
    assert reset.application_count == 1

    persisted_state = await db.get(CustomerOnboardingStateModel, state.id)
    assert persisted_state is not None
    assert persisted_state.status == "pending"
    assert persisted_state.completed_at is None

    audit = await db.scalar(
        select(AuditLog).where(
            AuditLog.admin_id == admin.id,
            AuditLog.entity_type == "customer_onboarding_state",
            AuditLog.entity_id == str(state.id),
        )
    )
    assert audit is not None
    assert audit.action == "growth_onboarding_state.reset"
    assert audit.old_value["status"] == "completed"
    assert audit.new_value["status"] == "pending"
    assert audit.new_value["reason"] == "support requested onboarding retry"


async def test_admin_growth_onboarding_state_scrubs_raw_idempotency_keys(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    _mobile_user, state, _application = await _onboarding_fixture(db, admin)
    state.status = "skipped"
    state.skipped_at = datetime.now(UTC)
    state.result_payload = {
        "message_key": "onboarding.skipped",
        "idempotency_key": "skip-secret-key",
        "nested": {
            "raw_idempotency_key": "nested-secret-key",
        },
    }
    await db.flush()

    states = await list_growth_onboarding_states(
        mobile_user_id=None,
        status_filter="skipped",
        flow_key=None,
        limit=50,
        offset=0,
        _current_user=admin,
        db=db,
    )
    assert states.total == 1
    payload = states.items[0].result_payload
    assert payload["idempotency_key_present"] is True
    assert payload["idempotency_key_hash"] == hashlib.sha256(b"skip-secret-key").hexdigest()
    assert payload["nested"]["raw_idempotency_key_present"] is True
    assert payload["nested"]["raw_idempotency_key_hash"] == hashlib.sha256(b"nested-secret-key").hexdigest()
    assert "skip-secret-key" not in states.items[0].model_dump_json()
    assert "nested-secret-key" not in states.items[0].model_dump_json()

    detail = await get_growth_onboarding_state(state.id, _current_user=admin, db=db)
    assert detail.result_payload == payload
