from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import ValidationError

from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.remnawave.client import RemnawaveTransportError
from src.presentation.api.v1.partner_remnawave import routes
from src.presentation.api.v1.remnawave_operator.schemas import NodeIntegration, SetTagsResponse
from src.presentation.dependencies import get_remnawave_client
from src.presentation.dependencies.auth import get_current_active_web_user
from src.presentation.dependencies.database import get_db


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "PATCH",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 443),
        }
    )


def _access(workspace_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset(
            {
                PartnerPermission.REMNAWAVE_READ.value,
                PartnerPermission.REMNAWAVE_WRITE.value,
            }
        ),
        is_internal_admin_override=False,
    )


def _record(*, state: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), status=state, response_payload={})


def _missing_scalar_result() -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _collection_result(values: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def test_partner_mutation_requests_reject_provider_config_and_restart_controls() -> None:
    with pytest.raises(ValidationError):
        routes.PartnerIntegrationMetadataMutationRequest.model_validate(
            {"name": "safe-name", "config": {"token": "forbidden"}}
        )
    with pytest.raises(ValidationError):
        routes.PartnerIntegrationMetadataMutationRequest.model_validate({"description": "safe", "restartNodes": True})
    with pytest.raises(ValidationError):
        routes.PartnerIntegrationMetadataMutationRequest.model_validate({"name": None})


def test_profile_tags_are_bounded_unique_uppercase_values() -> None:
    with pytest.raises(ValidationError):
        routes.PartnerProfileTagsMutationRequest(tags=["DUPLICATE", "DUPLICATE"])
    with pytest.raises(ValidationError):
        routes.PartnerProfileTagsMutationRequest(tags=["lowercase"])


def test_only_write_granted_profile_and_integration_advertise_safe_mutations() -> None:
    workspace_id = uuid4()
    access = _access(workspace_id)

    def grant(resource_type: str, permissions: list[str]) -> SimpleNamespace:
        return SimpleNamespace(
            workspace_id=workspace_id,
            resource_type=resource_type,
            resource_uuid=uuid4(),
            permission_keys=permissions,
            revoked_at=None,
        )

    profile = routes._serialize_resource(
        access=access,
        grant=grant("profile", ["remnawave_read", "remnawave_write"]),
    )
    integration = routes._serialize_resource(
        access=access,
        grant=grant("integration", ["remnawave_read", "remnawave_write"]),
    )
    node = routes._serialize_resource(
        access=access,
        grant=grant("node", ["remnawave_read", "remnawave_write"]),
    )

    assert profile.safe_mutations == [routes.PartnerRemnawaveSafeMutation.PROFILE_TAGS]
    assert integration.safe_mutations == [routes.PartnerRemnawaveSafeMutation.INTEGRATION_METADATA]
    assert node.safe_mutations == []
    assert routes.PartnerRemnawaveOperation.MUTATE_RESOURCE in profile.available_operations
    assert routes.PartnerRemnawaveOperation.MUTATE_RESOURCE in node.unavailable_operations

    enabled = routes._control_capabilities(
        access=access,
        grants=[grant("profile", ["remnawave_read", "remnawave_write"])],
    )
    disabled = routes._control_capabilities(
        access=access,
        grants=[
            grant("profile", ["remnawave_read"]),
            grant("node", ["remnawave_read", "remnawave_write"]),
        ],
    )
    assert enabled.mutate_resource is True
    assert enabled.safe_mutations == [routes.PartnerRemnawaveSafeMutation.PROFILE_TAGS]
    assert disabled.mutate_resource is False
    assert disabled.safe_mutations == []
    assert disabled.mutation_unavailable_reason == "no_current_write_granted_safe_mutation"


@pytest.mark.unit
async def test_direct_mutation_urls_hide_foreign_workspace_and_missing_object_grant() -> None:
    own_workspace_id = uuid4()
    foreign_workspace_id = uuid4()
    resource_uuid = uuid4()
    db = AsyncMock()
    db.execute.return_value = _missing_scalar_result()
    provider = AsyncMock()
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def access_override(workspace_id: UUID):
        if workspace_id != own_workspace_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave workspace not found")
        return _access(own_workspace_id)

    async def user_override():
        return SimpleNamespace(id=uuid4(), totp_enabled=True)

    async def db_override():
        yield db

    app.dependency_overrides[routes.get_partner_remnawave_workspace_access] = access_override
    app.dependency_overrides[get_current_active_web_user] = user_override
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_remnawave_client] = lambda: provider

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://partner.cyber-vpn.net",
    ) as client:
        foreign = await client.patch(
            f"/api/v1/partner-workspaces/{foreign_workspace_id}/remnawave/resources/profile/{resource_uuid}/tags",
            headers={"Idempotency-Key": "partner-profile-tags-foreign"},
            json={"tags": ["PARTNER_SAFE"]},
        )
        missing = await client.patch(
            f"/api/v1/partner-workspaces/{own_workspace_id}/remnawave/resources/profile/{resource_uuid}/tags",
            headers={"Idempotency-Key": "partner-profile-tags-missing"},
            json={"tags": ["PARTNER_SAFE"]},
        )

    assert foreign.status_code == status.HTTP_404_NOT_FOUND
    assert missing.status_code == status.HTTP_404_NOT_FOUND
    assert missing.json()["detail"] == "Remnawave resource not found"
    provider.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_authorization_requires_role_and_exact_object_write_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    access = _access(workspace_id)
    current_user = SimpleNamespace(id=uuid4(), totp_enabled=True)
    db = AsyncMock()
    grant_query = MagicMock()
    grant_query.scalars.return_value.all.return_value = [workspace_id]
    db.execute.return_value = grant_query
    workspace_check = AsyncMock()
    object_check = AsyncMock(return_value=SimpleNamespace(resource_uuid=resource_uuid))
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", workspace_check)
    monkeypatch.setattr(routes, "enforce_partner_remnawave_resource_grant", object_check)

    await routes._authorize_partner_mutation(
        access=access,
        current_user=current_user,
        db=db,
        resource_type=routes.PartnerRemnawaveResourceType.PROFILE,
        resource_uuid=resource_uuid,
    )

    assert workspace_check.await_args.kwargs["permission"] is PartnerPermission.REMNAWAVE_WRITE
    assert object_check.await_args.kwargs == {
        "access": access,
        "resource_type": "profile",
        "resource_uuid": resource_uuid,
        "permission": PartnerPermission.REMNAWAVE_WRITE,
        "db": db,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reserved_mutation_locks_current_policy_and_exact_grant_through_audit_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    actor_id = uuid4()
    role_id = uuid4()
    access = _access(workspace_id)
    workspace = SimpleNamespace(id=workspace_id, status="active")
    access.workspace = workspace
    membership = SimpleNamespace(
        partner_account_id=workspace_id,
        admin_user_id=actor_id,
        role_id=role_id,
        membership_status="active",
    )
    role = SimpleNamespace(
        id=role_id,
        permission_keys=["remnawave_read", "remnawave_write"],
    )
    profile = SimpleNamespace(require_mfa_for_workspace=True)
    grant = SimpleNamespace(
        workspace_id=workspace_id,
        resource_type="profile",
        resource_uuid=resource_uuid,
        permission_keys=["remnawave_read", "remnawave_write"],
        revoked_at=None,
    )
    actor = SimpleNamespace(
        id=actor_id,
        is_active=True,
        deleted_at=None,
        status="active",
        totp_enabled=True,
    )
    db = AsyncMock()
    db.execute.side_effect = [
        _scalar_result(workspace),
        _scalar_result(membership),
        _scalar_result(role),
        _scalar_result(profile),
        _collection_result([grant]),
        _scalar_result(actor),
    ]
    writer = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)
    record = _record()

    await routes._lock_reserved_partner_mutation_ownership(
        db=db,
        request=_request("/profile/tags"),
        actor=actor,
        access=access,
        workspace_id=workspace_id,
        resource_type=routes.PartnerRemnawaveResourceType.PROFILE,
        resource_uuid=resource_uuid,
        operation=routes.PartnerRemnawaveSafeMutation.PROFILE_TAGS,
        service=AsyncMock(),
        decision=routes.RemnawaveCreateAttemptDecision(record=record, should_mutate=True),
    )

    statements = [call.args[0] for call in db.execute.await_args_list]
    entities = [statement.column_descriptions[0]["entity"] for statement in statements]
    assert entities == [
        routes.PartnerAccountModel,
        routes.PartnerAccountUserModel,
        routes.PartnerRoleModel,
        routes.PartnerWorkspaceProfileModel,
        routes.PartnerRemnawaveResourceGrantModel,
        routes.AdminUserModel,
    ]
    assert all("FOR UPDATE" in str(statement) for statement in statements)
    writer.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ownership_change_after_reservation_rejects_and_audits_before_provider_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    service = AsyncMock()

    async def stage(item, *, error_code: str) -> None:
        item.status = "rejected"
        item.response_payload = {"error_code": error_code}

    service.stage_rejected.side_effect = stage
    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute.return_value = query_result
    writer = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)

    with pytest.raises(HTTPException) as caught:
        await routes._lock_reserved_partner_mutation_ownership(
            db=db,
            request=_request("/profile/tags"),
            actor=SimpleNamespace(id=uuid4()),
            access=_access(workspace_id),
            workspace_id=workspace_id,
            resource_type=routes.PartnerRemnawaveResourceType.PROFILE,
            resource_uuid=resource_uuid,
            operation=routes.PartnerRemnawaveSafeMutation.PROFILE_TAGS,
            service=service,
            decision=routes.RemnawaveCreateAttemptDecision(record=record, should_mutate=True),
        )

    assert caught.value.status_code == status.HTTP_404_NOT_FOUND
    assert record.status == "rejected"
    service.stage_rejected.assert_awaited_once_with(
        record,
        error_code="authorization_changed_before_provider",
    )
    writer.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_partner_replay_reports_committed_completion_without_downgrade_or_duplicate_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    service = AsyncMock()

    async def refresh_terminal(item) -> None:
        item.status = "completed"
        item.response_payload = {"resource_uuid": str(resource_uuid)}

    service.stage_reconciliation_required.side_effect = refresh_terminal
    writer = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)
    db = AsyncMock()

    response = await routes._mark_partner_reconciliation_required(
        db=db,
        request=_request("/profile/tags"),
        actor=SimpleNamespace(id=uuid4()),
        workspace_id=workspace_id,
        resource_type=routes.PartnerRemnawaveResourceType.PROFILE,
        resource_uuid=resource_uuid,
        operation=routes.PartnerRemnawaveSafeMutation.PROFILE_TAGS,
        service=service,
        record=record,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.body is not None
    assert b'"state":"accepted"' in response.body
    assert record.status == "completed"
    writer.assert_not_awaited()
    db.commit.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_partner_mutation_rejects_cross_workspace_shared_global_resource_before_reservation_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    foreign_workspace_id = uuid4()
    resource_uuid = uuid4()
    db = AsyncMock()
    grant_query = MagicMock()
    grant_query.scalars.return_value.all.return_value = [workspace_id, foreign_workspace_id]
    db.execute.return_value = grant_query
    monkeypatch.setattr(routes, "enforce_partner_workspace_permission", AsyncMock())
    monkeypatch.setattr(
        routes,
        "enforce_partner_remnawave_resource_grant",
        AsyncMock(return_value=SimpleNamespace(workspace_id=workspace_id, resource_uuid=resource_uuid)),
    )
    begin = AsyncMock()
    provider = AsyncMock()
    monkeypatch.setattr(routes, "_begin_partner_mutation_attempt", begin)

    with pytest.raises(HTTPException) as caught:
        await routes.update_partner_profile_tags(
            workspace_id=workspace_id,
            resource_uuid=resource_uuid,
            body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
            request=_request("/profile/tags"),
            idempotency_key="partner-profile-shared-global",
            access=_access(workspace_id),
            current_user=SimpleNamespace(id=uuid4()),
            db=db,
            client=provider,
        )

    assert caught.value.status_code == status.HTTP_404_NOT_FOUND
    begin.assert_not_awaited()
    provider.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_profile_tag_update_reserves_before_provider_and_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    events: list[str] = []
    service = AsyncMock()
    authorize = AsyncMock(side_effect=lambda **_kwargs: events.append("authorized"))

    async def begin(**_kwargs):
        events.append("reserved")
        return service, SimpleNamespace(record=record, should_mutate=True)

    async def complete(**_kwargs):
        events.append("completed")

    client = AsyncMock()

    async def patch(*_args, **_kwargs):
        events.append("provider")
        return SetTagsResponse(uuid=resource_uuid, tags=["PARTNER_SAFE"])

    client.patch_validated.side_effect = patch
    monkeypatch.setattr(routes, "_authorize_partner_mutation", authorize)
    monkeypatch.setattr(routes, "_begin_partner_mutation_attempt", begin)
    monkeypatch.setattr(
        routes,
        "_lock_reserved_partner_mutation_ownership",
        AsyncMock(side_effect=lambda **_kwargs: events.append("locked")),
    )
    monkeypatch.setattr(routes, "_complete_partner_mutation", complete)

    result = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-tags-0001",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
        client=client,
    )

    assert events == ["authorized", "reserved", "locked", "provider", "completed"]
    assert result == routes.PartnerProfileTagsMutationResponse(
        resource_uuid=resource_uuid,
        tags=["PARTNER_SAFE"],
    )


@pytest.mark.unit
async def test_profile_tag_transport_ambiguity_latches_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    client = AsyncMock()
    client.patch_validated.side_effect = RemnawaveTransportError()
    mark = AsyncMock(
        return_value=routes._partner_receipt_response(
            routes._partner_mutation_receipt(
                record,
                state="reconciliation_required",
                resource_type=routes.PartnerRemnawaveResourceType.PROFILE,
                resource_uuid=resource_uuid,
            )
        )
    )
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(
        routes,
        "_begin_partner_mutation_attempt",
        AsyncMock(return_value=(AsyncMock(), SimpleNamespace(record=record, should_mutate=True))),
    )
    monkeypatch.setattr(routes, "_mark_partner_reconciliation_required", mark)

    result = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-tags-0002",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
        client=client,
    )

    assert result.status_code == status.HTTP_202_ACCEPTED
    client.patch_validated.assert_awaited_once()
    mark.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_profile_success_body_is_durably_reconciled_and_replay_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    service = AsyncMock()

    async def stage(item) -> None:
        item.status = "reconciliation_required"

    service.stage_reconciliation_required.side_effect = stage
    begin = AsyncMock(return_value=(service, SimpleNamespace(record=record, should_mutate=True)))
    client = AsyncMock()
    client.patch_validated.side_effect = HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Upstream service returned invalid response",
    )
    writer = AsyncMock()
    db = AsyncMock()
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(routes, "_begin_partner_mutation_attempt", begin)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)

    first = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-invalid-body",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
        client=client,
    )
    begin.return_value = (service, SimpleNamespace(record=record, should_mutate=False))
    second = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-invalid-body",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
        client=client,
    )

    assert first.status_code == second.status_code == status.HTTP_202_ACCEPTED
    assert record.status == "reconciliation_required"
    service.stage_reconciliation_required.assert_awaited_once_with(record)
    client.patch_validated.assert_awaited_once()
    writer.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_partner_audit_failure_does_not_commit_completion_and_pending_replay_never_repeats_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    service = AsyncMock()

    async def complete(item, *, reference) -> None:
        item.status = "completed"
        item.response_payload = dict(reference)

    async def stage(item) -> None:
        item.status = "reconciliation_required"
        item.response_payload = {}

    service.mark_completed_reference.side_effect = complete
    service.stage_reconciliation_required.side_effect = stage
    begin = AsyncMock(return_value=(service, SimpleNamespace(record=record, should_mutate=True)))
    client = AsyncMock()
    client.patch_validated.return_value = SetTagsResponse(uuid=resource_uuid, tags=["PARTNER_SAFE"])
    writer = AsyncMock(side_effect=[RuntimeError("audit unavailable"), None])
    db = AsyncMock()
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(routes, "_begin_partner_mutation_attempt", begin)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await routes.update_partner_profile_tags(
            workspace_id=workspace_id,
            resource_uuid=resource_uuid,
            body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
            request=_request("/profile/tags"),
            idempotency_key="partner-profile-audit-atomic",
            access=_access(workspace_id),
            current_user=SimpleNamespace(id=uuid4()),
            db=db,
            client=client,
        )

    db.commit.assert_not_awaited()
    record.status = "pending"
    record.response_payload = {}
    begin.return_value = (service, SimpleNamespace(record=record, should_mutate=False))
    replay = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-audit-atomic",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
        client=client,
    )

    assert replay.status_code == status.HTTP_202_ACCEPTED
    client.patch_validated.assert_awaited_once()
    assert record.status == "reconciliation_required"
    assert db.commit.await_count == 1
    assert writer.await_count == 2


@pytest.mark.unit
async def test_replayed_profile_attempt_never_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    client = AsyncMock()
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(
        routes,
        "_begin_partner_mutation_attempt",
        AsyncMock(
            return_value=(
                AsyncMock(),
                SimpleNamespace(record=_record(state="reconciliation_required"), should_mutate=False),
            )
        ),
    )

    result = await routes.update_partner_profile_tags(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerProfileTagsMutationRequest(tags=["PARTNER_SAFE"]),
        request=_request("/profile/tags"),
        idempotency_key="partner-profile-tags-0003",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
        client=client,
    )

    assert result.status_code == status.HTTP_202_ACCEPTED
    client.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_integration_metadata_response_never_exposes_provider_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    client = AsyncMock()
    client.patch_validated.return_value = NodeIntegration(
        uuid=resource_uuid,
        name="safe-name",
        description="allowlisted",
        config={"token": "must-not-leak", "endpoint": "https://private.invalid"},
    )
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(
        routes,
        "_begin_partner_mutation_attempt",
        AsyncMock(
            return_value=(
                AsyncMock(),
                SimpleNamespace(record=_record(), should_mutate=True),
            )
        ),
    )
    monkeypatch.setattr(routes, "_complete_partner_mutation", AsyncMock())

    result = await routes.update_partner_integration_metadata(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerIntegrationMetadataMutationRequest(description="allowlisted"),
        request=_request("/integration/metadata"),
        idempotency_key="partner-integration-meta-0001",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
        client=client,
    )

    serialized = result.model_dump_json()
    assert "allowlisted" in serialized
    assert "config" not in serialized
    assert "must-not-leak" not in serialized
    assert "private.invalid" not in serialized


@pytest.mark.unit
async def test_integration_ambiguous_response_settles_from_exact_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    client = AsyncMock()
    client.patch_validated.side_effect = RemnawaveTransportError()
    readback = NodeIntegration(
        uuid=resource_uuid,
        name="safe-name",
        description="settled",
        config={"secret": "never returned"},
    )
    client.get_validated.return_value = readback
    complete = AsyncMock()
    mark = AsyncMock()
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(
        routes,
        "_begin_partner_mutation_attempt",
        AsyncMock(return_value=(AsyncMock(), SimpleNamespace(record=record, should_mutate=True))),
    )
    monkeypatch.setattr(routes, "_complete_partner_mutation", complete)
    monkeypatch.setattr(routes, "_mark_partner_reconciliation_required", mark)

    result = await routes.update_partner_integration_metadata(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerIntegrationMetadataMutationRequest(description="settled"),
        request=_request("/integration/metadata"),
        idempotency_key="partner-integration-meta-0002",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=AsyncMock(),
        client=client,
    )

    assert result.description == "settled"
    client.patch_validated.assert_awaited_once()
    client.get_validated.assert_awaited_once_with(f"/node-integrations/{resource_uuid}", NodeIntegration)
    complete.assert_awaited_once()
    mark.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_integration_success_body_is_latched_and_replay_never_repeats_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record()
    service = AsyncMock()

    async def stage(item) -> None:
        item.status = "reconciliation_required"

    service.stage_reconciliation_required.side_effect = stage
    begin = AsyncMock(return_value=(service, SimpleNamespace(record=record, should_mutate=True)))
    invalid_upstream = HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Upstream service returned invalid response format",
    )
    client = AsyncMock()
    client.patch_validated.side_effect = invalid_upstream
    client.get_validated.side_effect = invalid_upstream
    writer = AsyncMock()
    db = AsyncMock()
    monkeypatch.setattr(routes, "_authorize_partner_mutation", AsyncMock())
    monkeypatch.setattr(routes, "_lock_reserved_partner_mutation_ownership", AsyncMock())
    monkeypatch.setattr(routes, "_begin_partner_mutation_attempt", begin)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)

    first = await routes.update_partner_integration_metadata(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerIntegrationMetadataMutationRequest(description="safe"),
        request=_request("/integration/metadata"),
        idempotency_key="partner-integration-invalid-body",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
        client=client,
    )
    begin.return_value = (service, SimpleNamespace(record=record, should_mutate=False))
    second = await routes.update_partner_integration_metadata(
        workspace_id=workspace_id,
        resource_uuid=resource_uuid,
        body=routes.PartnerIntegrationMetadataMutationRequest(description="safe"),
        request=_request("/integration/metadata"),
        idempotency_key="partner-integration-invalid-body",
        access=_access(workspace_id),
        current_user=SimpleNamespace(id=uuid4()),
        db=db,
        client=client,
    )

    assert first.status_code == second.status_code == status.HTTP_202_ACCEPTED
    assert record.status == "reconciliation_required"
    client.patch_validated.assert_awaited_once()
    assert client.get_validated.await_count == 2
    writer.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.unit
async def test_partner_audit_contains_scope_but_no_mutation_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    record = _record(state="completed")
    writer = AsyncMock()
    db = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", writer)

    await routes._audit_partner_mutation(
        db=db,
        request=_request("/integration/metadata"),
        actor=SimpleNamespace(id=uuid4()),
        workspace_id=workspace_id,
        resource_type=routes.PartnerRemnawaveResourceType.INTEGRATION,
        resource_uuid=resource_uuid,
        operation=routes.PartnerRemnawaveSafeMutation.INTEGRATION_METADATA,
        record=record,
        state="completed",
    )

    details = writer.await_args.kwargs["details"]
    assert details["workspace_id"] == str(workspace_id)
    assert details["resource_uuid"] == str(resource_uuid)
    assert "payload" not in details
    assert "config" not in details
    assert "description" not in details
    await db.commit()
