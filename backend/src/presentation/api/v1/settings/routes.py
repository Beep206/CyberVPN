from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import (
    CreateSettingRequest,
    RemnawaveSettingsResponse,
    UpdateRemnawaveSettingsRequest,
    UpdateSettingRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTINGS_UNSUPPORTED_DETAIL = {"code": "remnawave_settings_legacy_operation_not_supported"}


def _raise_legacy_settings_operation_unsupported() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=_SETTINGS_UNSUPPORTED_DETAIL,
    )


@router.get("/", response_model=RemnawaveSettingsResponse)
async def get_settings(
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> RemnawaveSettingsResponse:
    """Get the singleton Remnawave settings document (admin only)."""
    result = await client.get_validated("/remnawave-settings", RemnawaveSettingsResponse)
    route_operations_total.labels(route="settings", action="get", status="success").inc()
    return result


@router.patch(
    "/",
    response_model=RemnawaveSettingsResponse,
    responses={202: {"description": "Update accepted without a response body"}},
)
async def update_settings(
    setting_data: UpdateRemnawaveSettingsRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> RemnawaveSettingsResponse | Response:
    """Patch the singleton Remnawave settings document (admin only)."""
    result = await client.patch_validated(
        "/remnawave-settings",
        RemnawaveSettingsResponse,
        json=setting_data.model_dump(
            mode="json",
            by_alias=True,
            exclude_unset=True,
        ),
    )
    route_operations_total.labels(route="settings", action="update", status="success").inc()
    if result is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return result


@router.post(
    "/",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 has no create-settings operation"}},
)
async def create_setting(
    setting_data: CreateSettingRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed legacy create operation without provider I/O."""
    _raise_legacy_settings_operation_unsupported()


@router.put(
    "/{id}",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 has no by-id settings operation"}},
)
async def update_setting(
    id: int,
    setting_data: UpdateSettingRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed legacy by-id operation without provider I/O."""
    _raise_legacy_settings_operation_unsupported()
