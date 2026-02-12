from fastapi import APIRouter, Depends

from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client
from src.presentation.schemas.remnawave_responses import (
    RemnawavePublicKeyResponse,
    RemnawaveSignPayloadResponse,
)

from .schemas import SignPayloadRequest

router = APIRouter(prefix="/keygen", tags=["keygen"])


@router.get("/public-key", response_model=RemnawavePublicKeyResponse)
async def get_public_key(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get public key for signature verification"""
    result = await client.get("/keygen/public-key")
    route_operations_total.labels(route="keygen", action="get_public_key", status="success").inc()
    return result


@router.post("/sign-payload", response_model=RemnawaveSignPayloadResponse)
async def sign_payload(
    payload_data: SignPayloadRequest,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Sign a payload with the private key"""
    result = await client.post("/keygen/sign-payload", json=payload_data.model_dump())
    route_operations_total.labels(route="keygen", action="sign_payload", status="success").inc()
    return result
