from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from src.application.use_cases.growth_code_sets.rule_policies import (
    GROWTH_RULE_POLICY_FAMILY,
    GrowthRulePolicyError,
    ManageGrowthRulePolicyUseCase,
)
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthRuleCatalogVersionModel,
    GrowthRuleDefinitionModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel
from tests.helpers.realm_auth import (
    SyncSessionAdapter,
    cleanup_sqlite_file,
    create_realm_test_sessionmaker,
    initialize_realm_test_database,
)


def _rule_ast(*, currency: str = "USD") -> dict:
    return {
        "schema_version": "growth-rule.v1",
        "when": {
            "type": "condition",
            "field": "checkout.currency",
            "operator": "eq",
            "value": currency,
        },
        "then": [{"action": "allow", "params": {}}],
    }


@pytest.mark.asyncio
async def test_growth_rule_policy_lifecycle_persists_definition_and_supersedes_previous_active() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    admin_id = UUID("00000000-0000-0000-0000-000000000111")
    approver_id = UUID("00000000-0000-0000-0000-000000000222")

    try:
        with sessionmaker() as db:
            use_case = ManageGrowthRulePolicyUseCase(SyncSessionAdapter(db))
            first = await use_case.create_draft(
                policy_key="Checkout_Eligibility",
                subject_type="growth_rule",
                subject_id=None,
                ast=_rule_ast(currency="USD"),
                change_reason="initial rule",
                created_by_admin_user_id=admin_id,
            )
            assert first.policy_version.policy_family == GROWTH_RULE_POLICY_FAMILY
            assert first.policy_version.policy_key == "checkout_eligibility"
            assert first.policy_version.version_number == 1
            assert first.policy_version.approval_state == "draft"
            assert first.rule_definition is not None
            assert first.rule_definition.validation_status == "valid"
            assert first.rule_definition.compiled_checksum
            assert first.rule_definition.catalog_version_id is not None

            submitted = await use_case.submit_for_approval(first.policy_version.id)
            assert submitted.policy_version.approval_state == "pending_approval"
            approved = await use_case.approve(
                policy_version_id=first.policy_version.id,
                approved_by_admin_user_id=approver_id,
            )
            assert approved.policy_version.approval_state == "approved"
            assert approved.policy_version.version_status == "approved"
            published = await use_case.publish(policy_version_id=first.policy_version.id)
            assert published.policy_version.version_status == "active"

            second = await use_case.create_draft(
                policy_key="checkout_eligibility",
                subject_type="growth_rule",
                subject_id=None,
                ast=_rule_ast(currency="EUR"),
                change_reason="switch test currency",
                created_by_admin_user_id=admin_id,
            )
            assert second.policy_version.version_number == 2
            assert second.policy_version.supersedes_policy_version_id == first.policy_version.id
            await use_case.submit_for_approval(second.policy_version.id)
            await use_case.approve(
                policy_version_id=second.policy_version.id,
                approved_by_admin_user_id=approver_id,
            )
            second_published = await use_case.publish(
                policy_version_id=second.policy_version.id,
                effective_from=datetime(2026, 6, 26, 12, 0, tzinfo=UTC),
            )

            assert second_published.retired_policy_version_ids == (first.policy_version.id,)
            first_row = db.get(PolicyVersionModel, first.policy_version.id)
            second_row = db.get(PolicyVersionModel, second.policy_version.id)
            assert first_row is not None
            assert second_row is not None
            assert first_row.version_status == "superseded"
            assert first_row.effective_to == datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
            assert second_row.version_status == "active"

            definitions = (
                db.execute(select(GrowthRuleDefinitionModel).order_by(GrowthRuleDefinitionModel.created_at.asc()))
                .scalars()
                .all()
            )
            catalog_versions = db.execute(select(GrowthRuleCatalogVersionModel)).scalars().all()
            assert len(definitions) == 2
            assert len(catalog_versions) == 1
            assert definitions[0].catalog_version_id == catalog_versions[0].id
            assert definitions[1].catalog_version_id == catalog_versions[0].id
            assert definitions[0].policy_version_id == first.policy_version.id
            assert definitions[1].policy_version_id == second.policy_version.id
            assert definitions[0].compiled_checksum != definitions[1].compiled_checksum
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_rule_policy_rejects_invalid_ast_before_persistence() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)

    try:
        with sessionmaker() as db:
            use_case = ManageGrowthRulePolicyUseCase(SyncSessionAdapter(db))
            with pytest.raises(GrowthRulePolicyError) as exc_info:
                await use_case.create_draft(
                    policy_key="checkout_eligibility",
                    subject_type="growth_rule",
                    subject_id=None,
                    ast={"schema_version": "growth-rule.v1", "then": []},
                    change_reason="invalid draft",
                    created_by_admin_user_id=uuid4(),
                )

            assert exc_info.value.code == "RULE_WHEN_REQUIRED"
            assert db.execute(select(PolicyVersionModel)).scalars().all() == []
            assert db.execute(select(GrowthRuleDefinitionModel)).scalars().all() == []
            assert db.execute(select(GrowthRuleCatalogVersionModel)).scalars().all() == []
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)


@pytest.mark.asyncio
async def test_growth_rule_policy_rejects_self_approval_and_self_publish() -> None:
    sessionmaker, engine, sqlite_path = create_realm_test_sessionmaker()
    await initialize_realm_test_database(engine)
    admin_id = UUID("00000000-0000-0000-0000-000000000333")
    checker_id = UUID("00000000-0000-0000-0000-000000000444")

    try:
        with sessionmaker() as db:
            use_case = ManageGrowthRulePolicyUseCase(SyncSessionAdapter(db))
            draft = await use_case.create_draft(
                policy_key="checkout_eligibility",
                subject_type="growth_rule",
                subject_id=None,
                ast=_rule_ast(currency="USD"),
                change_reason="maker checker candidate",
                created_by_admin_user_id=admin_id,
            )
            await use_case.submit_for_approval(draft.policy_version.id)

            with pytest.raises(GrowthRulePolicyError) as self_approval:
                await use_case.approve(
                    policy_version_id=draft.policy_version.id,
                    approved_by_admin_user_id=admin_id,
                )
            assert self_approval.value.code == "growth_rule_policy_maker_checker_required"

            await use_case.approve(
                policy_version_id=draft.policy_version.id,
                approved_by_admin_user_id=checker_id,
            )
            draft.policy_version.approved_by_admin_user_id = admin_id
            db.flush()

            with pytest.raises(GrowthRulePolicyError) as self_publish:
                await use_case.publish(policy_version_id=draft.policy_version.id)
            assert self_publish.value.code == "growth_rule_policy_maker_checker_required"
    finally:
        engine.dispose()
        cleanup_sqlite_file(sqlite_path)
