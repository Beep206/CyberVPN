from fastapi import APIRouter, Depends, HTTPException
from src.presentation.dependencies import get_current_active_user, require_role, get_remnawave_client
from src.infrastructure.remnawave.client import RemnawaveClient

from .schemas import CreateSubscriptionTemplateRequest, UpdateSubscriptionTemplateRequest

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

@router.get("/")
async def list_subscription_templates(
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """List all subscription templates (admin only)"""
    return await client.get("/subscriptions")

@router.post("/")
async def create_subscription_template(
    template_data: CreateSubscriptionTemplateRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Create a new subscription template (admin only)"""
    return await client.post("/subscriptions", json=template_data.model_dump())

@router.get("/{uuid}")
async def get_subscription_template(
    uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Get subscription template details"""
    return await client.get(f"/subscriptions/{uuid}")

@router.put("/{uuid}")
async def update_subscription_template(
    uuid: str,
    template_data: UpdateSubscriptionTemplateRequest,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Update subscription template (admin only)"""
    return await client.put(f"/subscriptions/{uuid}", json=template_data.model_dump(exclude_none=True))

@router.delete("/{uuid}")
async def delete_subscription_template(
    uuid: str,
    current_user=Depends(require_role("admin")),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Delete subscription template (admin only)"""
    return await client.delete(f"/subscriptions/{uuid}")

@router.get("/config/{user_uuid}")
async def generate_config(
    user_uuid: str,
    current_user=Depends(get_current_active_user),
    client: RemnawaveClient = Depends(get_remnawave_client)
):
    """Generate VPN configuration for a user"""
    return await client.get(f"/subscriptions/config/{user_uuid}")
