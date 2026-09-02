from fastapi import APIRouter, Depends, HTTPException, status

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.infrastructure.remnawave.contracts import RemnawaveSnippetResponse
from src.presentation.api.v1.remnawave_degraded import optional_remnawave_read
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import CreateSnippetRequest

router = APIRouter(prefix="/snippets", tags=["snippets"])


@router.get("/", response_model=list[RemnawaveSnippetResponse])
async def list_snippets(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List configuration snippets (admin only)"""
    return await optional_remnawave_read(
        route="snippets",
        action="list",
        fetch=lambda: client.get_collection_validated("/snippets", "snippets", RemnawaveSnippetResponse),
        fallback=[],
    )


@router.post(
    "/",
    deprecated=True,
    responses={
        410: {"description": ("Legacy mutation disabled; use the durable trusted-admin Remnawave operator endpoint")}
    },
)
async def create_snippet(
    _snippet_data: CreateSnippetRequest,
    _current_user=Depends(require_role(AdminRole.ADMIN)),
) -> None:
    """Fail closed instead of replaying an unguarded legacy create mutation."""

    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=(
            "Legacy snippet creation is disabled. Use "
            "/api/v1/admin/remnawave-operator/snippets with an Idempotency-Key."
        ),
    )
