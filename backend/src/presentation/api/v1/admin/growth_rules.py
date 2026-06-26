"""Admin Growth Codes v6 rule-builder endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_code_sets.rule_builder import (
    RuleValidationError,
    build_rule_catalog,
    compile_rule_ast,
    simulate_rule_ast,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.dependencies.roles import require_permission

router = APIRouter(prefix="/admin/growth/rules", tags=["admin", "growth-rules"])


class AdminGrowthRuleCatalogResponse(BaseModel):
    catalog: dict[str, Any]


class AdminGrowthRuleCompileRequest(BaseModel):
    ast: dict[str, Any] = Field(default_factory=dict)


class AdminGrowthRuleCompileResponse(BaseModel):
    schema_version: str
    catalog_version: str
    normalized_ast: dict[str, Any]
    compiled_plan: dict[str, Any]
    compiled_checksum: str
    node_count: int
    max_depth: int
    complexity_score: int


class AdminGrowthRuleSimulateRequest(AdminGrowthRuleCompileRequest):
    context: dict[str, Any] = Field(default_factory=dict)


class AdminGrowthRuleSimulateResponse(BaseModel):
    matched: bool
    result: str
    actions: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    compiled_checksum: str


@router.get("/catalog", response_model=AdminGrowthRuleCatalogResponse)
async def get_growth_rule_catalog(
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
) -> AdminGrowthRuleCatalogResponse:
    return AdminGrowthRuleCatalogResponse(catalog=build_rule_catalog())


@router.post("/compile", response_model=AdminGrowthRuleCompileResponse)
async def compile_growth_rule(
    body: AdminGrowthRuleCompileRequest,
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VALIDATE)),
) -> AdminGrowthRuleCompileResponse:
    try:
        compiled = compile_rule_ast(body.ast)
    except RuleValidationError as exc:
        raise _rule_validation_http_error(exc) from exc
    return AdminGrowthRuleCompileResponse(
        schema_version=compiled.schema_version,
        catalog_version=compiled.catalog_version,
        normalized_ast=compiled.normalized_ast,
        compiled_plan=compiled.compiled_plan,
        compiled_checksum=compiled.compiled_checksum,
        node_count=compiled.node_count,
        max_depth=compiled.max_depth,
        complexity_score=compiled.complexity_score,
    )


@router.post("/simulate", response_model=AdminGrowthRuleSimulateResponse)
async def simulate_growth_rule(
    body: AdminGrowthRuleSimulateRequest,
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VALIDATE)),
) -> AdminGrowthRuleSimulateResponse:
    try:
        result = simulate_rule_ast(body.ast, body.context)
    except RuleValidationError as exc:
        raise _rule_validation_http_error(exc) from exc
    return AdminGrowthRuleSimulateResponse(
        matched=result.matched,
        result=result.result,
        actions=result.actions,
        trace=result.trace,
        compiled_checksum=result.compiled_checksum,
    )


def _rule_validation_http_error(exc: RuleValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": exc.code,
            "message_key": f"growth.rules.{exc.code.lower()}",
            "message": exc.message,
        },
    )
