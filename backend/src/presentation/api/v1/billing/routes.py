from fastapi import APIRouter, Depends

from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client
from src.presentation.schemas.remnawave_responses import RemnavwaveBillingRecordResponse

from .schemas import CreatePaymentRequest

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/", response_model=list[RemnavwaveBillingRecordResponse])
async def get_billing_info(
    current_user=Depends(get_current_active_user), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get user billing information and history"""
    return await client.get("/billing")


@router.post("/", response_model=RemnavwaveBillingRecordResponse)
async def create_payment(
    payment_data: CreatePaymentRequest,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new payment transaction"""
    return await client.post("/billing", json=payment_data.model_dump())
