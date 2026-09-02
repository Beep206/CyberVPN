from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client

from .schemas import CreatePaymentRequest

router = APIRouter(prefix="/billing", tags=["billing"])

_BILLING_UNSUPPORTED_DETAIL = {"code": "remnawave_billing_not_supported"}


def _raise_billing_unsupported(*, action: str) -> NoReturn:
    route_operations_total.labels(route="billing", action=action, status="unsupported").inc()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=_BILLING_UNSUPPORTED_DETAIL,
    )


@router.get(
    "/",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 exposes no customer billing endpoint"}},
)
async def get_billing_info(
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed Remnawave billing proxy without provider I/O."""
    _raise_billing_unsupported(action="get_billing_info")


@router.post(
    "/",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 exposes no customer payment endpoint"}},
)
async def create_payment(
    payment_data: CreatePaymentRequest,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed Remnawave payment proxy without provider I/O."""
    _raise_billing_unsupported(action="create_payment")
