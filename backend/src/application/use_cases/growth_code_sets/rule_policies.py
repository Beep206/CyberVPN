"""Lifecycle management for admin-authored Growth Codes rule policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_code_sets.rule_builder import (
    RULE_CATALOG_VERSION,
    CompiledRule,
    RuleValidationError,
    build_rule_catalog,
    compile_rule_ast,
)
from src.infrastructure.database.models.growth_code_set_model import (
    GrowthRuleCatalogVersionModel,
    GrowthRuleDefinitionModel,
)
from src.infrastructure.database.models.policy_version_model import PolicyVersionModel

GROWTH_RULE_POLICY_FAMILY = "growth_rules"
DEFAULT_GROWTH_RULE_SUBJECT_TYPE = "growth_rule"


class GrowthRulePolicyError(ValueError):
    """Typed error for public admin API mapping."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GrowthRulePolicyMutationResult:
    policy_version: PolicyVersionModel
    rule_definition: GrowthRuleDefinitionModel | None
    previous_snapshot: dict[str, Any] | None = None
    retired_policy_version_ids: tuple[UUID, ...] = ()


class ManageGrowthRulePolicyUseCase:
    """Persist compiled rule ASTs and enforce policy-version state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_policies(
        self,
        *,
        policy_key: str | None = None,
        subject_type: str | None = None,
        subject_id: UUID | None = None,
        approval_state: str | None = None,
        include_inactive: bool = True,
        limit: int = 100,
    ) -> list[tuple[PolicyVersionModel, GrowthRuleDefinitionModel | None]]:
        query = (
            select(PolicyVersionModel, GrowthRuleDefinitionModel)
            .outerjoin(
                GrowthRuleDefinitionModel,
                GrowthRuleDefinitionModel.policy_version_id == PolicyVersionModel.id,
            )
            .where(PolicyVersionModel.policy_family == GROWTH_RULE_POLICY_FAMILY)
            .order_by(PolicyVersionModel.policy_key.asc(), PolicyVersionModel.version_number.desc())
            .limit(limit)
        )
        if policy_key is not None:
            query = query.where(PolicyVersionModel.policy_key == _normalize_policy_key(policy_key))
        if subject_type is not None:
            query = query.where(PolicyVersionModel.subject_type == subject_type.strip())
        if subject_id is not None:
            query = query.where(PolicyVersionModel.subject_id == subject_id)
        if approval_state is not None:
            query = query.where(PolicyVersionModel.approval_state == approval_state.strip())
        if not include_inactive:
            now = datetime.now(UTC)
            query = query.where(
                PolicyVersionModel.approval_state == "approved",
                PolicyVersionModel.version_status == "active",
                PolicyVersionModel.effective_from <= now,
                (PolicyVersionModel.effective_to.is_(None)) | (PolicyVersionModel.effective_to > now),
            )

        result = await self._session.execute(query)
        return [(policy, definition) for policy, definition in result.all()]

    async def create_draft(
        self,
        *,
        policy_key: str,
        subject_type: str,
        subject_id: UUID | None,
        ast: dict[str, Any],
        change_reason: str,
        created_by_admin_user_id: UUID,
    ) -> GrowthRulePolicyMutationResult:
        normalized_policy_key = _normalize_policy_key(policy_key)
        normalized_subject_type = subject_type.strip() or DEFAULT_GROWTH_RULE_SUBJECT_TYPE
        compiled = self._compile_or_raise(ast)
        catalog_version = await self._ensure_catalog_version()
        next_version = await self._next_version_number(normalized_policy_key)
        supersedes = await self._current_active_policy(
            policy_key=normalized_policy_key,
            subject_type=normalized_subject_type,
            subject_id=subject_id,
        )
        now = datetime.now(UTC)
        policy_version = PolicyVersionModel(
            policy_family=GROWTH_RULE_POLICY_FAMILY,
            policy_key=normalized_policy_key,
            subject_type=normalized_subject_type,
            subject_id=subject_id,
            version_number=next_version,
            payload=_build_policy_payload(compiled=compiled, change_reason=change_reason),
            approval_state="draft",
            version_status="draft",
            effective_from=now,
            effective_to=None,
            created_by_admin_user_id=created_by_admin_user_id,
            supersedes_policy_version_id=supersedes.id if supersedes is not None else None,
        )
        self._session.add(policy_version)
        await self._session.flush()

        rule_definition = _build_rule_definition(
            policy_version_id=policy_version.id,
            catalog_version_id=catalog_version.id,
            compiled=compiled,
        )
        self._session.add(rule_definition)
        await self._flush_policy_uniqueness()
        await self._session.refresh(policy_version)
        await self._session.refresh(rule_definition)
        return GrowthRulePolicyMutationResult(policy_version=policy_version, rule_definition=rule_definition)

    async def submit_for_approval(self, policy_version_id: UUID) -> GrowthRulePolicyMutationResult:
        policy_version, rule_definition = await self._get_policy_with_definition(policy_version_id)
        previous_snapshot = policy_audit_snapshot(policy_version, rule_definition)
        if policy_version.approval_state != "draft" or policy_version.version_status != "draft":
            raise GrowthRulePolicyError(
                "invalid_growth_rule_policy_state",
                "Only draft growth rule policies can be submitted for approval.",
            )
        policy_version.approval_state = "pending_approval"
        policy_version.version_status = "pending_approval"
        policy_version.updated_at = datetime.now(UTC)
        await self._flush_policy_uniqueness()
        await self._session.refresh(policy_version)
        return GrowthRulePolicyMutationResult(
            policy_version=policy_version,
            rule_definition=rule_definition,
            previous_snapshot=previous_snapshot,
        )

    async def approve(
        self,
        *,
        policy_version_id: UUID,
        approved_by_admin_user_id: UUID,
    ) -> GrowthRulePolicyMutationResult:
        policy_version, rule_definition = await self._get_policy_with_definition(policy_version_id)
        previous_snapshot = policy_audit_snapshot(policy_version, rule_definition)
        if policy_version.approval_state not in {"pending_approval", "draft"}:
            raise GrowthRulePolicyError(
                "invalid_growth_rule_policy_state",
                "Only draft or pending growth rule policies can be approved.",
            )
        if policy_version.created_by_admin_user_id == approved_by_admin_user_id:
            raise GrowthRulePolicyError(
                "growth_rule_policy_maker_checker_required",
                "Growth rule policy approval requires a different admin user.",
            )
        policy_version.approval_state = "approved"
        policy_version.version_status = "approved"
        policy_version.approved_by_admin_user_id = approved_by_admin_user_id
        policy_version.approved_at = datetime.now(UTC)
        policy_version.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(policy_version)
        return GrowthRulePolicyMutationResult(
            policy_version=policy_version,
            rule_definition=rule_definition,
            previous_snapshot=previous_snapshot,
        )

    async def reject(
        self,
        *,
        policy_version_id: UUID,
        rejection_reason: str,
    ) -> GrowthRulePolicyMutationResult:
        policy_version, rule_definition = await self._get_policy_with_definition(policy_version_id)
        previous_snapshot = policy_audit_snapshot(policy_version, rule_definition)
        if policy_version.approval_state not in {"pending_approval", "draft"}:
            raise GrowthRulePolicyError(
                "invalid_growth_rule_policy_state",
                "Only draft or pending growth rule policies can be rejected.",
            )
        policy_version.approval_state = "rejected"
        policy_version.version_status = "archived"
        policy_version.rejection_reason = rejection_reason
        policy_version.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(policy_version)
        return GrowthRulePolicyMutationResult(
            policy_version=policy_version,
            rule_definition=rule_definition,
            previous_snapshot=previous_snapshot,
        )

    async def publish(
        self,
        *,
        policy_version_id: UUID,
        effective_from: datetime | None = None,
        effective_to: datetime | None = None,
    ) -> GrowthRulePolicyMutationResult:
        policy_version, rule_definition = await self._get_policy_with_definition(policy_version_id)
        previous_snapshot = policy_audit_snapshot(policy_version, rule_definition)
        if policy_version.approval_state != "approved":
            raise GrowthRulePolicyError(
                "growth_rule_policy_not_approved",
                "Growth rule policy must be approved before publish.",
            )
        if (
            policy_version.created_by_admin_user_id is not None
            and policy_version.created_by_admin_user_id == policy_version.approved_by_admin_user_id
        ):
            raise GrowthRulePolicyError(
                "growth_rule_policy_maker_checker_required",
                "Growth rule policy publish requires independent approval.",
            )
        resolved_effective_from = effective_from or datetime.now(UTC)
        if effective_to is not None and effective_to <= resolved_effective_from:
            raise GrowthRulePolicyError(
                "invalid_growth_rule_policy_effective_window",
                "Policy effective_to must be greater than effective_from.",
            )

        retired = await self._retire_active_siblings(policy_version, retired_at=resolved_effective_from)
        policy_version.version_status = "active"
        policy_version.effective_from = resolved_effective_from
        policy_version.effective_to = effective_to
        policy_version.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(policy_version)
        return GrowthRulePolicyMutationResult(
            policy_version=policy_version,
            rule_definition=rule_definition,
            previous_snapshot=previous_snapshot,
            retired_policy_version_ids=tuple(retired),
        )

    async def rollback(
        self,
        *,
        target_policy_version_id: UUID,
        effective_from: datetime | None = None,
    ) -> GrowthRulePolicyMutationResult:
        policy_version, rule_definition = await self._get_policy_with_definition(target_policy_version_id)
        previous_snapshot = policy_audit_snapshot(policy_version, rule_definition)
        if policy_version.approval_state != "approved":
            raise GrowthRulePolicyError(
                "growth_rule_policy_not_approved",
                "Only approved growth rule policies can be restored.",
            )

        resolved_effective_from = effective_from or datetime.now(UTC)
        retired = await self._retire_active_siblings(policy_version, retired_at=resolved_effective_from)
        policy_version.version_status = "active"
        policy_version.effective_from = resolved_effective_from
        policy_version.effective_to = None
        policy_version.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(policy_version)
        return GrowthRulePolicyMutationResult(
            policy_version=policy_version,
            rule_definition=rule_definition,
            previous_snapshot=previous_snapshot,
            retired_policy_version_ids=tuple(retired),
        )

    async def diff(
        self,
        *,
        policy_version_id: UUID,
        compare_to_policy_version_id: UUID | None = None,
    ) -> tuple[
        PolicyVersionModel,
        GrowthRuleDefinitionModel | None,
        PolicyVersionModel | None,
        GrowthRuleDefinitionModel | None,
    ]:
        policy_version, rule_definition = await self._get_policy_with_definition(policy_version_id)
        compare_policy: PolicyVersionModel | None = None
        compare_definition: GrowthRuleDefinitionModel | None = None
        resolved_compare_id = compare_to_policy_version_id or policy_version.supersedes_policy_version_id
        if resolved_compare_id is not None:
            compare_policy, compare_definition = await self._get_policy_with_definition(resolved_compare_id)
        return policy_version, rule_definition, compare_policy, compare_definition

    async def _next_version_number(self, policy_key: str) -> int:
        result = await self._session.execute(
            select(func.max(PolicyVersionModel.version_number)).where(
                PolicyVersionModel.policy_family == GROWTH_RULE_POLICY_FAMILY,
                PolicyVersionModel.policy_key == policy_key,
            )
        )
        current_max = result.scalar_one_or_none()
        return int(current_max or 0) + 1

    async def _current_active_policy(
        self,
        *,
        policy_key: str,
        subject_type: str,
        subject_id: UUID | None,
    ) -> PolicyVersionModel | None:
        query = (
            select(PolicyVersionModel)
            .where(
                PolicyVersionModel.policy_family == GROWTH_RULE_POLICY_FAMILY,
                PolicyVersionModel.policy_key == policy_key,
                PolicyVersionModel.subject_type == subject_type,
                PolicyVersionModel.version_status == "active",
            )
            .order_by(PolicyVersionModel.effective_from.desc())
            .limit(1)
        )
        query = query.where(_subject_clause(subject_id))
        result = await self._session.execute(query)
        return result.scalars().first()

    async def _ensure_catalog_version(self) -> GrowthRuleCatalogVersionModel:
        result = await self._session.execute(
            select(GrowthRuleCatalogVersionModel).where(
                GrowthRuleCatalogVersionModel.catalog_version == RULE_CATALOG_VERSION
            )
        )
        existing = result.scalars().first()
        if existing is not None:
            return existing

        catalog = build_rule_catalog()
        model = GrowthRuleCatalogVersionModel(
            catalog_version=RULE_CATALOG_VERSION,
            fields_schema=catalog["fields"],
            operators_schema=catalog["operators"],
            actions_schema=catalog["actions"],
            status="active",
            checksum=_checksum_catalog(catalog),
            activated_at=datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return model

    async def _retire_active_siblings(self, policy_version: PolicyVersionModel, *, retired_at: datetime) -> list[UUID]:
        query = select(PolicyVersionModel).where(
            PolicyVersionModel.policy_family == policy_version.policy_family,
            PolicyVersionModel.policy_key == policy_version.policy_key,
            PolicyVersionModel.subject_type == policy_version.subject_type,
            PolicyVersionModel.version_status == "active",
            PolicyVersionModel.id != policy_version.id,
            _subject_clause(policy_version.subject_id),
        )
        result = await self._session.execute(query)
        retired_ids: list[UUID] = []
        for sibling in result.scalars().all():
            sibling.version_status = "superseded"
            sibling.effective_to = retired_at
            sibling.updated_at = datetime.now(UTC)
            retired_ids.append(sibling.id)
        return retired_ids

    async def _flush_policy_uniqueness(self) -> None:
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise GrowthRulePolicyError(
                "growth_rule_policy_active_conflict",
                "Another active growth rule policy already exists for this scope.",
            ) from exc

    async def _get_policy_with_definition(
        self,
        policy_version_id: UUID,
    ) -> tuple[PolicyVersionModel, GrowthRuleDefinitionModel | None]:
        result = await self._session.execute(
            select(PolicyVersionModel, GrowthRuleDefinitionModel)
            .outerjoin(
                GrowthRuleDefinitionModel,
                GrowthRuleDefinitionModel.policy_version_id == PolicyVersionModel.id,
            )
            .where(
                PolicyVersionModel.id == policy_version_id,
                PolicyVersionModel.policy_family == GROWTH_RULE_POLICY_FAMILY,
            )
        )
        row = result.first()
        if row is None:
            raise GrowthRulePolicyError("growth_rule_policy_not_found", "Growth rule policy version not found.")
        policy_version, rule_definition = row
        return policy_version, rule_definition

    def _compile_or_raise(self, ast: dict[str, Any]) -> CompiledRule:
        try:
            return compile_rule_ast(ast)
        except RuleValidationError as exc:
            raise GrowthRulePolicyError(exc.code, exc.message) from exc


def policy_audit_snapshot(
    policy_version: PolicyVersionModel,
    rule_definition: GrowthRuleDefinitionModel | None,
) -> dict[str, Any]:
    return {
        "policy_version_id": str(policy_version.id),
        "policy_key": policy_version.policy_key,
        "subject_type": policy_version.subject_type,
        "subject_id": str(policy_version.subject_id) if policy_version.subject_id is not None else None,
        "version_number": policy_version.version_number,
        "approval_state": policy_version.approval_state,
        "version_status": policy_version.version_status,
        "effective_from": policy_version.effective_from.isoformat(),
        "effective_to": policy_version.effective_to.isoformat() if policy_version.effective_to else None,
        "compiled_checksum": rule_definition.compiled_checksum if rule_definition else None,
        "node_count": rule_definition.node_count if rule_definition else None,
        "max_depth": rule_definition.max_depth if rule_definition else None,
        "complexity_score": rule_definition.complexity_score if rule_definition else None,
    }


def _build_policy_payload(*, compiled: CompiledRule, change_reason: str) -> dict[str, Any]:
    return {
        "rule_builder": {
            "schema_version": compiled.schema_version,
            "catalog_version": compiled.catalog_version,
            "normalized_ast": compiled.normalized_ast,
            "compiled_plan": compiled.compiled_plan,
            "compiled_checksum": compiled.compiled_checksum,
            "node_count": compiled.node_count,
            "max_depth": compiled.max_depth,
            "complexity_score": compiled.complexity_score,
        },
        "change_reason": change_reason,
    }


def _build_rule_definition(
    *,
    policy_version_id: UUID,
    catalog_version_id: UUID,
    compiled: CompiledRule,
) -> GrowthRuleDefinitionModel:
    return GrowthRuleDefinitionModel(
        policy_version_id=policy_version_id,
        catalog_version_id=catalog_version_id,
        schema_version=compiled.schema_version,
        ast_payload=compiled.normalized_ast,
        compiled_plan_payload=compiled.compiled_plan,
        compiled_checksum=compiled.compiled_checksum,
        complexity_score=compiled.complexity_score,
        node_count=compiled.node_count,
        max_depth=compiled.max_depth,
        validation_status="valid",
        validation_errors={},
        compiled_at=datetime.now(UTC),
    )


def _normalize_policy_key(policy_key: str) -> str:
    normalized = policy_key.strip().lower()
    if not normalized:
        raise GrowthRulePolicyError("invalid_growth_rule_policy_key", "Growth rule policy key is required.")
    return normalized


def _subject_clause(subject_id: UUID | None):
    if subject_id is None:
        return PolicyVersionModel.subject_id.is_(None)
    return PolicyVersionModel.subject_id == subject_id


def _checksum_catalog(catalog: dict[str, Any]) -> str:
    import hashlib
    import json

    payload = json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
