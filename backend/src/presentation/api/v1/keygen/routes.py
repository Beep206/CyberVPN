from fastapi import APIRouter, Depends
from src.presentation.dependencies import get_current_active_user, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import SignPayloadRequest, PublicKeyResponse, SignPayloadResponse

router = APIRouter(prefix="/keygen", tags=["keygen"])

@router.get("/public-key", responses={200: {"model": PublicKeyResponse}})
async def get_public_key(
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get public key for signature verification"""
    return await client.get("/keygen/public-key")

@router.post("/sign-payload", responses={200: {"model": SignPayloadResponse}})
async def sign_payload(
    payload_data: SignPayloadRequest,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Sign a payload with the private key"""
    return await client.post("/keygen/sign-payload", json=payload_data.model_dump())
