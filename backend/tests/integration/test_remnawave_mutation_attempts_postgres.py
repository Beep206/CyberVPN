from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptDecision,
    RemnawaveMutationAttemptService,
    remnawave_create_request_hash,
)
from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel, PartnerAccountModel
from src.infrastructure.database.models.partner_role_model import PartnerRoleModel
from src.infrastructure.database.models.partner_workspace_profile_model import PartnerWorkspaceProfileModel
from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.api.v1.partner_remnawave import routes as partner_routes
from src.presentation.api.v1.remnawave_operator.schemas import SetTagsResponse
from src.presentation.dependencies.partner_workspace import PartnerWorkspaceAccess
from tests.integration.test_partner_commission_contracts_migration_postgres import (
    _create_database,
    _database_url,
    _drop_database,
    _run_alembic,
)

pytestmark = [pytest.mark.integration]


@dataclass(frozen=True, slots=True)
class _PartnerMutationFixture:
    actor: AdminUserModel
    workspace: PartnerAccountModel
    membership: PartnerAccountUserModel
    write_role: PartnerRoleModel
    read_role: PartnerRoleModel
    grant: PartnerRemnawaveResourceGrantModel
    access: PartnerWorkspaceAccess


def _partner_request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "PATCH",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [(b"user-agent", b"pytest-partner-two-session")],
            "client": ("203.0.113.44", 443),
            "server": ("partner.cyber-vpn.net", 443),
        }
    )


async def _seed_partner_mutation_fixture(
    session: AsyncSession,
    *,
    suffix: str,
) -> _PartnerMutationFixture:
    actor = AdminUserModel(
        id=uuid.uuid4(),
        login=f"partner-cas-{suffix}",
        role="viewer",
        is_active=True,
        status="active",
        totp_enabled=True,
        deleted_at=None,
    )
    workspace = PartnerAccountModel(
        id=uuid.uuid4(),
        account_key=f"partner-cas-{suffix}",
        display_name=f"Partner CAS {suffix}",
        status="active",
        created_by_admin_user_id=actor.id,
    )
    write_role = PartnerRoleModel(
        id=uuid.uuid4(),
        role_key=f"cas_writer_{suffix}",
        display_name=f"CAS writer {suffix}",
        description="Two-session partner mutation writer",
        permission_keys=[
            PartnerPermission.REMNAWAVE_READ.value,
            PartnerPermission.REMNAWAVE_WRITE.value,
        ],
        is_system=False,
    )
    read_role = PartnerRoleModel(
        id=uuid.uuid4(),
        role_key=f"cas_reader_{suffix}",
        display_name=f"CAS reader {suffix}",
        description="Two-session partner mutation reader",
        permission_keys=[PartnerPermission.REMNAWAVE_READ.value],
        is_system=False,
    )
    membership = PartnerAccountUserModel(
        id=uuid.uuid4(),
        partner_account_id=workspace.id,
        admin_user_id=actor.id,
        role_id=write_role.id,
        membership_status="active",
        invited_by_admin_user_id=actor.id,
    )
    profile = PartnerWorkspaceProfileModel(
        id=uuid.uuid4(),
        partner_account_id=workspace.id,
        require_mfa_for_workspace=True,
    )
    grant = PartnerRemnawaveResourceGrantModel(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        resource_type="profile",
        resource_uuid=uuid.uuid4(),
        permission_keys=[
            PartnerPermission.REMNAWAVE_READ.value,
            PartnerPermission.REMNAWAVE_WRITE.value,
        ],
        granted_by_admin_user_id=actor.id,
        granted_at=datetime.now(UTC),
        audit_reason="two-session authorization fixture",
    )
    # These models intentionally do not declare ORM relationships for every FK,
    # so make the dependency order explicit instead of relying on flush sorting.
    session.add_all([actor, write_role, read_role])
    await session.flush()
    session.add(workspace)
    await session.flush()
    session.add_all([membership, profile, grant])
    await session.commit()
    return _PartnerMutationFixture(
        actor=actor,
        workspace=workspace,
        membership=membership,
        write_role=write_role,
        read_role=read_role,
        grant=grant,
        access=PartnerWorkspaceAccess(
            workspace=workspace,
            membership=membership,
            role=write_role,
            permission_keys=frozenset(write_role.permission_keys),
            is_internal_admin_override=False,
        ),
    )


@pytest.mark.asyncio
async def test_stale_partner_and_operator_sessions_cannot_downgrade_terminal_attempts() -> None:
    """A stale replay must refresh the marker after the winner commits.

    The replay session intentionally reads ``pending`` before the winner moves
    the same row to a terminal state.  This is the production interleaving
    that previously allowed a late reconciliation write to overwrite a
    committed completion or rejection.
    """

    database_name = f"cvpn_remnawave_attempt_cas_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        scenarios = (
            (
                "partner",
                f"partner-remnawave:profile_tags:{uuid.uuid4()}",
                "partner_remnawave_profile_tags",
            ),
            (
                "operator",
                "remnawave-operator:node-integration:create",
                "remnawave_node_integration_create",
            ),
        )
        for surface, scope, resource_type in scenarios:
            for terminal_state in ("completed", "rejected"):
                idempotency_key = f"two-session-{terminal_state}"
                request_hash = remnawave_create_request_hash({"surface": surface, "terminal_state": terminal_state})
                async with session_factory() as winner_session, session_factory() as replay_session:
                    winner = RemnawaveMutationAttemptService(
                        winner_session,
                        resource_type=resource_type,
                    )
                    replay = RemnawaveMutationAttemptService(
                        replay_session,
                        resource_type=resource_type,
                    )
                    winner_decision = await winner.begin(
                        scope=scope,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                    )
                    stale_decision = await replay.begin(
                        scope=scope,
                        idempotency_key=idempotency_key,
                        request_hash=request_hash,
                    )
                    assert winner_decision.should_mutate is True
                    assert stale_decision.should_mutate is False
                    assert stale_decision.record.status == "pending"

                    expected_payload: dict[str, str | int | bool]
                    if terminal_state == "completed":
                        expected_payload = {
                            "resource_uuid": str(uuid.uuid4()),
                        }
                        await winner.mark_completed_reference(
                            winner_decision.record,
                            reference=expected_payload,
                        )
                    else:
                        expected_payload = {"error_code": "provider_validation_rejected"}
                        await winner.stage_rejected(
                            winner_decision.record,
                            error_code="provider_validation_rejected",
                        )
                    await winner_session.commit()

                    await replay.stage_reconciliation_required(stale_decision.record)
                    await replay_session.commit()
                    assert stale_decision.record.status == terminal_state
                    assert stale_decision.record.response_payload == expected_payload

                async with session_factory() as verification_session:
                    persisted = (
                        await verification_session.execute(
                            select(ApiIdempotencyRecordModel).where(
                                ApiIdempotencyRecordModel.scope == scope,
                                ApiIdempotencyRecordModel.idempotency_key == idempotency_key,
                            )
                        )
                    ).scalar_one()
                    assert persisted.status == terminal_state
                    assert persisted.response_payload == expected_payload
    finally:
        await engine.dispose()
        await _drop_database(database_name)


@pytest.mark.asyncio
async def test_partner_post_reservation_policy_revalidation_and_grant_lock_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Role/member revocation wins before provider I/O and grant revoke cannot deadlock."""

    database_name = f"cvpn_partner_policy_cas_{uuid.uuid4().hex[:12]}"
    await _create_database(database_name)
    url = _database_url(database_name)
    await asyncio.to_thread(_run_alembic, url, "upgrade", "head")
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        for revocation_mode in ("membership_disabled", "role_downgraded"):
            async with session_factory() as mutation_session:
                fixture = await _seed_partner_mutation_fixture(
                    mutation_session,
                    suffix=f"{revocation_mode[:8]}_{uuid.uuid4().hex[:6]}",
                )
                provider = AsyncMock(spec=RemnawaveClient)
                original_begin = partner_routes._begin_partner_mutation_attempt

                async def begin_then_revoke(
                    *,
                    db: AsyncSession,
                    workspace_id: uuid.UUID,
                    resource_type: partner_routes.PartnerRemnawaveResourceType,
                    resource_uuid: uuid.UUID,
                    operation: partner_routes.PartnerRemnawaveSafeMutation,
                    idempotency_key: str,
                    payload: dict[str, object],
                    _original_begin: Callable[
                        ...,
                        Awaitable[tuple[RemnawaveMutationAttemptService, RemnawaveCreateAttemptDecision]],
                    ] = original_begin,
                    _fixture: _PartnerMutationFixture = fixture,
                    _revocation_mode: str = revocation_mode,
                ) -> tuple[RemnawaveMutationAttemptService, RemnawaveCreateAttemptDecision]:
                    service, decision = await _original_begin(
                        db=db,
                        workspace_id=workspace_id,
                        resource_type=resource_type,
                        resource_uuid=resource_uuid,
                        operation=operation,
                        idempotency_key=idempotency_key,
                        payload=payload,
                    )
                    async with session_factory() as revocation_session:
                        membership = await revocation_session.get(
                            PartnerAccountUserModel,
                            _fixture.membership.id,
                        )
                        assert membership is not None
                        if _revocation_mode == "membership_disabled":
                            membership.membership_status = "disabled"
                        else:
                            membership.role_id = _fixture.read_role.id
                        await revocation_session.commit()
                    return service, decision

                idempotency_key = f"partner-two-session-{revocation_mode}"
                request = _partner_request(
                    f"/api/v1/partner-workspaces/{fixture.workspace.id}/remnawave/"
                    f"resources/profile/{fixture.grant.resource_uuid}/tags"
                )
                with monkeypatch.context() as scoped_patch:
                    scoped_patch.setattr(
                        partner_routes,
                        "_begin_partner_mutation_attempt",
                        begin_then_revoke,
                    )
                    with pytest.raises(HTTPException) as rejected:
                        await partner_routes.update_partner_profile_tags(
                            workspace_id=fixture.workspace.id,
                            resource_uuid=fixture.grant.resource_uuid,
                            body=partner_routes.PartnerProfileTagsMutationRequest(tags=["SAFE"]),
                            request=request,
                            idempotency_key=idempotency_key,
                            access=fixture.access,
                            current_user=fixture.actor,
                            db=mutation_session,
                            client=provider,
                        )

                assert rejected.value.status_code == status.HTTP_404_NOT_FOUND
                provider.patch_validated.assert_not_awaited()

                async with session_factory() as verification_session:
                    attempt = (
                        await verification_session.execute(
                            select(ApiIdempotencyRecordModel).where(
                                ApiIdempotencyRecordModel.scope
                                == f"partner-remnawave:profile_tags:{fixture.workspace.id}",
                                ApiIdempotencyRecordModel.idempotency_key == idempotency_key,
                            )
                        )
                    ).scalar_one()
                    audit = (
                        await verification_session.execute(
                            select(AuditLog).where(
                                AuditLog.action == "partner_remnawave.profile_tags.rejected",
                                AuditLog.entity_id == str(attempt.id),
                            )
                        )
                    ).scalar_one()
                    assert attempt.status == "rejected"
                    assert attempt.response_payload == {
                        "error_code": "authorization_changed_before_provider",
                    }
                    assert audit.new_value is not None
                    assert audit.new_value["workspace_id"] == str(fixture.workspace.id)
                    assert "payload" not in audit.new_value

        async with session_factory() as mutation_session:
            fixture = await _seed_partner_mutation_fixture(
                mutation_session,
                suffix=f"grantlock_{uuid.uuid4().hex[:6]}",
            )
            provider_started = asyncio.Event()
            release_provider = asyncio.Event()
            revoke_before_flush = asyncio.Event()
            provider = AsyncMock(spec=RemnawaveClient)

            async def patch_tags(*_args: object, **_kwargs: object) -> SetTagsResponse:
                provider_started.set()
                await release_provider.wait()
                return SetTagsResponse(uuid=fixture.grant.resource_uuid, tags=["SAFE"])

            provider.patch_validated.side_effect = patch_tags
            request = _partner_request(
                f"/api/v1/partner-workspaces/{fixture.workspace.id}/remnawave/"
                f"resources/profile/{fixture.grant.resource_uuid}/tags"
            )
            mutation_task = asyncio.create_task(
                partner_routes.update_partner_profile_tags(
                    workspace_id=fixture.workspace.id,
                    resource_uuid=fixture.grant.resource_uuid,
                    body=partner_routes.PartnerProfileTagsMutationRequest(tags=["SAFE"]),
                    request=request,
                    idempotency_key="partner-grant-lock-order",
                    access=fixture.access,
                    current_user=fixture.actor,
                    db=mutation_session,
                    client=provider,
                )
            )

            async def revoke_like_admin_grant_path() -> None:
                async with session_factory() as revoke_session:
                    grant = await revoke_session.get(
                        PartnerRemnawaveResourceGrantModel,
                        fixture.grant.id,
                    )
                    actor = await revoke_session.get(AdminUserModel, fixture.actor.id)
                    assert grant is not None
                    assert actor is not None
                    grant.revoked_by_admin_user_id = actor.id
                    grant.revoked_at = datetime.now(UTC)
                    grant.audit_reason = "grant lock-order regression"
                    revoke_before_flush.set()
                    await revoke_session.flush()
                    await write_required_admin_audit_entry(
                        db=revoke_session,
                        action="partner_remnawave_resource_grant.revoked",
                        resource_type="partner_remnawave_resource_grant",
                        resource_id=grant.id,
                        actor=actor,
                        request=request,
                        details={
                            "workspace_id": grant.workspace_id,
                            "resource_type": grant.resource_type,
                            "resource_uuid": grant.resource_uuid,
                            "permission_keys": grant.permission_keys,
                            "reason": grant.audit_reason,
                        },
                    )
                    await revoke_session.commit()

            revoke_task = None
            try:
                await asyncio.wait_for(provider_started.wait(), timeout=10)
                revoke_task = asyncio.create_task(revoke_like_admin_grant_path())
                await asyncio.wait_for(revoke_before_flush.wait(), timeout=10)
                release_provider.set()
                mutation_result, _ = await asyncio.wait_for(
                    asyncio.gather(mutation_task, revoke_task),
                    timeout=10,
                )
            finally:
                release_provider.set()
                if not mutation_task.done():
                    mutation_task.cancel()
                if revoke_task is not None and not revoke_task.done():
                    revoke_task.cancel()

            assert isinstance(mutation_result, partner_routes.PartnerProfileTagsMutationResponse)
            assert mutation_result.resource_uuid == fixture.grant.resource_uuid
            assert mutation_result.tags == ["SAFE"]
            provider.patch_validated.assert_awaited_once()

            async with session_factory() as verification_session:
                persisted_grant = await verification_session.get(
                    PartnerRemnawaveResourceGrantModel,
                    fixture.grant.id,
                )
                attempt = (
                    await verification_session.execute(
                        select(ApiIdempotencyRecordModel).where(
                            ApiIdempotencyRecordModel.scope == f"partner-remnawave:profile_tags:{fixture.workspace.id}",
                            ApiIdempotencyRecordModel.idempotency_key == "partner-grant-lock-order",
                        )
                    )
                ).scalar_one()
                assert persisted_grant is not None
                assert persisted_grant.revoked_at is not None
                assert attempt.status == "completed"
    finally:
        await engine.dispose()
        await _drop_database(database_name)
