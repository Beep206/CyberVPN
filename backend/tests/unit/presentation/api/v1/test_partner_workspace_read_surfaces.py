from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.config.settings import settings
from src.presentation.api.v1.auth import passkey_policy
from src.presentation.api.v1.partners import routes as partner_routes
from src.presentation.api.v1.support_tickets import routes as support_routes


@pytest.mark.asyncio
async def test_reseller_voucher_batch_list_returns_empty_without_workspace_capability(monkeypatch) -> None:
    async def disabled_capability(**_kwargs) -> bool:
        return False

    class RaisingGrowthCodeRepository:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("list endpoint should not query gift codes without reseller capability")

    monkeypatch.setattr(partner_routes, "_workspace_reseller_voucher_capability_enabled", disabled_capability)
    monkeypatch.setattr(partner_routes, "GrowthCodeRepository", RaisingGrowthCodeRepository)
    monkeypatch.setattr(partner_routes, "track_partner_operation", lambda **_kwargs: None)

    workspace_id = uuid.uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(
            id=workspace_id,
            status="active",
            display_name="Synthetic Workspace",
        )
    )

    response = await partner_routes.list_partner_workspace_reseller_voucher_batches(
        workspace_id,
        access=access,
        db=object(),
    )

    assert response == []


@pytest.mark.asyncio
async def test_partner_workspace_creative_approvals_get_lists_workspace_items(monkeypatch) -> None:
    workspace_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    created_at = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    fake_approval = SimpleNamespace(
        id=uuid.uuid4(),
        partner_account_id=workspace_id,
        approval_kind="creative_approval",
        approval_status="under_review",
        scope_label="Synthetic campaign",
        creative_ref="creative-001",
        approval_payload={"channel": "partner_portal"},
        notes_payload=["Synthetic approval"],
        submitted_by_admin_user_id=actor_id,
        reviewed_by_admin_user_id=None,
        reviewed_at=None,
        expires_at=None,
        created_at=created_at,
        updated_at=created_at,
    )
    calls: dict[str, object] = {}

    class FakeListCreativeApprovalsUseCase:
        def __init__(self, db) -> None:
            calls["db"] = db

        async def execute(self, **kwargs):
            calls["kwargs"] = kwargs
            return [fake_approval]

    monkeypatch.setattr(partner_routes, "ListCreativeApprovalsUseCase", FakeListCreativeApprovalsUseCase)
    monkeypatch.setattr(
        partner_routes,
        "track_partner_operation",
        lambda **kwargs: calls.update(operation=kwargs["operation"]),
    )

    db = object()
    access = SimpleNamespace(workspace=SimpleNamespace(id=workspace_id))

    response = await partner_routes.list_partner_workspace_creative_approvals(
        workspace_id,
        limit=25,
        offset=5,
        access=access,
        db=db,
    )

    assert calls["db"] is db
    assert calls["kwargs"] == {
        "partner_account_id": workspace_id,
        "approval_kind": "creative_approval",
        "limit": 25,
        "offset": 5,
    }
    assert calls["operation"] == "list_workspace_creative_approvals"
    assert response[0].id == fake_approval.id
    assert response[0].partner_account_id == workspace_id
    assert response[0].notes == ["Synthetic approval"]


@pytest.mark.asyncio
async def test_partner_support_ticket_list_returns_empty_read_only_payload(monkeypatch) -> None:
    workspace_id = uuid.uuid4()
    calls: dict[str, object] = {}

    class FakeSupportTicketService:
        async def list_partner_tickets(self, **kwargs):
            calls["kwargs"] = kwargs
            return SimpleNamespace(tickets=(), next_cursor=None)

    monkeypatch.setattr(support_routes, "_service", lambda db: FakeSupportTicketService())

    response = await support_routes.list_partner_support_tickets(
        ticket_status=None,
        category=None,
        priority=None,
        cursor=None,
        limit=50,
        workspace_access=SimpleNamespace(workspace=SimpleNamespace(id=workspace_id)),
        db=object(),
    )

    assert calls["kwargs"] == {
        "partner_workspace_id": workspace_id,
        "status": None,
        "category": None,
        "priority": None,
        "cursor": None,
        "limit": 50,
    }
    assert response.tickets == []
    assert response.next_cursor is None


@pytest.mark.asyncio
async def test_partner_passkey_context_skips_credential_storage_when_partner_passkeys_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "passkey_enabled", False)
    monkeypatch.setattr(settings, "passkey_partner_enabled", False)

    profile = SimpleNamespace(
        prefer_passkeys=False,
        require_mfa_for_workspace=False,
        updated_at=None,
    )
    membership = SimpleNamespace(
        admin_user_id=uuid.uuid4(),
        membership_status="active",
    )

    class FakeProfileRepository:
        def __init__(self, _db) -> None:
            pass

        async def get_or_create(self, _workspace_id):
            return profile

    class FakePartnerAccountRepository:
        def __init__(self, _db) -> None:
            pass

        async def list_memberships(self, _workspace_id):
            return [membership]

    class RaisingPasskeyCredentialRepository:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AssertionError("disabled partner passkeys should not query passkey credential storage")

    monkeypatch.setattr(passkey_policy, "PartnerWorkspaceProfileRepository", FakeProfileRepository)
    monkeypatch.setattr(passkey_policy, "PartnerAccountRepository", FakePartnerAccountRepository)
    monkeypatch.setattr(passkey_policy, "PasskeyCredentialRepository", RaisingPasskeyCredentialRepository)

    partner_realm = SimpleNamespace(
        id=uuid.uuid4(),
        realm_key="partner",
        realm_type="partner",
    )
    access = SimpleNamespace(workspace=SimpleNamespace(id=uuid.uuid4()))

    context = await passkey_policy._partner_workspace_passkey_context(
        db=object(),
        access=access,
        partner_realm=partner_realm,
    )
    resolved_realm, resolved_profile, memberships, credentials = context

    assert resolved_realm is partner_realm
    assert resolved_profile is profile
    assert memberships == [membership]
    assert credentials == []
