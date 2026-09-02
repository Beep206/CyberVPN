"""Fail-closed Remnawave 2.8 UUID -> 3.x numeric identity reconciliation."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    _acquire_remnawave_identity_registry_lock,
)
from src.domain.entities.user import User
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel


class RemnawaveUserInventory(Protocol):
    async def get_all_cursor(self, *, cursor: str | None = None, limit: int = 1000) -> list[User]: ...


@dataclass(frozen=True, slots=True)
class LocalRemnawaveSubject:
    subject_type: str
    subject_id: uuid.UUID
    customer_account_id: uuid.UUID
    legacy_uuid: uuid.UUID | None
    current_numeric_id: int | None
    identity_scope: str | None = None
    legacy_uuid_invalid: bool = False


@dataclass(frozen=True, slots=True)
class ReconciledRemnawaveSubject:
    subject: LocalRemnawaveSubject
    numeric_user_id: int
    legacy_uuid: uuid.UUID
    matched_by: Literal["legacy_uuid", "numeric_id"]
    provider_auto_renew_observed: bool | None = None


@dataclass(frozen=True, slots=True)
class RemnawaveReconciliationIssue:
    code: str
    subject_type: str | None = None
    subject_id: uuid.UUID | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RemnawaveReconciliationPlan:
    mappings: tuple[ReconciledRemnawaveSubject, ...]
    issues: tuple[RemnawaveReconciliationIssue, ...]
    upstream_count: int
    fingerprint: str

    @property
    def ready_for_cutover(self) -> bool:
        return not self.issues and bool(self.mappings)


class RemnawaveCutoverBlocked(RuntimeError):
    def __init__(self, plan: RemnawaveReconciliationPlan) -> None:
        self.plan = plan
        codes = sorted({issue.code for issue in plan.issues}) or ["empty_mapping"]
        super().__init__(f"Remnawave numeric identity cutover blocked: {', '.join(codes)}")


def build_remnawave_reconciliation_plan(
    *,
    upstream_users: Iterable[User],
    local_subjects: Iterable[LocalRemnawaveSubject],
) -> RemnawaveReconciliationPlan:
    """Build a deterministic all-or-nothing mapping without mutating persistence."""

    issues: list[RemnawaveReconciliationIssue] = []
    by_uuid: dict[uuid.UUID, User] = {}
    by_id: dict[int, User] = {}
    upstream_count = 0

    for user in upstream_users:
        upstream_count += 1
        if user.uuid is None or user.remnawave_id is None:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="upstream_identity_incomplete",
                    detail="2.8 inventory row did not contain both UUID and numeric id",
                )
            )
            continue
        if user.uuid in by_uuid and by_uuid[user.uuid].remnawave_id != user.remnawave_id:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="duplicate_upstream_uuid",
                    detail="one upstream UUID maps to multiple numeric ids",
                )
            )
            continue
        if user.remnawave_id in by_id and by_id[user.remnawave_id].uuid != user.uuid:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="duplicate_upstream_numeric_id",
                    detail="one upstream numeric id maps to multiple UUIDs",
                )
            )
            continue
        by_uuid[user.uuid] = user
        by_id[user.remnawave_id] = user

    mappings: list[ReconciledRemnawaveSubject] = []
    numeric_bindings: dict[int, list[LocalRemnawaveSubject]] = {}
    legacy_bindings: dict[uuid.UUID, list[LocalRemnawaveSubject]] = {}
    for subject in local_subjects:
        if subject.legacy_uuid_invalid:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="invalid_local_legacy_uuid",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="local rollback identity is not a valid UUID",
                )
            )
            continue
        match: User | None = None
        matched_by: Literal["legacy_uuid", "numeric_id"] = "legacy_uuid"
        if subject.legacy_uuid is not None:
            match = by_uuid.get(subject.legacy_uuid)
        elif subject.current_numeric_id is not None:
            match = by_id.get(subject.current_numeric_id)
            matched_by = "numeric_id"

        if match is None or match.uuid is None or match.remnawave_id is None:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="local_subject_missing_upstream",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="local Remnawave identity has no exact upstream mapping",
                )
            )
            continue
        if subject.current_numeric_id is not None and subject.current_numeric_id != match.remnawave_id:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="numeric_identity_conflict",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="stored numeric id disagrees with the 2.8 UUID inventory",
                )
            )
            continue
        owner_conflict = False
        prior_numeric_bindings = numeric_bindings.get(match.remnawave_id, [])
        if prior_numeric_bindings and any(
            prior.customer_account_id != subject.customer_account_id for prior in prior_numeric_bindings
        ):
            issues.append(
                RemnawaveReconciliationIssue(
                    code="provider_numeric_identity_owner_conflict",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="one provider numeric identity belongs to different customer accounts",
                )
            )
            owner_conflict = True
        prior_legacy_bindings = legacy_bindings.get(match.uuid, [])
        if prior_legacy_bindings and any(
            prior.customer_account_id != subject.customer_account_id for prior in prior_legacy_bindings
        ):
            issues.append(
                RemnawaveReconciliationIssue(
                    code="provider_legacy_identity_owner_conflict",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="one provider rollback identity belongs to different customer accounts",
                )
            )
            owner_conflict = True
        if owner_conflict:
            continue
        prior_same_type_numeric = next(
            (
                prior
                for prior in prior_numeric_bindings
                if prior.subject_id != subject.subject_id and prior.subject_type == subject.subject_type
            ),
            None,
        )
        if prior_same_type_numeric is not None:
            duplicate_code = "duplicate_provider_numeric_id"
            if (
                subject.subject_type == "service_identity"
                and subject.identity_scope == "subscription"
                and prior_same_type_numeric.identity_scope == "subscription"
            ):
                duplicate_code = "duplicate_subscription_numeric_id"
            issues.append(
                RemnawaveReconciliationIssue(
                    code=duplicate_code,
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="multiple same-type subjects resolve to one provider user",
                )
            )
            continue
        prior_same_type_legacy = next(
            (
                prior
                for prior in prior_legacy_bindings
                if prior.subject_id != subject.subject_id and prior.subject_type == subject.subject_type
            ),
            None,
        )
        if prior_same_type_legacy is not None:
            issues.append(
                RemnawaveReconciliationIssue(
                    code="duplicate_provider_legacy_uuid",
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    detail="multiple same-type subjects resolve to one rollback identity",
                )
            )
            continue
        numeric_bindings.setdefault(match.remnawave_id, []).append(subject)
        legacy_bindings.setdefault(match.uuid, []).append(subject)
        mappings.append(
            ReconciledRemnawaveSubject(
                subject=subject,
                numeric_user_id=match.remnawave_id,
                legacy_uuid=match.uuid,
                matched_by=matched_by,
                # Remnawave's provider-side flag is inventory evidence only.
                # Billing consent remains authoritative in CyberVPN.
                provider_auto_renew_observed=match.auto_renew,
            )
        )

    fingerprint_payload = [
        {
            "subject_type": item.subject.subject_type,
            "subject_id": str(item.subject.subject_id),
            "customer_account_id": str(item.subject.customer_account_id),
            "legacy_uuid": str(item.legacy_uuid),
            "numeric_user_id": item.numeric_user_id,
            "matched_by": item.matched_by,
            "provider_auto_renew_observed": item.provider_auto_renew_observed,
        }
        for item in sorted(mappings, key=lambda value: (value.subject.subject_type, str(value.subject.subject_id)))
    ]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RemnawaveReconciliationPlan(
        mappings=tuple(mappings),
        issues=tuple(issues),
        upstream_count=upstream_count,
        fingerprint=fingerprint,
    )


class ReconcileRemnawaveIdentitiesService:
    """Inventory 2.8 and atomically persist numeric ids only when every row agrees."""

    MAX_INVENTORY_USERS = 1_000_000

    def __init__(self, session: AsyncSession, inventory: RemnawaveUserInventory) -> None:
        self._session = session
        self._inventory = inventory

    async def execute(self, *, apply: bool = False) -> RemnawaveReconciliationPlan:
        upstream_users = await self._inventory.get_all_cursor(limit=self.MAX_INVENTORY_USERS)
        if apply:
            # Runtime mapping writes take this transaction lock before their
            # global provider-identity locks. Acquiring it before local
            # inventory prevents delete-and-replace from erasing a concurrent
            # runtime mapping committed after the plan was built.
            await _acquire_remnawave_identity_registry_lock(self._session)
        mobile_users = list(
            (
                await self._session.execute(
                    select(MobileUserModel).where(
                        (MobileUserModel.remnawave_uuid.is_not(None)) | (MobileUserModel.remnawave_user_id.is_not(None))
                    )
                )
            )
            .scalars()
            .all()
        )
        service_identities = list(
            (
                await self._session.execute(
                    select(ServiceIdentityModel).where(
                        ServiceIdentityModel.provider_name == "remnawave",
                        # Pre-cutover inventory must retain rollback identity
                        # coverage for inactive and disabled service subjects.
                        (ServiceIdentityModel.provider_subject_ref.is_not(None))
                        | (ServiceIdentityModel.provider_numeric_subject_id.is_not(None)),
                    )
                )
            )
            .scalars()
            .all()
        )
        subjects = [
            LocalRemnawaveSubject(
                subject_type="mobile_user",
                subject_id=user.id,
                customer_account_id=user.id,
                legacy_uuid=_parse_uuid(user.remnawave_uuid),
                current_numeric_id=user.remnawave_user_id,
                legacy_uuid_invalid=_legacy_uuid_is_invalid(user.remnawave_uuid),
            )
            for user in mobile_users
        ]
        subjects.extend(
            LocalRemnawaveSubject(
                subject_type="service_identity",
                subject_id=identity.id,
                customer_account_id=identity.customer_account_id,
                legacy_uuid=_parse_uuid(identity.provider_subject_ref),
                current_numeric_id=identity.provider_numeric_subject_id,
                identity_scope=identity.identity_scope,
                legacy_uuid_invalid=_legacy_uuid_is_invalid(identity.provider_subject_ref),
            )
            for identity in service_identities
        )
        plan = build_remnawave_reconciliation_plan(upstream_users=upstream_users, local_subjects=subjects)
        if not plan.ready_for_cutover:
            raise RemnawaveCutoverBlocked(plan)
        if not apply:
            return plan

        by_mobile_id = {user.id: user for user in mobile_users}
        by_service_id = {identity.id: identity for identity in service_identities}
        await self._session.execute(delete(RemnawaveIdentityReconciliationModel))
        reconciled_at = datetime.now(UTC)
        for mapping in plan.mappings:
            if mapping.subject.subject_type == "mobile_user":
                mobile_user = by_mobile_id[mapping.subject.subject_id]
                mobile_user.remnawave_user_id = mapping.numeric_user_id
                mobile_user.remnawave_uuid = str(mapping.legacy_uuid)
            else:
                service_identity = by_service_id[mapping.subject.subject_id]
                service_identity.provider_numeric_subject_id = mapping.numeric_user_id
                service_identity.provider_subject_ref = str(mapping.legacy_uuid)
            self._session.add(
                RemnawaveIdentityReconciliationModel(
                    id=uuid.uuid4(),
                    subject_type=mapping.subject.subject_type,
                    subject_id=mapping.subject.subject_id,
                    legacy_uuid=str(mapping.legacy_uuid),
                    numeric_user_id=mapping.numeric_user_id,
                    reconciliation_state="mapped",
                    evidence={
                        "inventory_fingerprint": plan.fingerprint,
                        "customer_account_id": str(mapping.subject.customer_account_id),
                        "matched_by": mapping.matched_by,
                        "upstream_count": plan.upstream_count,
                        "provider_auto_renew_authoritative": False,
                        "backend_auto_renew_consent_preserved": True,
                    },
                    reconciled_at=reconciled_at,
                    created_at=reconciled_at,
                    updated_at=reconciled_at,
                )
            )
        await self._session.flush()
        return plan


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _legacy_uuid_is_invalid(value: str | None) -> bool:
    return value not in (None, "") and _parse_uuid(value) is None
