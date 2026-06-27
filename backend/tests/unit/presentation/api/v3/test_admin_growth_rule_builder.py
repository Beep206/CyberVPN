from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.presentation.api.v1.admin.growth_rules import (
    AdminGrowthRuleCompileRequest,
    AdminGrowthRuleSimulateRequest,
)
from src.presentation.api.v1.router import api_router as api_v1_router
from src.presentation.api.v3.admin_growth_rule_builder import (
    compile_v3_growth_policy,
    get_v3_growth_rule_catalog,
    preview_v3_growth_policy_impact,
    validate_v3_growth_policy,
)
from src.presentation.api.v3.router import api_v3_router

pytestmark = [pytest.mark.asyncio]


async def _admin_user(db: AsyncSession) -> AdminUserModel:
    suffix = uuid4().hex[:8]
    user = AdminUserModel(
        id=uuid4(),
        login=f"growth-rule-builder-admin-{suffix}",
        email=f"growth-rule-builder-admin-{suffix}@example.test",
        role=AdminRole.ADMIN.value,
        is_active=True,
        is_email_verified=True,
        language="en",
        timezone="UTC",
    )
    db.add(user)
    await db.flush()
    return user


def _route_paths(router) -> set[str]:
    return {route.path for route in router.routes if isinstance(route, APIRoute)}


async def test_v3_rule_builder_exposes_canonical_paths_without_v1_backport(db: AsyncSession) -> None:
    admin = await _admin_user(db)
    v3_paths = _route_paths(api_v3_router)
    v1_paths = _route_paths(api_v1_router)

    assert "/api/v3/admin/growth/rule-catalog" in v3_paths
    assert "/api/v3/admin/growth/policies/validate" in v3_paths
    assert "/api/v3/admin/growth/policies/compile" in v3_paths
    assert "/api/v3/admin/growth/policies/impact-preview" in v3_paths
    assert "/api/v3/admin/growth/fx/status" in v3_paths
    assert "/api/v1/admin/growth/rule-catalog" not in v1_paths
    assert "/api/v1/admin/growth/policies/validate" not in v1_paths
    assert "/api/v1/admin/growth/fx/status" not in v1_paths
    assert "/api/v1/admin/growth/private-grants" not in v1_paths

    ast = {
        "schema_version": "growth-rule.v1",
        "when": {"type": "condition", "field": "checkout.currency", "operator": "eq", "value": "USD"},
        "then": [{"action": "allow", "params": {}}],
    }
    catalog = await get_v3_growth_rule_catalog(admin)
    validate_response = await validate_v3_growth_policy(AdminGrowthRuleCompileRequest(ast=ast), admin)
    compile_response = await compile_v3_growth_policy(AdminGrowthRuleCompileRequest(ast=ast), admin)
    preview_response = await preview_v3_growth_policy_impact(
        AdminGrowthRuleSimulateRequest(ast=ast, context={"checkout": {"currency": "USD"}}),
        admin,
    )

    assert catalog.catalog["catalog_version"] == "growth-rule-catalog.v1"
    assert validate_response.compiled_checksum == compile_response.compiled_checksum
    assert preview_response.matched is True
    assert preview_response.result == "allow"
