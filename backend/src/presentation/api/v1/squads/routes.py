from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.infrastructure.remnawave.contracts import RemnawaveRawSquadResponse, RemnawaveSquadResponse

from .schemas import CreateSquadRequest

router = APIRouter(prefix="/squads", tags=["squads"])


def _map_squad(payload: RemnawaveRawSquadResponse, squad_type: str) -> RemnawaveSquadResponse:
    return RemnawaveSquadResponse(
        uuid=payload.uuid,
        name=payload.name,
        squadType=squad_type,
        maxMembers=None,
        isActive=True,
        description=None,
        memberCount=payload.info.members_count if payload.info else None,
    )


@router.get("/internal", response_model=list[RemnawaveSquadResponse])
async def list_internal_squads(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List internal squads (admin only)"""
    result = await client.get_collection_validated("/internal-squads", "internalSquads", RemnawaveRawSquadResponse)
    route_operations_total.labels(route="squads", action="list_internal", status="success").inc()
    return [_map_squad(squad, "internal") for squad in result]


@router.get("/external", response_model=list[RemnawaveSquadResponse])
async def list_external_squads(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List external squads"""
    result = await client.get_collection_validated("/external-squads", "externalSquads", RemnawaveRawSquadResponse)
    route_operations_total.labels(route="squads", action="list_external", status="success").inc()
    return [_map_squad(squad, "external") for squad in result]


@router.post("/", response_model=RemnawaveSquadResponse)
async def create_squad(
    squad_data: CreateSquadRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new squad (admin only)"""
    if squad_data.squad_type == "internal":
        result = await client.post_validated(
            "/internal-squads",
            RemnawaveRawSquadResponse,
            json={"name": squad_data.name, "inbounds": squad_data.inbounds},
        )
    else:
        result = await client.post_validated(
            "/external-squads",
            RemnawaveRawSquadResponse,
            json={"name": squad_data.name},
        )
    route_operations_total.labels(route="squads", action="create", status="success").inc()
    return _map_squad(result, squad_data.squad_type)
