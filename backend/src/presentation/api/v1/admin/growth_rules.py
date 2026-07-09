"""Admin Growth Codes v6 rule-builder endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.permissions import Permission
from src.application.use_cases.growth_code_sets.rule_builder import (
    RuleValidationError,
    build_rule_catalog,
    compile_rule_ast,
    simulate_rule_ast,
)
from src.application.use_cases.growth_code_sets.rule_policies import (
    DEFAULT_GROWTH_RULE_SUBJECT_TYPE,
    GrowthRulePolicyError,
    ManageGrowthRulePolicyUseCase,
    policy_audit_snapshot,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.growth_code_set_model import GrowthRuleDefinitionModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_permission

from .audit import write_required_admin_audit_entry

router = APIRouter()
rules_router = APIRouter(prefix="/admin/growth/rules", tags=["admin", "growth-rules"])
policy_versions_router = APIRouter(
    prefix="/admin/growth/policy-versions",
    tags=["admin", "growth-policy-versions"],
)


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


class AdminGrowthRulePolicyCreateRequest(BaseModel):
    policy_key: str = Field(default="checkout_eligibility", min_length=1, max_length=80)
    subject_type: str = Field(default=DEFAULT_GROWTH_RULE_SUBJECT_TYPE, min_length=1, max_length=40)
    subject_id: UUID | None = None
    ast: dict[str, Any] = Field(default_factory=dict)
    change_reason: str = Field(..., min_length=3, max_length=500)


class AdminGrowthRulePolicyActionRequest(BaseModel):
    change_reason: str = Field(..., min_length=3, max_length=500)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class AdminGrowthRulePolicyRollbackRequest(BaseModel):
    change_reason: str = Field(..., min_length=3, max_length=500)
    effective_from: datetime | None = None


class AdminGrowthRulePolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_family: str
    policy_key: str
    subject_type: str
    subject_id: UUID | None
    version_number: int
    payload: dict[str, Any]
    approval_state: str
    version_status: str
    effective_from: datetime
    effective_to: datetime | None
    created_by_admin_user_id: UUID | None
    approved_by_admin_user_id: UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    supersedes_policy_version_id: UUID | None
    rule_definition_id: UUID | None
    schema_version: str | None
    catalog_version: str | None
    normalized_ast: dict[str, Any] | None
    compiled_plan: dict[str, Any] | None
    compiled_checksum: str | None
    node_count: int | None
    max_depth: int | None
    complexity_score: int | None
    validation_status: str | None


class AdminGrowthRulePolicyListResponse(BaseModel):
    items: list[AdminGrowthRulePolicyVersionResponse]
    total: int


class AdminGrowthRulePolicyDiffResponse(BaseModel):
    policy_version_id: UUID
    compare_to_policy_version_id: UUID | None
    current_checksum: str | None
    compare_checksum: str | None
    changed: bool
    changed_fields: list[str]
    current: AdminGrowthRulePolicyVersionResponse
    compare_to: AdminGrowthRulePolicyVersionResponse | None


@rules_router.get("/catalog", response_model=AdminGrowthRuleCatalogResponse)
async def get_growth_rule_catalog(
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
) -> AdminGrowthRuleCatalogResponse:
    return AdminGrowthRuleCatalogResponse(catalog=build_rule_catalog())


@rules_router.post("/compile", response_model=AdminGrowthRuleCompileResponse)
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


@rules_router.post("/simulate", response_model=AdminGrowthRuleSimulateResponse)
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


@policy_versions_router.get("", response_model=AdminGrowthRulePolicyListResponse)
async def list_growth_rule_policies(
    policy_key: str | None = Query(None, min_length=1, max_length=80),
    subject_type: str | None = Query(None, min_length=1, max_length=40),
    subject_id: UUID | None = Query(None),
    approval_state: str | None = Query(None, min_length=1, max_length=40),
    include_inactive: bool = Query(True),
    limit: int = Query(100, ge=1, le=200),
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyListResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    items = await use_case.list_policies(
        policy_key=policy_key,
        subject_type=subject_type,
        subject_id=subject_id,
        approval_state=approval_state,
        include_inactive=include_inactive,
        limit=limit,
    )
    responses = [_policy_response(policy, definition) for policy, definition in items]
    return AdminGrowthRulePolicyListResponse(items=responses, total=len(responses))


@policy_versions_router.post(
    "",
    response_model=AdminGrowthRulePolicyVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_growth_rule_policy(
    body: AdminGrowthRulePolicyCreateRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.create_draft(
            policy_key=body.policy_key,
            subject_type=body.subject_type,
            subject_id=body.subject_id,
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
        action="growth_rule_policy.created",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.post("/{policy_version_id}/submit", response_model=AdminGrowthRulePolicyVersionResponse)
async def submit_growth_rule_policy(
    policy_version_id: UUID,
    body: AdminGrowthRulePolicyActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_EDIT)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    _ = body.effective_from, body.effective_to
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.submit_for_approval(policy_version_id)
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_rule_policy.submitted",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.post("/{policy_version_id}/approve", response_model=AdminGrowthRulePolicyVersionResponse)
async def approve_growth_rule_policy(
    policy_version_id: UUID,
    body: AdminGrowthRulePolicyActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    _ = body.effective_from, body.effective_to
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.approve(
            policy_version_id=policy_version_id,
            approved_by_admin_user_id=current_user.id,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_rule_policy.approved",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.post("/{policy_version_id}/reject", response_model=AdminGrowthRulePolicyVersionResponse)
async def reject_growth_rule_policy(
    policy_version_id: UUID,
    body: AdminGrowthRulePolicyActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    _ = body.effective_from, body.effective_to
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.reject(
            policy_version_id=policy_version_id,
            rejection_reason=body.change_reason,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_rule_policy.rejected",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.post("/{policy_version_id}/publish", response_model=AdminGrowthRulePolicyVersionResponse)
async def publish_growth_rule_policy(
    policy_version_id: UUID,
    body: AdminGrowthRulePolicyActionRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_PUBLISH)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.publish(
            policy_version_id=policy_version_id,
            effective_from=body.effective_from,
            effective_to=body.effective_to,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_rule_policy.published",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.post("/{policy_version_id}/rollback", response_model=AdminGrowthRulePolicyVersionResponse)
async def rollback_growth_rule_policy(
    policy_version_id: UUID,
    body: AdminGrowthRulePolicyRollbackRequest,
    request: Request,
    current_user: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_PUBLISH)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyVersionResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        result = await use_case.rollback(
            target_policy_version_id=policy_version_id,
            effective_from=body.effective_from,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    await _write_policy_audit(
        db=db,
        request=request,
        actor=current_user,
        action="growth_rule_policy.rolled_back",
        result=result,
        change_reason=body.change_reason,
    )
    return _policy_response(result.policy_version, result.rule_definition)


@policy_versions_router.get("/{policy_version_id}/diff", response_model=AdminGrowthRulePolicyDiffResponse)
async def diff_growth_rule_policy(
    policy_version_id: UUID,
    compare_to_policy_version_id: UUID | None = Query(None),
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyDiffResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        current, current_definition, compare, compare_definition = await use_case.diff(
            policy_version_id=policy_version_id,
            compare_to_policy_version_id=compare_to_policy_version_id,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    return _diff_response(current, current_definition, compare, compare_definition)


@policy_versions_router.get(
    "/{policy_version_id}/diff/{compare_to_policy_version_id}",
    response_model=AdminGrowthRulePolicyDiffResponse,
)
async def diff_growth_rule_policy_against(
    policy_version_id: UUID,
    compare_to_policy_version_id: UUID,
    _: AdminUserModel = Depends(require_permission(Permission.GROWTH_RULES_VIEW)),
    db: AsyncSession = Depends(get_db),
) -> AdminGrowthRulePolicyDiffResponse:
    use_case = ManageGrowthRulePolicyUseCase(db)
    try:
        current, current_definition, compare, compare_definition = await use_case.diff(
            policy_version_id=policy_version_id,
            compare_to_policy_version_id=compare_to_policy_version_id,
        )
    except GrowthRulePolicyError as exc:
        raise _rule_policy_http_error(exc) from exc
    return _diff_response(current, current_definition, compare, compare_definition)


def _rule_validation_http_error(exc: RuleValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": exc.code,
            "message_key": f"growth.rules.{exc.code.lower()}",
            "message": exc.message,
        },
    )


def _rule_policy_http_error(exc: GrowthRulePolicyError) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.code.endswith("_not_found"):
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code.startswith("invalid_") or exc.code in {"max_nodes_exceeded", "max_depth_exceeded"}:
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    return HTTPException(
        status_code=status_code,
        detail={
            "code": exc.code,
            "message_key": f"growth.rules.{exc.code.lower()}",
            "message": exc.message,
        },
    )


def _policy_response(
    policy: PolicyVersionModel,
    definition: GrowthRuleDefinitionModel | None,
) -> AdminGrowthRulePolicyVersionResponse:
    rule_payload = policy.payload.get("rule_builder") if isinstance(policy.payload, dict) else {}
    if not isinstance(rule_payload, dict):
        rule_payload = {}
    return AdminGrowthRulePolicyVersionResponse(
        id=policy.id,
        policy_family=policy.policy_family,
        policy_key=policy.policy_key,
        subject_type=policy.subject_type,
        subject_id=policy.subject_id,
        version_number=policy.version_number,
        payload=policy.payload,
        approval_state=policy.approval_state,
        version_status=policy.version_status,
        effective_from=policy.effective_from,
        effective_to=policy.effective_to,
        created_by_admin_user_id=policy.created_by_admin_user_id,
        approved_by_admin_user_id=policy.approved_by_admin_user_id,
        approved_at=policy.approved_at,
        rejection_reason=policy.rejection_reason,
        supersedes_policy_version_id=policy.supersedes_policy_version_id,
        rule_definition_id=definition.id if definition is not None else None,
        schema_version=definition.schema_version
        if definition is not None
        else _string_or_none(rule_payload.get("schema_version")),
        catalog_version=_string_or_none(rule_payload.get("catalog_version")),
        normalized_ast=definition.ast_payload
        if definition is not None
        else _dict_or_none(rule_payload.get("normalized_ast")),
        compiled_plan=definition.compiled_plan_payload
        if definition is not None
        else _dict_or_none(rule_payload.get("compiled_plan")),
        compiled_checksum=definition.compiled_checksum
        if definition is not None
        else _string_or_none(rule_payload.get("compiled_checksum")),
        node_count=definition.node_count if definition is not None else _int_or_none(rule_payload.get("node_count")),
        max_depth=definition.max_depth if definition is not None else _int_or_none(rule_payload.get("max_depth")),
        complexity_score=definition.complexity_score
        if definition is not None
        else _int_or_none(rule_payload.get("complexity_score")),
        validation_status=definition.validation_status if definition is not None else None,
    )


async def _write_policy_audit(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    action: str,
    result,
    change_reason: str,
) -> None:
    details = policy_audit_snapshot(result.policy_version, result.rule_definition)
    details["change_reason"] = change_reason
    details["retired_policy_version_ids"] = [str(value) for value in result.retired_policy_version_ids]
    await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type="growth_rule_policy",
        resource_id=result.policy_version.id,
        actor=actor,
        request=request,
        details=details,
        old_value=result.previous_snapshot,
    )


def _changed_rule_policy_fields(
    current: AdminGrowthRulePolicyVersionResponse,
    compare_to: AdminGrowthRulePolicyVersionResponse | None,
) -> list[str]:
    if compare_to is None:
        return ["created"]
    changed_fields: list[str] = []
    for field in (
        "compiled_checksum",
        "normalized_ast",
        "compiled_plan",
        "node_count",
        "max_depth",
        "complexity_score",
    ):
        if getattr(current, field) != getattr(compare_to, field):
            changed_fields.append(field)
    return changed_fields


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _diff_response(
    current: PolicyVersionModel,
    current_definition: GrowthRuleDefinitionModel | None,
    compare: PolicyVersionModel | None,
    compare_definition: GrowthRuleDefinitionModel | None,
) -> AdminGrowthRulePolicyDiffResponse:
    current_response = _policy_response(current, current_definition)
    compare_response = _policy_response(compare, compare_definition) if compare is not None else None
    changed_fields = _changed_rule_policy_fields(current_response, compare_response)
    return AdminGrowthRulePolicyDiffResponse(
        policy_version_id=current.id,
        compare_to_policy_version_id=compare.id if compare is not None else None,
        current_checksum=current_definition.compiled_checksum if current_definition is not None else None,
        compare_checksum=compare_definition.compiled_checksum if compare_definition is not None else None,
        changed=bool(changed_fields),
        changed_fields=changed_fields,
        current=current_response,
        compare_to=compare_response,
    )


router.include_router(rules_router)
router.include_router(policy_versions_router)
