from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_code_sets.rule_policies import (
    DEFAULT_GROWTH_RULE_SUBJECT_TYPE,
    GrowthRulePolicyError,
    ManageGrowthRulePolicyUseCase,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.admin.growth_rules import (
    AdminGrowthRulePolicyCreateRequest,
    AdminGrowthRulePolicyVersionResponse,
    _policy_response,
    _rule_policy_http_error,
    _write_policy_audit,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth", tags=["admin-growth-policies-v3"])


@router.post(
    "/campaigns/{campaign_id}/policy-versions",
    response_model=AdminGrowthRulePolicyVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_growth_campaign_policy_version(
    campaign_id: UUID,
    body: AdminGrowthRulePolicyCreateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.create_draft(
            policy_key=body.policy_key,
            subject_type=body.subject_type or DEFAULT_GROWTH_RULE_SUBJECT_TYPE,
            subject_id=campaign_id,
            ast=body.ast,
            change_reason=body.change_reason,
            created_by_admin_user_id=current_user.id,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_campaign_policy_version.created",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)
