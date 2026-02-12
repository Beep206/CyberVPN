from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveSquadResponse

from .schemas import CreateSquadRequest

router = APIRouter(prefix="/squads", tags=["squads"])


@router.get("/internal", response_model=list[RemnawaveSquadResponse])
async def list_internal_squads(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List internal squads (admin only)"""
    result = await client.get("/squads/internal")
    route_operations_total.labels(route="squads", action="list_internal", status="success").inc()
    return result


@router.get("/external", response_model=list[RemnawaveSquadResponse])
async def list_external_squads(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List external squads"""
    result = await client.get("/squads/external")
    route_operations_total.labels(route="squads", action="list_external", status="success").inc()
    return result


@router.post("/", response_model=RemnawaveSquadResponse)
async def create_squad(
    squad_data: CreateSquadRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new squad (admin only)"""
    result = await client.post("/squads", json=squad_data.model_dump())
    route_operations_total.labels(route="squads", action="create", status="success").inc()
    return result
