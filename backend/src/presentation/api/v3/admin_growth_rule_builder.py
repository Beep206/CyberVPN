"""Canonical Admin Growth Codes v6 rule-builder endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.application.use_cases.auth.permissions import Permission
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.admin.growth_rules import (
    AdminGrowthRuleCatalogResponse,
    AdminGrowthRuleCompileRequest,
    AdminGrowthRuleCompileResponse,
    AdminGrowthRuleSimulateRequest,
    AdminGrowthRuleSimulateResponse,
    compile_growth_rule,
    get_growth_rule_catalog,
    simulate_growth_rule,
)
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth", tags=["admin-growth-rule-builder-v3"])


@router.get("/rule-catalog", response_model=AdminGrowthRuleCatalogResponse)
async def get_v3_growth_rule_catalog(
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
) -> AdminGrowthRuleCatalogResponse:
    return await get_growth_rule_catalog(current_user)


@router.post("/policies/validate", response_model=AdminGrowthRuleCompileResponse)
async def validate_v3_growth_policy(
    body: AdminGrowthRuleCompileRequest,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VALIDATE)),
) -> AdminGrowthRuleCompileResponse:
    return await compile_growth_rule(body, current_user)


@router.post("/policies/compile", response_model=AdminGrowthRuleCompileResponse)
async def compile_v3_growth_policy(
    body: AdminGrowthRuleCompileRequest,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VALIDATE)),
) -> AdminGrowthRuleCompileResponse:
    return await compile_growth_rule(body, current_user)


@router.post("/policies/impact-preview", response_model=AdminGrowthRuleSimulateResponse)
async def preview_v3_growth_policy_impact(
    body: AdminGrowthRuleSimulateRequest,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VALIDATE)),
) -> AdminGrowthRuleSimulateResponse:
    return await simulate_growth_rule(body, current_user)
