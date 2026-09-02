from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.domain.entities.partner_permission import PartnerPermission
from src.domain.entities.partner_role import BUILTIN_PARTNER_ROLE_DEFINITIONS
from src.presentation.dependencies.partner_workspace import enforce_partner_remnawave_resource_grant


@pytest.mark.unit
def test_no_builtin_partner_role_auto_grants_remnawave_capabilities() -> None:
    privileged = {
        PartnerPermission.REMNAWAVE_READ,
        PartnerPermission.REMNAWAVE_WRITE,
        PartnerPermission.REMNAWAVE_EXECUTE,
        PartnerPermission.REMNAWAVE_SSH,
    }

    for role in BUILTIN_PARTNER_ROLE_DEFINITIONS:
        assert privileged.isdisjoint(role.permissions), role.role_key


@pytest.mark.unit
def test_owner_role_does_not_track_permission_enum_expansion() -> None:
    owner = next(role for role in BUILTIN_PARTNER_ROLE_DEFINITIONS if role.role_key == "owner")

    assert tuple(owner.permissions) != tuple(PartnerPermission)


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = [] if value is None else [value]
    return result


@pytest.mark.asyncio
async def test_object_grant_is_required_for_partner_remnawave_resource() -> None:
    workspace_id = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({PartnerPermission.REMNAWAVE_READ.value}),
        is_internal_admin_override=False,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(None))

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=uuid4(),
            permission=PartnerPermission.REMNAWAVE_READ,
            db=db,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.parametrize(
    "permission",
    [
        PartnerPermission.REMNAWAVE_READ,
        PartnerPermission.REMNAWAVE_WRITE,
        PartnerPermission.REMNAWAVE_EXECUTE,
    ],
)
@pytest.mark.asyncio
async def test_object_grant_cannot_bypass_missing_role_permission(permission: PartnerPermission) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset(),
        is_internal_admin_override=False,
    )
    grant = SimpleNamespace(
        workspace_id=workspace_id,
        resource_type="node",
        resource_uuid=resource_uuid,
        permission_keys=[permission.value],
        revoked_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(grant))

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=resource_uuid,
            permission=permission,
            db=db,
        )

    assert exc_info.value.status_code == 404
    assert db.execute.await_count == 0


@pytest.mark.parametrize(
    "permission",
    [
        PartnerPermission.REMNAWAVE_READ,
        PartnerPermission.REMNAWAVE_WRITE,
        PartnerPermission.REMNAWAVE_EXECUTE,
    ],
)
@pytest.mark.asyncio
async def test_role_permission_cannot_bypass_missing_object_permission(permission: PartnerPermission) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({permission.value}),
        is_internal_admin_override=False,
    )
    wrong_permission = (
        PartnerPermission.REMNAWAVE_WRITE
        if permission is PartnerPermission.REMNAWAVE_READ
        else PartnerPermission.REMNAWAVE_READ
    )
    grant = SimpleNamespace(
        workspace_id=workspace_id,
        resource_type="node",
        resource_uuid=resource_uuid,
        permission_keys=[wrong_permission.value],
        revoked_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(grant))

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=resource_uuid,
            permission=permission,
            db=db,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.parametrize(
    "permission",
    [
        PartnerPermission.REMNAWAVE_READ,
        PartnerPermission.REMNAWAVE_WRITE,
        PartnerPermission.REMNAWAVE_EXECUTE,
    ],
)
@pytest.mark.asyncio
async def test_matching_role_and_object_grant_allows_resource(permission: PartnerPermission) -> None:
    workspace_id = uuid4()
    resource_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({permission.value}),
        is_internal_admin_override=False,
    )
    grant = SimpleNamespace(
        workspace_id=workspace_id,
        resource_type="node",
        resource_uuid=resource_uuid,
        permission_keys=[permission.value],
        revoked_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(grant))

    result = await enforce_partner_remnawave_resource_grant(
        access=access,
        resource_type="node",
        resource_uuid=resource_uuid,
        permission=permission,
        db=db,
    )

    assert result is grant


@pytest.mark.asyncio
async def test_partner_browser_ssh_is_always_rejected() -> None:
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=uuid4(), status="active"),
        permission_keys=frozenset({PartnerPermission.REMNAWAVE_SSH.value}),
        is_internal_admin_override=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=uuid4(),
            permission=PartnerPermission.REMNAWAVE_SSH,
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_grant_for_one_object_cannot_authorize_another_object() -> None:
    workspace_id = uuid4()
    granted_resource_uuid = uuid4()
    requested_resource_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({PartnerPermission.REMNAWAVE_READ.value}),
        is_internal_admin_override=False,
    )
    wrong_object_grant = SimpleNamespace(
        workspace_id=workspace_id,
        resource_type="node",
        resource_uuid=granted_resource_uuid,
        permission_keys=[PartnerPermission.REMNAWAVE_READ.value],
        revoked_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_result(wrong_object_grant))

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=requested_resource_uuid,
            permission=PartnerPermission.REMNAWAVE_READ,
            db=db,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_cross_workspace_duplicate_node_grants_fail_closed() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    resource_uuid = uuid4()
    access = SimpleNamespace(
        workspace=SimpleNamespace(id=workspace_id, status="active"),
        permission_keys=frozenset({PartnerPermission.REMNAWAVE_READ.value}),
        is_internal_admin_override=False,
    )
    grants = [
        SimpleNamespace(
            workspace_id=workspace_id,
            resource_type="node",
            resource_uuid=resource_uuid,
            permission_keys=[PartnerPermission.REMNAWAVE_READ.value],
            revoked_at=None,
        ),
        SimpleNamespace(
            workspace_id=other_workspace_id,
            resource_type="node",
            resource_uuid=resource_uuid,
            permission_keys=[PartnerPermission.REMNAWAVE_READ.value],
            revoked_at=None,
        ),
    ]
    result = MagicMock()
    result.scalars.return_value.all.return_value = grants
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc_info:
        await enforce_partner_remnawave_resource_grant(
            access=access,
            resource_type="node",
            resource_uuid=resource_uuid,
            permission=PartnerPermission.REMNAWAVE_READ,
            db=db,
        )

    assert exc_info.value.status_code == 404
