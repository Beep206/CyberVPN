from fastapi import APIRouter, Depends
from src.presentation.dependencies import require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreateSnippetRequest

router = APIRouter(prefix="/snippets", tags=["snippets"])

@router.get("/")
async def list_snippets(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List configuration snippets (admin only)"""
    return await client.get("/snippets")

@router.post("/")
async def create_snippet(
    snippet_data: CreateSnippetRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new configuration snippet (admin only)"""
    return await client.post("/snippets", json=snippet_data.model_dump())
