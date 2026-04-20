from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import PartnerIntegrationCredentialKind, PartnerIntegrationCredentialStatus
from src.infrastructure.database.models.partner_integration_credential_model import (
    PartnerIntegrationCredentialModel,
)
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_integration_credential_repo import (
    PartnerIntegrationCredentialRepository,
)
from src.presentation.dependencies.database import get_db


@dataclass(frozen=True)
class PartnerReportingTokenAccess:
    workspace_id: UUID
    workspace_key: str
    workspace_status: str
    workspace_display_name: str
    credential: PartnerIntegrationCredentialModel


async def require_partner_reporting_token(
    workspace_id: UUID,
    authorization: str | None = Header(default=None, alias="Authorization"),
    reporting_token: str | None = Header(default=None, alias="X-Partner-Reporting-Token"),
    db: AsyncSession = Depends(get_db),
) -> PartnerReportingTokenAccess:
    raw_token = _extract_token(authorization=authorization, explicit_token=reporting_token)
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Partner reporting token is required",
        )

    hashed_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    credential = await PartnerIntegrationCredentialRepository(db).get_by_hash_and_kind(
        credential_hash=hashed_token,
        credential_kind=PartnerIntegrationCredentialKind.REPORTING_API_TOKEN.value,
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner reporting token is invalid",
        )

    workspace = await PartnerAccountRepository(db).get_account_by_id(credential.partner_account_id)
    if workspace is None or workspace.id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner reporting token is not scoped to this workspace",
        )

    if _effective_token_status(workspace_status=workspace.status, credential=credential) != "ready":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Partner reporting token is not active for this workspace",
        )

    return PartnerReportingTokenAccess(
        workspace_id=workspace.id,
        workspace_key=workspace.account_key,
        workspace_status=workspace.status,
        workspace_display_name=workspace.display_name,
        credential=credential,
    )


def _extract_token(*, authorization: str | None, explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token.strip()
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _effective_token_status(
    *,
    workspace_status: str,
    credential: PartnerIntegrationCredentialModel,
) -> str:
    if workspace_status in {"restricted", "suspended", "rejected", "terminated"}:
        return PartnerIntegrationCredentialStatus.BLOCKED.value
    if credential.credential_status == PartnerIntegrationCredentialStatus.BLOCKED.value:
        return PartnerIntegrationCredentialStatus.BLOCKED.value
    if workspace_status in {
        "draft",
        "email_verified",
        "submitted",
        "under_review",
        "waitlisted",
        "approved_probation",
        "needs_info",
    }:
        return PartnerIntegrationCredentialStatus.PENDING_ROTATION.value
    return credential.credential_status
