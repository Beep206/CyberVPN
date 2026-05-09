"""S1-ADM-004 privileged admin audit checks."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.domain.enums import AdminRole
from src.presentation.api.v1.admin import customer_support, invites
from src.presentation.api.v1.admin.audit import (
    STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS,
    build_admin_audit_details,
)
from src.presentation.api.v1.admin.customer_support_schemas import AdminCreateCustomerStaffNoteRequest


class RecordingDB:
    def __init__(self, *, fail_flush: bool = False) -> None:
        self.fail_flush = fail_flush
        self.added: list[object] = []

    def add(self, model) -> None:
        self.added.append(model)

    async def flush(self) -> None:
        if self.fail_flush:
            raise RuntimeError("audit flush failed")


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.10"),
        headers={"user-agent": "pytest-agent"},
    )


def _admin(role: AdminRole = AdminRole.ADMIN):
    return SimpleNamespace(
        id=uuid4(),
        role=role.value,
        login="admin-auditor",
        email="admin@example.test",
        display_name="Admin Auditor",
    )


def test_stage1_required_admin_audit_manifest_covers_sensitive_actions() -> None:
    expected_actions = {
        "admin_invite_created",
        "admin_invite_revoked",
        "customer_profile_updated",
        "customer_staff_note_created",
        "customer_vpn_enabled",
        "customer_vpn_disabled",
        "customer_vpn_credentials_regenerated",
        "customer_device_revoked",
        "customer_devices_revoked_all",
        "customer_password_reset",
        "customer_subscription_manual_granted",
        "customer_subscription_resynced",
        "customer_operations.verify_payout_account",
        "customer_operations.suspend_payout_account",
        "customer_operations.approve_payout_instruction",
        "customer_operations.reject_payout_instruction",
        "system_config.miniapp_runtime.updated",
        "system_config.miniapp_launch_readiness.updated",
        "system_config.miniapp_launch_action.executed",
        "admin.bootstrap.first_admin_created",
    }

    assert expected_actions <= STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS


def test_stage1_admin_audit_details_redact_sensitive_values() -> None:
    details = build_admin_audit_details(
        {
            "email_hint": "alice@example.com",
            "subscription_url": "https://sub.example.test/secret-token",
            "new_password": "TempPassword123!",
            "nested": {
                "config_link": "vless://secret@example.test",
                "reason_length": 12,
            },
            "changed_fields": ["email", "status"],
        }
    )

    serialized = str(details).lower()
    assert details is not None
    assert details["email_hint"] == "al***@example.com"
    assert details["subscription_url"] == "[REDACTED]"
    assert details["new_password"] == "[REDACTED]"
    assert details["nested"]["config_link"] == "[REDACTED]"
    assert details["nested"]["reason_length"] == 12
    assert "secret-token" not in serialized
    assert "vless://" not in serialized
    assert "temppassword" not in serialized


@pytest.mark.asyncio
async def test_stage1_customer_support_audit_is_required_and_sanitized() -> None:
    db = RecordingDB()
    user_id = uuid4()
    admin = _admin(AdminRole.SUPPORT)

    await customer_support._write_audit_entry(
        db=db,
        action="customer_subscription_resynced",
        user_id=user_id,
        actor=admin,
        request=_request(),
        details={
            "previous_subscription_url": "https://sub.example.test/old-secret-token",
            "stored_subscription_url": "https://sub.example.test/new-secret-token",
            "changed": True,
            "reason_length": 28,
        },
    )

    audit_entry = db.added[0]
    assert audit_entry.action == "customer_subscription_resynced"
    assert audit_entry.admin_id == admin.id
    assert audit_entry.entity_type == "mobile_user"
    assert audit_entry.entity_id == str(user_id)
    assert audit_entry.ip_address == "203.0.113.10"
    assert audit_entry.user_agent == "pytest-agent"
    assert audit_entry.new_value["previous_subscription_url"] == "[REDACTED]"
    assert audit_entry.new_value["stored_subscription_url"] == "[REDACTED]"
    assert audit_entry.new_value["changed"] is True


@pytest.mark.asyncio
async def test_stage1_customer_support_action_fails_if_required_audit_fails() -> None:
    with pytest.raises(RuntimeError, match="audit flush failed"):
        await customer_support._write_audit_entry(
            db=RecordingDB(fail_flush=True),
            action="customer_password_reset",
            user_id=uuid4(),
            actor=_admin(AdminRole.SUPPORT),
            request=_request(),
            details={"password_mode": "generated", "reason_length": 14},
        )


@pytest.mark.asyncio
async def test_stage1_create_staff_note_writes_required_audit(monkeypatch) -> None:
    db = RecordingDB()
    user_id = uuid4()
    admin = _admin(AdminRole.SUPPORT)
    now = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)

    async def fake_require_mobile_user(received_user_id, received_db):
        assert received_user_id == user_id
        assert received_db is db
        return SimpleNamespace(id=user_id)

    class FakeCustomerStaffNoteRepository:
        def __init__(self, received_db) -> None:
            assert received_db is db

        async def create(self, model):
            model.id = uuid4()
            model.created_at = now
            model.updated_at = now
            return model

    monkeypatch.setattr(customer_support, "_require_mobile_user", fake_require_mobile_user)
    monkeypatch.setattr(customer_support, "CustomerStaffNoteRepository", FakeCustomerStaffNoteRepository)

    response = await customer_support.create_customer_staff_note(
        user_id=user_id,
        body=AdminCreateCustomerStaffNoteRequest(category="support", note="User reports connection issue"),
        request=_request(),
        current_user=admin,
        db=db,
    )

    assert response.user_id == user_id
    audit_entry = db.added[0]
    assert audit_entry.action == "customer_staff_note_created"
    assert audit_entry.entity_id == str(user_id)
    assert audit_entry.new_value["category"] == "support"
    assert audit_entry.new_value["note_length"] == len("User reports connection issue")


@pytest.mark.asyncio
async def test_stage1_invite_create_writes_audit_without_raw_token(monkeypatch) -> None:
    db = RecordingDB()
    admin = _admin(AdminRole.ADMIN)
    raw_token = "11111111-2222-4333-8444-555555555555"

    class FakeInviteTokenService:
        def __init__(self, redis_client) -> None:
            self.redis_client = redis_client

        async def generate(self, *, created_by, role, email_hint):
            assert created_by == str(admin.id)
            assert role == AdminRole.SUPPORT.value
            assert str(email_hint) == "alice@example.com"
            return raw_token

    monkeypatch.setattr(invites, "InviteTokenService", FakeInviteTokenService)

    response = await invites.create_invite(
        request=invites.CreateInviteRequest(role=AdminRole.SUPPORT, email_hint="alice@example.com"),
        http_request=_request(),
        redis_client=object(),
        db=db,
        current_user=admin,
    )

    assert response.token == raw_token
    audit_entry = db.added[0]
    assert audit_entry.action == "admin_invite_created"
    assert audit_entry.entity_type == "admin_invite"
    assert audit_entry.entity_id != raw_token
    serialized_audit = f"{audit_entry.entity_id} {audit_entry.new_value}"
    assert raw_token not in serialized_audit
    assert audit_entry.new_value["email_hint"] == "al***@example.com"
    assert audit_entry.new_value["invite_fingerprint"] == audit_entry.entity_id


@pytest.mark.asyncio
async def test_stage1_invite_revoke_writes_audit_without_raw_token(monkeypatch) -> None:
    db = RecordingDB()
    admin = _admin(AdminRole.ADMIN)
    raw_token = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"

    class FakeInviteTokenService:
        def __init__(self, redis_client) -> None:
            self.redis_client = redis_client

        async def revoke(self, token):
            assert token == raw_token
            return True

    monkeypatch.setattr(invites, "InviteTokenService", FakeInviteTokenService)

    await invites.revoke_invite(
        token=raw_token,
        request=_request(),
        redis_client=object(),
        db=db,
        current_user=admin,
    )

    audit_entry = db.added[0]
    assert audit_entry.action == "admin_invite_revoked"
    assert audit_entry.entity_id != raw_token
    serialized_audit = f"{audit_entry.entity_id} {audit_entry.new_value}"
    assert raw_token not in serialized_audit
    assert audit_entry.new_value["invite_fingerprint"] == audit_entry.entity_id
    assert audit_entry.new_value["revoked"] is True
