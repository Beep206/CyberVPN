"""Admin-only routes for audit logs and webhook logs."""

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.webhook_log_repo import WebhookLogRepository
from src.presentation.api.v1.admin.schemas import AuditLogResponse, WebhookLogResponse
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.pagination import get_pagination, PaginationParams
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def get_audit_logs(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.AUDIT_READ)),
) -> List[AuditLogResponse]:
    """Get audit logs (admin only)."""
    try:
        audit_log_repo = AuditLogRepository(db)

        logs = await audit_log_repo.get_paginated(
            offset=pagination.skip,
            limit=pagination.page_size,
        )

        return [
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                username=log.username,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}",
        )


@router.get("/webhook-log", response_model=List[WebhookLogResponse])
async def get_webhook_logs(
    pagination: PaginationParams = Depends(get_pagination),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission(Permission.WEBHOOK_READ)),
) -> List[WebhookLogResponse]:
    """Get webhook logs (admin only)."""
    try:
        webhook_log_repo = WebhookLogRepository(db)

        logs = await webhook_log_repo.get_paginated(
            offset=pagination.skip,
            limit=pagination.page_size,
        )

        return [
            WebhookLogResponse(
                id=log.id,
                source=log.source,
                event_type=log.event_type,
                payload=log.payload,
                status=log.status,
                error_message=log.error_message,
                processed_at=log.processed_at,
                created_at=log.created_at,
            )
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook logs: {str(e)}",
        )
