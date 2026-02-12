from fastapi import APIRouter, Depends

from src.domain.enums import AdminRole
from src.infrastructure.monitoring.metrics import route_operations_total
from src.infrastructure.remnawave.client import RemnawaveClient
from src.presentation.dependencies import get_remnawave_client, require_role
from src.presentation.schemas.remnawave_responses import RemnawaveSnippetResponse

from .schemas import CreateSnippetRequest

router = APIRouter(prefix="/snippets", tags=["snippets"])


@router.get("/", response_model=list[RemnawaveSnippetResponse])
async def list_snippets(
    current_user=Depends(require_role(AdminRole.ADMIN)), client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List configuration snippets (admin only)"""
    result = await client.get("/snippets")
    route_operations_total.labels(route="snippets", action="list", status="success").inc()
    return result


@router.post("/", response_model=RemnawaveSnippetResponse)
async def create_snippet(
    snippet_data: CreateSnippetRequest,
    current_user=Depends(require_role(AdminRole.ADMIN)),
    client: RemnawaveClient = Depends(get_remnawave_client),
):
    """Create a new configuration snippet (admin only)"""
    result = await client.post("/snippets", json=snippet_data.model_dump())
    route_operations_total.labels(route="snippets", action="create", status="success").inc()
    return result
