from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status

from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_current_active_user, get_remnawave_client

from .schemas import SignPayloadRequest

router = APIRouter(prefix="/keygen", tags=["keygen"])

_KEYGEN_UNSUPPORTED_DETAIL = {"code": "remnawave_keygen_operation_not_supported"}


def _raise_keygen_unsupported(*, action: str) -> NoReturn:
    route_operations_total.labels(route="keygen", action=action, status="unsupported").inc()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=_KEYGEN_UNSUPPORTED_DETAIL,
    )


@router.get(
    "/public-key",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 has no public-key operation"}},
)
async def get_public_key(
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed public-key operation without exposing node secrets."""
    _raise_keygen_unsupported(action="get_public_key")


@router.post(
    "/sign-payload",
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    response_model=None,
    deprecated=True,
    responses={503: {"description": "Remnawave 3.4.3 has no sign-payload operation"}},
)
async def sign_payload(
    payload_data: SignPayloadRequest,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client),
) -> NoReturn:
    """Reject the removed sign-payload operation without provider I/O."""
    _raise_keygen_unsupported(action="sign_payload")
