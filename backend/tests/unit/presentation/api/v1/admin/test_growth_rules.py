from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from src.domain.enums import AdminRole
from src.infrastructure.database.models.growth_code_set_model import GrowthRuleDefinitionModel
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from src.presentation.api.v1.admin import growth_rules

ADMIN_ID = UUID("00000000-0000-0000-0000-000000000111")
POLICY_ID = UUID("00000000-0000-0000-0000-000000000222")
DEFINITION_ID = UUID("00000000-0000-0000-0000-000000000333")
NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)


class RecordingDB:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


class FakeCreateUseCase:
    async def create_draft(self, **kwargs):
        assert kwargs["created_by_admin_user_id"] == ADMIN_ID
        assert kwargs["policy_key"] == "Checkout_Eligibility"
        return _mutation_result(approval_state="draft", version_status="draft")


class FakeRejectUseCase:
    async def reject(self, **kwargs):
        assert kwargs["policy_version_id"] == POLICY_ID
        assert kwargs["rejection_reason"] == "unsafe private catalog action"
        return _mutation_result(
            approval_state="rejected",
            version_status="archived",
            previous_snapshot={"approval_state": "pending_approval", "version_status": "pending_approval"},
        )


class FakeInvalidStateUseCase:
    async def publish(self, **kwargs):
        _ = kwargs
        raise growth_rules.GrowthRulePolicyError(
            "growth_rule_policy_not_approved",
            "Growth rule policy must be approved before publish.",
        )


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.45"),
        state=SimpleNamespace(),
        headers={"user-agent": "pytest-admin"},
    )


def _admin():
    return SimpleNamespace(
        id=ADMIN_ID,
        role=AdminRole.ADMIN.value,
        login="growth-admin",
        email="growth-admin@example.test",
    )


def _policy(*, approval_state: str, version_status: str) -> PolicyVersionModel:
    return PolicyVersionModel(
        id=POLICY_ID,
        policy_family="growth_rules",
        policy_key="checkout_eligibility",
        subject_type="growth_rule",
        subject_id=None,
        version_number=3,
        payload={
            "rule_builder": {
                "schema_version": "growth-rule.v1",
                "catalog_version": "growth-rule-catalog.v1",
                "normalized_ast": {
                    "schema_version": "growth-rule.v1",
                    "when": {
                        "type": "condition",
                        "field": "checkout.currency",
                        "operator": "eq",
                        "value": "USD",
                    },
                    "then": [{"action": "allow", "params": {}}],
                },
                "compiled_plan": {"catalog_version": "growth-rule-catalog.v1"},
                "compiled_checksum": "checksum-route-test",
                "node_count": 2,
                "max_depth": 1,
                "complexity_score": 3,
            }
        },
        approval_state=approval_state,
        version_status=version_status,
        effective_from=NOW,
        effective_to=None,
        created_by_admin_user_id=ADMIN_ID,
    )


def _definition() -> GrowthRuleDefinitionModel:
    return GrowthRuleDefinitionModel(
        id=DEFINITION_ID,
        policy_version_id=POLICY_ID,
        schema_version="growth-rule.v1",
        ast_payload={
            "schema_version": "growth-rule.v1",
            "when": {
                "type": "condition",
                "field": "checkout.currency",
                "operator": "eq",
                "value": "USD",
            },
            "then": [{"action": "allow", "params": {}}],
        },
        compiled_plan_payload={"catalog_version": "growth-rule-catalog.v1"},
        compiled_checksum="checksum-route-test",
        complexity_score=3,
        node_count=2,
        max_depth=1,
        validation_status="valid",
        validation_errors={},
        compiled_at=NOW,
    )


def _mutation_result(
    *,
    approval_state: str,
    version_status: str,
    previous_snapshot: dict | None = None,
):
    return SimpleNamespace(
        policy_version=_policy(approval_state=approval_state, version_status=version_status),
        rule_definition=_definition(),
        previous_snapshot=previous_snapshot,
        retired_policy_version_ids=(),
    )


@pytest.mark.asyncio
async def test_create_growth_rule_policy_writes_sanitized_audit(monkeypatch) -> None:
    monkeypatch.setattr(growth_rules, "ManageGrowthRulePolicyUseCase", lambda _db: FakeCreateUseCase())
    db = RecordingDB()

    response = await growth_rules.create_growth_rule_policy(
        body=growth_rules.AdminGrowthRulePolicyCreateRequest(
            policy_key="Checkout_Eligibility",
            ast={
                "schema_version": "growth-rule.v1",
                "when": {
                    "type": "condition",
                    "field": "checkout.currency",
                    "operator": "eq",
                    "value": "USD",
                },
                "then": [{"action": "allow", "params": {}}],
            },
            change_reason="operator reviewed checkout eligibility rule",
        ),
        request=_request(),
        db=db,
        current_user=_admin(),
    )

    assert response.id == POLICY_ID
    assert response.compiled_checksum == "checksum-route-test"
    audit_entry = db.added[0]
    assert audit_entry.action == "growth_rule_policy.created"
    assert audit_entry.entity_type == "growth_rule_policy"
    assert audit_entry.entity_id == str(POLICY_ID)
    assert audit_entry.new_value["change_reason"] == "operator reviewed checkout eligibility rule"
    assert audit_entry.new_value["compiled_checksum"] == "checksum-route-test"
    assert "normalized_ast" not in audit_entry.new_value
    assert "compiled_plan" not in audit_entry.new_value


@pytest.mark.asyncio
async def test_reject_growth_rule_policy_records_old_and_new_lifecycle_state(monkeypatch) -> None:
    monkeypatch.setattr(growth_rules, "ManageGrowthRulePolicyUseCase", lambda _db: FakeRejectUseCase())
    db = RecordingDB()

    response = await growth_rules.reject_growth_rule_policy(
        policy_version_id=POLICY_ID,
        body=growth_rules.AdminGrowthRulePolicyActionRequest(change_reason="unsafe private catalog action"),
        request=_request(),
        db=db,
        current_user=_admin(),
    )

    assert response.approval_state == "rejected"
    assert response.version_status == "archived"
    audit_entry = db.added[0]
    assert audit_entry.action == "growth_rule_policy.rejected"
    assert audit_entry.old_value["approval_state"] == "pending_approval"
    assert audit_entry.new_value["approval_state"] == "rejected"
    assert audit_entry.new_value["change_reason"] == "unsafe private catalog action"


@pytest.mark.asyncio
async def test_publish_growth_rule_policy_maps_unapproved_policy_to_conflict(monkeypatch) -> None:
    monkeypatch.setattr(growth_rules, "ManageGrowthRulePolicyUseCase", lambda _db: FakeInvalidStateUseCase())

    with pytest.raises(HTTPException) as exc_info:
        await growth_rules.publish_growth_rule_policy(
            policy_version_id=POLICY_ID,
            body=growth_rules.AdminGrowthRulePolicyActionRequest(change_reason="publish after review"),
            request=_request(),
            db=RecordingDB(),
            current_user=_admin(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "growth_rule_policy_not_approved"
