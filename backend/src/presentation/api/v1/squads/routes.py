from fastapi import APIRouter, Depends
from src.presentation.dependencies import get_current_active_user, require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreateSquadRequest, SquadResponse

router = APIRouter(prefix="/squads", tags=["squads"])

@router.get("/internal", responses={200: {"model": list[SquadResponse]}})
async def list_internal_squads(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List internal squads (admin only)"""
    return await client.get("/squads/internal")

@router.get("/external", responses={200: {"model": list[SquadResponse]}})
async def list_external_squads(
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List external squads"""
    return await client.get("/squads/external")

@router.post("/", responses={200: {"model": SquadResponse}})
async def create_squad(
    squad_data: CreateSquadRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new squad (admin only)"""
    return await client.post("/squads", json=squad_data.model_dump())
