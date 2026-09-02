"""Transactional retirement of a customer's canonical Remnawave identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_create_attempts import remnawave_customer_create_key
from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    _acquire_remnawave_identity_dimension_locks,
    _acquire_remnawave_identity_registry_lock,
    _normalize_runtime_identity,
    _parse_optional_legacy_uuid,
)
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel
from src.infrastructure.database.models.remnawave_upgrade_model import (
    PartnerRemnawaveResourceGrantModel,
    RemnawaveIdentityReconciliationModel,
)
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel

_RETIREMENT_REASON = "Owning customer account deleted"


@dataclass(frozen=True)
class RemnawaveOwnerIdentityRetirementPlan:
    """Locked local state that one confirmed provider deletion may retire."""

    customer: MobileUserModel
    user_ref: RemnawaveUserRef | None
    provider_refs: tuple[RemnawaveUserRef, ...]
    service_identities: tuple[ServiceIdentityModel, ...]
    reconciliations: tuple[RemnawaveIdentityReconciliationModel, ...]
    active_grants: tuple[PartnerRemnawaveResourceGrantModel, ...]


def _local_ref(numeric_user_id: object, legacy_uuid_raw: object) -> RemnawaveUserRef | None:
    if numeric_user_id is None and legacy_uuid_raw in {None, ""}:
        return None
    return _normalize_runtime_identity(
        numeric_user_id=numeric_user_id,
        legacy_uuid_raw=legacy_uuid_raw,
    )


def _assert_exact_subject_ledger(
    *,
    subject_label: str,
    local_ref: RemnawaveUserRef | None,
    rows: list[RemnawaveIdentityReconciliationModel],
) -> None:
    if local_ref is None:
        if any(
            row.reconciliation_state == "mapped" or row.numeric_user_id is not None or row.legacy_uuid not in {None, ""}
            for row in rows
        ):
            raise RemnawaveIdentityAccessConflict(
                f"{subject_label} has a reconciliation identity without a local binding"
            )
        return
    if len(rows) != 1:
        raise RemnawaveIdentityAccessConflict(f"{subject_label} reconciliation is not unique")
    row = rows[0]
    if row.reconciliation_state != "mapped" or row.numeric_user_id != local_ref.require_numeric_id():
        raise RemnawaveIdentityAccessConflict(f"{subject_label} reconciliation is incomplete")
    if _parse_optional_legacy_uuid(row.legacy_uuid) != local_ref.legacy_uuid:
        raise RemnawaveIdentityAccessConflict(f"{subject_label} reconciliation conflicts with the local subject")


def _validate_owner_bindings(
    *,
    customer: MobileUserModel,
    service_identities: list[ServiceIdentityModel],
    reconciliations: list[RemnawaveIdentityReconciliationModel],
) -> tuple[RemnawaveUserRef, ...]:
    """Require exact ledgers and return every distinct owner provider pair."""

    user_ref = _local_ref(customer.remnawave_user_id, customer.remnawave_uuid)
    provider_refs = {user_ref} if user_ref is not None else set()
    mobile_rows = [
        row for row in reconciliations if row.subject_type == "mobile_user" and row.subject_id == customer.id
    ]
    _assert_exact_subject_ledger(
        subject_label="Mobile Remnawave identity",
        local_ref=user_ref,
        rows=mobile_rows,
    )

    for identity in service_identities:
        if identity.customer_account_id != customer.id or identity.provider_name != "remnawave":
            raise RemnawaveIdentityAccessConflict("Remnawave service identity owner is invalid")
        service_ref = _local_ref(
            identity.provider_numeric_subject_id,
            identity.provider_subject_ref,
        )
        service_rows = [
            row for row in reconciliations if row.subject_type == "service_identity" and row.subject_id == identity.id
        ]
        _assert_exact_subject_ledger(
            subject_label="Service Remnawave identity",
            local_ref=service_ref,
            rows=service_rows,
        )
        if service_ref is None:
            continue
        for existing_ref in provider_refs:
            if existing_ref == service_ref:
                continue
            numeric_collision = existing_ref.require_numeric_id() == service_ref.require_numeric_id()
            legacy_collision = (
                existing_ref.legacy_uuid is not None
                and service_ref.legacy_uuid is not None
                and existing_ref.legacy_uuid == service_ref.legacy_uuid
            )
            if numeric_collision or legacy_collision:
                raise RemnawaveIdentityAccessConflict("Customer Remnawave provider pairs are inconsistent")
        provider_refs.add(service_ref)
    return tuple(
        sorted(
            provider_refs,
            key=lambda ref: (
                ref.require_numeric_id(),
                str(ref.legacy_uuid) if ref.legacy_uuid is not None else "",
            ),
        )
    )


def _identity_dimensions(
    *,
    customer: MobileUserModel,
    service_identities: list[ServiceIdentityModel],
    reconciliations: list[RemnawaveIdentityReconciliationModel],
) -> set[str]:
    scopes = {f"remnawave-identity:subject:mobile_user:{customer.id}"}
    candidates: list[tuple[object, object]] = [
        (customer.remnawave_user_id, customer.remnawave_uuid),
    ]
    for identity in service_identities:
        scopes.add(f"remnawave-identity:subject:service_identity:{identity.id}")
        candidates.append((identity.provider_numeric_subject_id, identity.provider_subject_ref))
    candidates.extend((row.numeric_user_id, row.legacy_uuid) for row in reconciliations)

    for numeric_user_id, legacy_uuid_raw in candidates:
        if numeric_user_id is not None:
            if isinstance(numeric_user_id, bool) or not isinstance(numeric_user_id, int) or numeric_user_id <= 0:
                raise RemnawaveIdentityAccessConflict("Remnawave numeric identity is incomplete")
            scopes.add(f"remnawave-identity:numeric:{numeric_user_id}")
        legacy_uuid = _parse_optional_legacy_uuid(legacy_uuid_raw)
        if legacy_uuid is not None:
            scopes.add(f"remnawave-identity:legacy:{legacy_uuid}")
    return scopes


def _owner_ledger_filter(customer_id: UUID, service_identity_ids: set[UUID]):
    clauses = [
        and_(
            RemnawaveIdentityReconciliationModel.subject_type == "mobile_user",
            RemnawaveIdentityReconciliationModel.subject_id == customer_id,
        )
    ]
    if service_identity_ids:
        clauses.append(
            and_(
                RemnawaveIdentityReconciliationModel.subject_type == "service_identity",
                RemnawaveIdentityReconciliationModel.subject_id.in_(service_identity_ids),
            )
        )
    return or_(*clauses)


async def _assert_provider_dimensions_have_no_foreign_owner(
    session: AsyncSession,
    *,
    customer_id: UUID,
    service_identity_ids: set[UUID],
    provider_refs: tuple[RemnawaveUserRef, ...],
) -> None:
    if not provider_refs:
        return
    numeric_ids = {ref.require_numeric_id() for ref in provider_refs}
    legacy_uuids = {str(ref.legacy_uuid) for ref in provider_refs if ref.legacy_uuid is not None}
    dimension_filters = [RemnawaveIdentityReconciliationModel.numeric_user_id.in_(numeric_ids)]
    if legacy_uuids:
        dimension_filters.append(
            func.lower(func.trim(RemnawaveIdentityReconciliationModel.legacy_uuid)).in_(legacy_uuids)
        )
    dimension_rows = list(
        (
            await session.execute(
                select(RemnawaveIdentityReconciliationModel).where(or_(*dimension_filters)).with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for row in dimension_rows:
        owned = (row.subject_type == "mobile_user" and row.subject_id == customer_id) or (
            row.subject_type == "service_identity" and row.subject_id in service_identity_ids
        )
        if not owned:
            raise RemnawaveIdentityAccessConflict(
                "Remnawave provider identity is referenced by another reconciliation owner"
            )

    mobile_filters = [MobileUserModel.remnawave_user_id.in_(numeric_ids)]
    service_filters = [ServiceIdentityModel.provider_numeric_subject_id.in_(numeric_ids)]
    if legacy_uuids:
        mobile_filters.append(func.lower(func.trim(MobileUserModel.remnawave_uuid)).in_(legacy_uuids))
        service_filters.append(func.lower(func.trim(ServiceIdentityModel.provider_subject_ref)).in_(legacy_uuids))
    foreign_mobile = (
        await session.execute(
            select(MobileUserModel.id)
            .where(or_(*mobile_filters), MobileUserModel.id != customer_id)
            .with_for_update()
            .limit(1)
        )
    ).scalar_one_or_none()
    foreign_service = (
        await session.execute(
            select(ServiceIdentityModel.id)
            .where(
                or_(*service_filters),
                ServiceIdentityModel.provider_name == "remnawave",
                ServiceIdentityModel.customer_account_id != customer_id,
            )
            .with_for_update()
            .limit(1)
        )
    ).scalar_one_or_none()
    if foreign_mobile is not None or foreign_service is not None:
        raise RemnawaveIdentityAccessConflict("Remnawave provider identity is referenced by another local owner")


async def prepare_remnawave_owner_identity_retirement(
    session: AsyncSession,
    *,
    customer: MobileUserModel,
) -> RemnawaveOwnerIdentityRetirementPlan:
    """Lock and validate all local aliases before any provider delete.

    The exclusive registry lock is acquired before the sorted subject/provider
    dimensions, matching the registry-first order used by runtime mapping.
    Locks remain transaction-scoped through the caller's commit or rollback.
    """

    customer_id = customer.id
    if not isinstance(customer_id, UUID):
        raise RemnawaveIdentityAccessConflict("Remnawave identity owner is invalid")
    await _acquire_remnawave_identity_registry_lock(session)

    unresolved_mutation = (
        await session.execute(
            select(ApiIdempotencyRecordModel.id)
            .where(
                ApiIdempotencyRecordModel.status.in_(("pending", "reconciliation_required")),
                or_(
                    ApiIdempotencyRecordModel.resource_id == customer_id,
                    ApiIdempotencyRecordModel.idempotency_key == remnawave_customer_create_key(customer_id),
                ),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if unresolved_mutation is not None:
        raise RemnawaveIdentityAccessConflict("Customer has an unresolved Remnawave provider mutation")

    reloaded_customer = (
        await session.execute(select(MobileUserModel).where(MobileUserModel.id == customer_id))
    ).scalar_one_or_none()
    if reloaded_customer is None:
        raise RemnawaveIdentityAccessConflict("Remnawave identity owner does not exist")
    customer = reloaded_customer
    initial_identities = list(
        (
            await session.execute(
                select(ServiceIdentityModel).where(
                    ServiceIdentityModel.customer_account_id == customer_id,
                    ServiceIdentityModel.provider_name == "remnawave",
                )
            )
        )
        .scalars()
        .all()
    )
    service_identity_ids = {identity.id for identity in initial_identities}
    initial_reconciliations = list(
        (
            await session.execute(
                select(RemnawaveIdentityReconciliationModel).where(
                    _owner_ledger_filter(customer_id, service_identity_ids)
                )
            )
        )
        .scalars()
        .all()
    )
    await _acquire_remnawave_identity_dimension_locks(
        session,
        _identity_dimensions(
            customer=customer,
            service_identities=initial_identities,
            reconciliations=initial_reconciliations,
        ),
    )

    customer = (
        await session.execute(select(MobileUserModel).where(MobileUserModel.id == customer_id).with_for_update())
    ).scalar_one()
    service_identities = list(
        (
            await session.execute(
                select(ServiceIdentityModel)
                .where(
                    ServiceIdentityModel.customer_account_id == customer_id,
                    ServiceIdentityModel.provider_name == "remnawave",
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    service_identity_ids = {identity.id for identity in service_identities}
    reconciliations = list(
        (
            await session.execute(
                select(RemnawaveIdentityReconciliationModel)
                .where(_owner_ledger_filter(customer_id, service_identity_ids))
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    provider_refs = _validate_owner_bindings(
        customer=customer,
        service_identities=service_identities,
        reconciliations=reconciliations,
    )
    await _assert_provider_dimensions_have_no_foreign_owner(
        session,
        customer_id=customer_id,
        service_identity_ids=service_identity_ids,
        provider_refs=provider_refs,
    )
    user_ref = _local_ref(customer.remnawave_user_id, customer.remnawave_uuid)

    active_grants: list[PartnerRemnawaveResourceGrantModel] = []
    if service_identity_ids:
        active_grants = list(
            (
                await session.execute(
                    select(PartnerRemnawaveResourceGrantModel)
                    .where(
                        PartnerRemnawaveResourceGrantModel.resource_type == "service_identity",
                        PartnerRemnawaveResourceGrantModel.resource_uuid.in_(service_identity_ids),
                        PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
    return RemnawaveOwnerIdentityRetirementPlan(
        customer=customer,
        user_ref=user_ref,
        provider_refs=provider_refs,
        service_identities=tuple(service_identities),
        reconciliations=tuple(reconciliations),
        active_grants=tuple(active_grants),
    )


async def apply_remnawave_owner_identity_retirement(
    session: AsyncSession,
    *,
    plan: RemnawaveOwnerIdentityRetirementPlan,
    retired_at: datetime,
) -> None:
    """Retire aliases, grants, and ledger in the caller-owned transaction."""

    affected_identity_ids = {identity.id for identity in plan.service_identities}
    for identity in plan.service_identities:
        identity.identity_status = "revoked"
        identity.provider_numeric_subject_id = None
        identity.provider_subject_ref = None
        context = dict(identity.service_context or {})
        context["remnawave_identity_retirement"] = {
            "reason": "customer_account_deleted",
            "retired_at": retired_at.isoformat(),
        }
        identity.service_context = context
        identity.updated_at = retired_at

    for grant in plan.active_grants:
        if grant.resource_type != "service_identity" or grant.resource_uuid not in affected_identity_ids:
            raise RemnawaveIdentityAccessConflict("Remnawave retirement grant scope is invalid")
        issuance_reason = grant.audit_reason
        grant.revoked_at = retired_at
        grant.revoked_by_admin_user_id = None
        grant.audit_reason = _RETIREMENT_REASON
        session.add(
            AuditLog(
                admin_id=None,
                action="partner_remnawave_resource_grant.revoked_by_account_deletion",
                entity_type="partner_remnawave_resource_grant",
                entity_id=str(grant.id),
                old_value={
                    "workspace_id": str(grant.workspace_id),
                    "resource_type": grant.resource_type,
                    "resource_uuid": str(grant.resource_uuid),
                    "issuance_reason": issuance_reason,
                },
                new_value={
                    "revoked_at": retired_at.isoformat(),
                    "reason": "customer_account_deleted",
                },
            )
        )

    for reconciliation in plan.reconciliations:
        await session.delete(reconciliation)
    await session.flush()


async def assert_remnawave_service_identity_grantable(
    session: AsyncSession,
    *,
    service_identity_id: UUID,
) -> ServiceIdentityModel:
    """Serialize grant issuance with owner retirement and reject tombstones."""

    await _acquire_remnawave_identity_registry_lock(session, shared=True)
    await _acquire_remnawave_identity_dimension_locks(
        session,
        {f"remnawave-identity:subject:service_identity:{service_identity_id}"},
    )
    identity = (
        await session.execute(
            select(ServiceIdentityModel).where(ServiceIdentityModel.id == service_identity_id).with_for_update()
        )
    ).scalar_one_or_none()
    if identity is None or identity.provider_name != "remnawave" or identity.identity_status != "active":
        raise RemnawaveIdentityAccessConflict("Remnawave service identity is not grantable")
    owner = (
        await session.execute(
            select(MobileUserModel).where(MobileUserModel.id == identity.customer_account_id).with_for_update()
        )
    ).scalar_one_or_none()
    if owner is None or owner.status in {"deleting", "deleted"}:
        raise RemnawaveIdentityAccessConflict("Remnawave service identity owner is terminal")
    service_ref = _local_ref(identity.provider_numeric_subject_id, identity.provider_subject_ref)
    if service_ref is None:
        raise RemnawaveIdentityAccessConflict("Remnawave service identity is not mapped")
    rows = list(
        (
            await session.execute(
                select(RemnawaveIdentityReconciliationModel)
                .where(
                    RemnawaveIdentityReconciliationModel.subject_type == "service_identity",
                    RemnawaveIdentityReconciliationModel.subject_id == service_identity_id,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    _assert_exact_subject_ledger(
        subject_label="Service Remnawave identity",
        local_ref=service_ref,
        rows=rows,
    )
    return identity
