"""Admin-only routes for audit logs and webhook logs."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.webhook_log_repo import WebhookLogRepository
from src.presentation.api.v1.admin.schemas import AuditLogResponse, WebhookLogResponse
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.pagination import PaginationParams, get_pagination
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log", response_model=list[AuditLogResponse])
async def get_audit_logs(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.AUDIT_READ)),
) -> list[AuditLogResponse]:
    """Get audit logs (admin only)."""
    audit_log_repo = AuditLogRepository(db)

    logs = await audit_log_repo.get_paginated(
        offset=pagination.skip,
        limit=pagination.page_size,
    )

    return logs


@router.get("/webhook-log", response_model=list[WebhookLogResponse])
async def get_webhook_logs(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.WEBHOOK_READ)),
) -> list[WebhookLogResponse]:
    """Get webhook logs (admin only)."""
    webhook_log_repo = WebhookLogRepository(db)

    logs = await webhook_log_repo.get_paginated(
        offset=pagination.skip,
        limit=pagination.page_size,
    )

    return logs
