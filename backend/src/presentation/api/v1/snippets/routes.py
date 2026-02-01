from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role

from .schemas import CreateSnippetRequest, SnippetResponse

router = APIRouter(prefix="/snippets", tags=["snippets"])


@router.get("/", response_model=list[SnippetResponse])
async def list_snippets(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List configuration snippets (admin only)"""
    return await client.get("/snippets")


@router.post("/", response_model=SnippetResponse)
async def create_snippet(
    snippet_data: CreateSnippetRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new configuration snippet (admin only)"""
    return await client.post("/snippets", json=snippet_data.model_dump())
