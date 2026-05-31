"""Commercial catalog admin permission and audit gates."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from src.application.use_cases.auth.permissions import Permission
from src.domain.enums import AdminRole
from src.presentation.api.v1.addons import routes as addon_routes
from src.presentation.api.v1.admin.audit import (
    STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS,
    write_required_commercial_catalog_audit_entry,
)
from src.presentation.api.v1.offers import routes as offer_routes
from src.presentation.api.v1.plans import routes as plan_routes
from src.presentation.api.v1.plans.schemas import CreatePlanRequest
from src.presentation.api.v1.pricebooks import routes as pricebook_routes
from src.presentation.dependencies.roles import require_permission


class RecordingDB:
    def __init__(self, *, fail_flush: bool = False) -> None:
        self.fail_flush = fail_flush
        self.added: list[object] = []

    def add(self, model) -> None:
        self.added.append(model)

    async def flush(self) -> None:
        if self.fail_flush:
            raise RuntimeError("audit flush failed")


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.55"),
        headers={
            "user-agent": "pytest-agent",
            "x-request-id": "req-commercial-catalog",
            "x-correlation-id": "corr-commercial-catalog",
        },
    )


def _admin(role: AdminRole = AdminRole.ADMIN):
    return SimpleNamespace(
        id=uuid4(),
        role=role.value,
        login=f"catalog-{role.value.replace('/', '-')}",
        email=f"{role.value.replace('/', '-')}@example.test",
        totp_enabled=True,
    )


def _dependency_permissions(router, endpoint) -> list[Permission]:
    route = next(item for item in router.routes if isinstance(item, APIRoute) and item.endpoint is endpoint)
    permissions: list[Permission] = []
    for dependency in route.dependant.dependencies:
        closure = dependency.call.__closure__ or ()
        for cell in closure:
            value = cell.cell_contents
            if isinstance(value, Permission):
                permissions.append(value)
    return permissions


@pytest.mark.asyncio
async def test_commercial_catalog_permission_denies_non_catalog_admin_roles() -> None:
    manage_plans = require_permission(Permission.MANAGE_PLANS)

    for allowed_role in (AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OWNER_SUPER_ADMIN):
        assert await manage_plans(_admin(allowed_role))

    for denied_role in (AdminRole.VIEWER, AdminRole.SUPPORT, AdminRole.FINANCE, AdminRole.OPERATOR):
        with pytest.raises(HTTPException) as permission_error:
            await manage_plans(_admin(denied_role))
        assert permission_error.value.status_code == 403
        assert permission_error.value.detail == "Missing permission: manage_plans"


def test_commercial_catalog_admin_routes_use_scoped_manage_plans_permission() -> None:
    scoped_endpoints = (
        (plan_routes.router, plan_routes.list_admin_plans),
        (plan_routes.router, plan_routes.create_plan),
        (plan_routes.router, plan_routes.update_plan),
        (plan_routes.router, plan_routes.delete_plan),
        (addon_routes.router, addon_routes.list_admin_addons),
        (addon_routes.router, addon_routes.create_addon),
        (addon_routes.router, addon_routes.update_addon),
        (offer_routes.router, offer_routes.list_admin_offers),
        (offer_routes.router, offer_routes.create_offer),
        (pricebook_routes.router, pricebook_routes.list_admin_pricebooks),
        (pricebook_routes.router, pricebook_routes.create_pricebook),
    )

    for router, endpoint in scoped_endpoints:
        assert Permission.MANAGE_PLANS in _dependency_permissions(router, endpoint)


def test_commercial_catalog_required_audit_manifest_covers_mutations() -> None:
    assert {
        "commercial_catalog.plan.created",
        "commercial_catalog.plan.updated",
        "commercial_catalog.plan.deleted",
        "commercial_catalog.addon.created",
        "commercial_catalog.addon.updated",
        "commercial_catalog.offer.created",
        "commercial_catalog.pricebook.created",
    } <= STAGE1_REQUIRED_ADMIN_AUDIT_ACTIONS


@pytest.mark.asyncio
async def test_commercial_catalog_audit_hashes_before_after_and_redacts_sensitive_values() -> None:
    db = RecordingDB()
    admin = _admin()

    await write_required_commercial_catalog_audit_entry(
        db=db,
        action="commercial_catalog.plan.updated",
        resource_type="subscription_plan",
        resource_id="plan-123",
        actor=admin,
        request=_request(),
        before={
            "display_name": "Basic",
            "api_key": "raw-api-key",
            "email_hint": "alice@example.com",
            "support_url": "https://support.example.test/secret-token",
        },
        after={
            "display_name": "Plus",
            "email_hint": "alice@example.com",
            "support_url": "https://support.example.test/new-secret-token",
            "nested": {"api_token": "raw-secret", "private_key": "raw-private-key"},
        },
    )

    audit_entry = db.added[0]
    assert audit_entry.action == "commercial_catalog.plan.updated"
    assert audit_entry.admin_id == admin.id
    assert audit_entry.entity_type == "subscription_plan"
    assert audit_entry.entity_id == "plan-123"
    assert audit_entry.old_value["request_id"] == "req-commercial-catalog"
    assert audit_entry.old_value["correlation_id"] == "corr-commercial-catalog"
    assert audit_entry.new_value["diff_hash"] == audit_entry.old_value["diff_hash"]
    assert len(audit_entry.new_value["diff_hash"]) == 64
    assert audit_entry.old_value["before"]["email_hint"] == "al***@example.com"
    assert audit_entry.old_value["before"]["api_key"] == "[REDACTED]"
    assert audit_entry.old_value["before"]["support_url"] == "[REDACTED]"
    assert audit_entry.new_value["after"]["nested"]["api_token"] == "[REDACTED]"
    assert audit_entry.new_value["after"]["nested"]["private_key"] == "[REDACTED]"
    serialized = f"{audit_entry.old_value} {audit_entry.new_value}"
    assert "secret-token" not in serialized
    assert "raw-secret" not in serialized
    assert "raw-api-key" not in serialized
    assert "raw-private-key" not in serialized
    assert "https://" not in serialized


@pytest.mark.asyncio
async def test_commercial_catalog_plan_create_fails_closed_when_audit_flush_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePlanRepo:
        def __init__(self, _db) -> None:
            pass

        async def get_by_name(self, _name):
            return None

        async def create(self, model):
            model.id = uuid4()
            return model

    monkeypatch.setattr(plan_routes, "SubscriptionPlanRepository", FakePlanRepo)

    with pytest.raises(RuntimeError, match="audit flush failed"):
        await plan_routes.create_plan(
            plan_data=CreatePlanRequest(
                name="plus_365",
                plan_code="plus",
                display_name="Plus",
                catalog_visibility="public",
                duration_days=365,
                devices_included=5,
                price_usd=79.0,
                features={"support_link": "https://support.example.test/private"},
            ),
            request=_request(),
            db=RecordingDB(fail_flush=True),
            current_user=_admin(),
        )
