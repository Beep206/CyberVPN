from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveSquadResponse

from .schemas import CreateSquadRequest

router = APIRouter(prefix="/squads", tags=["squads"])


def _map_squad(payload: dict, squad_type: str) -> dict:
    info = payload.get("info") if isinstance(payload, dict) else None
    members_count = None
    if isinstance(info, dict):
        members_count = info.get("membersCount")

    return {
        "uuid": payload["uuid"],
        "name": payload["name"],
        "squadType": squad_type,
        "maxMembers": None,
        "isActive": True,
        "description": None,
        "memberCount": members_count,
    }


@router.get("/internal", response_model=list[RemnawaveSquadResponse])
async def list_internal_squads(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List internal squads (admin only)"""
    result = await client.get("/internal-squads")
    route_operations_total.labels(route="squads", action="list_internal", status="success").inc()
    squads = result.get("internalSquads", []) if isinstance(result, dict) else []
    return [_map_squad(squad, "internal") for squad in squads]


@router.get("/external", response_model=list[RemnawaveSquadResponse])
async def list_external_squads(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List external squads"""
    result = await client.get("/external-squads")
    route_operations_total.labels(route="squads", action="list_external", status="success").inc()
    squads = result.get("externalSquads", []) if isinstance(result, dict) else []
    return [_map_squad(squad, "external") for squad in squads]


@router.post("/", response_model=RemnawaveSquadResponse)
async def create_squad(
    squad_data: CreateSquadRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new squad (admin only)"""
    if squad_data.squad_type == "internal":
        result = await client.post(
            "/internal-squads",
            json={"name": squad_data.name, "inbounds": squad_data.inbounds},
        )
    else:
        result = await client.post("/external-squads", json={"name": squad_data.name})
    route_operations_total.labels(route="squads", action="create", status="success").inc()
    return _map_squad(result, squad_data.squad_type)
