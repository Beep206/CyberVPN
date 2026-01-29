from fastapi import APIRouter, Depends
from src.presentation.dependencies import require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import InboundResponse

router = APIRouter(prefix="/inbounds", tags=["inbounds"])

@router.get("/", responses={200: {"model": list[InboundResponse]}})
async def list_inbounds(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List all inbound configurations (admin only)"""
    return await client.get("/inbounds")

@router.get("/{uuid}", responses={200: {"model": InboundResponse}})
async def get_inbound(
    uuid: str,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get inbound configuration details (admin only)"""
    return await client.get(f"/inbounds/{uuid}")
