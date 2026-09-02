"""Fail-closed access to canonical Remnawave 3.x user identities."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel
from src.infrastructure.database.models.service_identity_model import ServiceIdentityModel

RemnawaveReconciliationSubjectType = Literal["mobile_user", "service_identity"]


class RemnawaveIdentityAccessConflict(RuntimeError):
    """The local subject does not have one exact, mapped 3.x identity."""


async def resolve_exact_mapped_mobile_user_ref(
    session: AsyncSession | None,
    customer: object,
) -> RemnawaveUserRef | None:
    """Resolve a persisted mobile customer through the cutover ledger only."""

    numeric_user_id = getattr(customer, "remnawave_user_id", None)
    legacy_uuid_raw = getattr(customer, "remnawave_uuid", None)
    if numeric_user_id is None and (legacy_uuid_raw is None or legacy_uuid_raw == ""):
        return None
    if session is None:
        raise RemnawaveIdentityAccessConflict("A database session is required for Remnawave identity access")
    subject_id = getattr(customer, "id", None)
    if not isinstance(subject_id, UUID):
        raise RemnawaveIdentityAccessConflict("Remnawave identity subject is invalid")
    return await resolve_exact_mapped_remnawave_ref(
        session,
        subject_type="mobile_user",
        subject_id=subject_id,
        numeric_user_id=numeric_user_id,
        legacy_uuid_raw=legacy_uuid_raw,
    )


_RUNTIME_MAPPING_SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{2,79}$")


def _normalize_runtime_identity(*, numeric_user_id: object, legacy_uuid_raw: object) -> RemnawaveUserRef:
    if isinstance(numeric_user_id, bool) or not isinstance(numeric_user_id, int) or numeric_user_id <= 0:
        raise RemnawaveIdentityAccessConflict("Remnawave numeric identity is incomplete")
    legacy_uuid = _parse_optional_legacy_uuid(legacy_uuid_raw)
    return RemnawaveUserRef(id=numeric_user_id, legacy_uuid=legacy_uuid)


def _parse_optional_legacy_uuid(legacy_uuid_raw: object) -> UUID | None:
    if legacy_uuid_raw is None or legacy_uuid_raw == "":
        return None
    try:
        return UUID(str(legacy_uuid_raw))
    except (TypeError, ValueError) as exc:
        raise RemnawaveIdentityAccessConflict("Remnawave rollback reference is invalid") from exc


def _normalize_mapping_source(source: str) -> str:
    normalized = source.strip().lower()
    if not _RUNTIME_MAPPING_SOURCE_RE.fullmatch(normalized):
        raise ValueError("Remnawave mapping source must be a safe 3-80 character identifier")
    return normalized


def _assert_local_binding_is_empty_or_exact(
    *,
    current_numeric_user_id: object,
    current_legacy_uuid_raw: object,
    target: RemnawaveUserRef,
) -> RemnawaveUserRef:
    if current_numeric_user_id is None and (current_legacy_uuid_raw is None or current_legacy_uuid_raw == ""):
        return target

    current_legacy_uuid = _parse_optional_legacy_uuid(current_legacy_uuid_raw)
    if current_numeric_user_id is None:
        if target.legacy_uuid is None or current_legacy_uuid != target.legacy_uuid:
            raise RemnawaveIdentityAccessConflict("Local Remnawave identity conflicts with the runtime identity")
        return target

    current = _normalize_runtime_identity(
        numeric_user_id=current_numeric_user_id,
        legacy_uuid_raw=current_legacy_uuid,
    )
    if current.require_numeric_id() != target.require_numeric_id() or (
        current.legacy_uuid is not None and target.legacy_uuid is not None and current.legacy_uuid != target.legacy_uuid
    ):
        raise RemnawaveIdentityAccessConflict("Local Remnawave identity conflicts with the runtime identity")
    return RemnawaveUserRef(
        id=target.require_numeric_id(),
        legacy_uuid=current.legacy_uuid or target.legacy_uuid,
    )


async def _acquire_runtime_mapping_locks(
    session: AsyncSession,
    *,
    subject_type: RemnawaveReconciliationSubjectType,
    subject_id: UUID,
    numeric_user_id: int,
    legacy_uuid: UUID | None,
) -> None:
    """Serialize new subject/provider mappings on PostgreSQL.

    The reconciliation table has subject, mapped-numeric and mapped-legacy
    uniqueness constraints per subject type. Advisory transaction locks cover
    the otherwise-unlockable "row absent" dimensions globally across subject
    types, while database constraints remain the final same-type guard.
    """

    await _acquire_remnawave_identity_registry_lock(session, shared=True)
    scopes = [
        f"remnawave-identity:subject:{subject_type}:{subject_id}",
        f"remnawave-identity:numeric:{numeric_user_id}",
    ]
    if legacy_uuid is not None:
        scopes.append(f"remnawave-identity:legacy:{legacy_uuid}")
    await _acquire_remnawave_identity_dimension_locks(session, scopes)


async def _acquire_remnawave_identity_dimension_locks(
    session: AsyncSession,
    scopes: list[str] | set[str],
) -> None:
    """Acquire canonical identity dimensions after the registry lock.

    Callers must acquire the shared or exclusive registry lock first. Keeping
    this second-stage ordering common to mapping and retirement prevents a
    provider identity from being rebound while its owner is being deleted.
    """

    get_bind = getattr(session, "get_bind", None)
    if not callable(get_bind):
        return
    bind = get_bind()
    if getattr(getattr(bind, "dialect", None), "name", "") != "postgresql":
        return

    lock_ids = sorted(
        int.from_bytes(hashlib.blake2b(scope.encode("utf-8"), digest_size=8).digest(), "big", signed=True)
        for scope in set(scopes)
    )
    for lock_id in lock_ids:
        await session.execute(text("select pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})


async def _acquire_remnawave_identity_registry_lock(
    session: AsyncSession,
    *,
    shared: bool = False,
) -> None:
    """Coordinate concurrent runtime writes with reconciliation replacement."""

    get_bind = getattr(session, "get_bind", None)
    if not callable(get_bind):
        return
    bind = get_bind()
    if getattr(getattr(bind, "dialect", None), "name", "") != "postgresql":
        return
    scope = "remnawave-identity:registry"
    lock_id = int.from_bytes(
        hashlib.blake2b(scope.encode("utf-8"), digest_size=8).digest(),
        "big",
        signed=True,
    )
    statement = (
        text("select pg_advisory_xact_lock_shared(:lock_id)")
        if shared
        else text("select pg_advisory_xact_lock(:lock_id)")
    )
    await session.execute(statement, {"lock_id": lock_id})


async def _load_service_identity_owners(
    session: AsyncSession,
    subject_ids: set[UUID],
) -> dict[UUID, UUID]:
    if not subject_ids:
        return {}
    result = await session.execute(
        select(ServiceIdentityModel.id, ServiceIdentityModel.customer_account_id)
        .where(ServiceIdentityModel.id.in_(subject_ids))
        .with_for_update()
    )
    return {subject_id: customer_account_id for subject_id, customer_account_id in result.all()}


async def _assert_customer_identity_lifecycle_allows_mapping(
    session: AsyncSession,
    customer_account_id: UUID,
) -> None:
    """Reject a stale post-provider mapping after account deletion won.

    Runtime mapping is authoritative on PostgreSQL. The owner row is read only
    after the shared registry/dimension locks, so an ORM object loaded before a
    concurrent deletion cannot resurrect a terminal customer.
    """

    get_bind = getattr(session, "get_bind", None)
    if not callable(get_bind):
        return
    bind = get_bind()
    if getattr(getattr(bind, "dialect", None), "name", "") != "postgresql":
        return
    result = await session.execute(
        select(MobileUserModel.status).where(MobileUserModel.id == customer_account_id).with_for_update()
    )
    status = result.scalar_one_or_none()
    if status in {None, "deleting", "deleted"}:
        raise RemnawaveIdentityAccessConflict("Remnawave identity owner is terminal")


async def _assert_cross_type_aliases_are_same_owner(
    session: AsyncSession,
    *,
    subject_type: RemnawaveReconciliationSubjectType,
    subject_id: UUID,
    customer_account_id: UUID,
    numeric_user_id: int,
    legacy_uuid: UUID | None,
    candidates: list[RemnawaveIdentityReconciliationModel],
) -> None:
    aliases = [row for row in candidates if not (row.subject_type == subject_type and row.subject_id == subject_id)]
    if not aliases:
        return
    if any(row.subject_type == subject_type for row in aliases):
        raise RemnawaveIdentityAccessConflict("Remnawave identity is already mapped to another subject")
    if any(row.subject_type not in ("mobile_user", "service_identity") for row in aliases):
        raise RemnawaveIdentityAccessConflict("Remnawave identity has an unknown reconciliation owner")

    service_subject_ids = {row.subject_id for row in aliases if row.subject_type == "service_identity"}
    if subject_type == "service_identity":
        service_subject_ids.add(subject_id)
    service_owners = await _load_service_identity_owners(session, service_subject_ids)
    if subject_type == "service_identity" and service_owners.get(subject_id) != customer_account_id:
        raise RemnawaveIdentityAccessConflict("Remnawave identity subject owner is invalid")

    for row in aliases:
        alias_owner = row.subject_id if row.subject_type == "mobile_user" else service_owners.get(row.subject_id)
        if alias_owner is None or alias_owner != customer_account_id:
            raise RemnawaveIdentityAccessConflict(
                "Remnawave identity is already mapped to a different customer account"
            )
        if row.reconciliation_state != "mapped" or row.numeric_user_id != numeric_user_id:
            raise RemnawaveIdentityAccessConflict("Remnawave cross-type identity alias is inconsistent")
        if _parse_optional_legacy_uuid(row.legacy_uuid) != legacy_uuid:
            raise RemnawaveIdentityAccessConflict("Remnawave cross-type identity alias is inconsistent")


async def _persist_runtime_mapping(
    session: AsyncSession,
    *,
    subject_type: RemnawaveReconciliationSubjectType,
    subject_id: UUID,
    customer_account_id: UUID,
    numeric_user_id: object,
    legacy_uuid_raw: object,
    source: str,
) -> RemnawaveUserRef:
    """Create or verify one exact mapped ledger row in the caller transaction."""

    user_ref = _normalize_runtime_identity(
        numeric_user_id=numeric_user_id,
        legacy_uuid_raw=legacy_uuid_raw,
    )
    numeric_id = user_ref.require_numeric_id()
    legacy_uuid = user_ref.legacy_uuid
    normalized_source = _normalize_mapping_source(source)
    await _acquire_runtime_mapping_locks(
        session,
        subject_type=subject_type,
        subject_id=subject_id,
        numeric_user_id=numeric_id,
        legacy_uuid=legacy_uuid,
    )
    await _assert_customer_identity_lifecycle_allows_mapping(session, customer_account_id)

    identity_filters = [
        and_(
            RemnawaveIdentityReconciliationModel.subject_type == subject_type,
            RemnawaveIdentityReconciliationModel.subject_id == subject_id,
        ),
        RemnawaveIdentityReconciliationModel.numeric_user_id == numeric_id,
    ]
    if legacy_uuid is not None:
        identity_filters.append(
            func.lower(func.trim(RemnawaveIdentityReconciliationModel.legacy_uuid)) == str(legacy_uuid)
        )

    result = await session.execute(
        select(RemnawaveIdentityReconciliationModel).where(or_(*identity_filters)).with_for_update()
    )
    candidates = list(result.scalars().all())
    subject_rows = [row for row in candidates if row.subject_type == subject_type and row.subject_id == subject_id]
    if len(subject_rows) > 1:
        raise RemnawaveIdentityAccessConflict("Remnawave reconciliation is not unique")
    await _assert_cross_type_aliases_are_same_owner(
        session,
        subject_type=subject_type,
        subject_id=subject_id,
        customer_account_id=customer_account_id,
        numeric_user_id=numeric_id,
        legacy_uuid=legacy_uuid,
        candidates=candidates,
    )

    now = datetime.now(UTC)
    reconciliation = subject_rows[0] if subject_rows else None
    if reconciliation is None:
        reconciliation = RemnawaveIdentityReconciliationModel(
            id=uuid.uuid4(),
            subject_type=subject_type,
            subject_id=subject_id,
            legacy_uuid=str(legacy_uuid) if legacy_uuid is not None else None,
            numeric_user_id=numeric_id,
            reconciliation_state="mapped",
            evidence={
                "source": normalized_source,
                "customer_account_id": str(customer_account_id),
                "matched_by": "runtime_provider_response",
                "legacy_uuid_observed": legacy_uuid is not None,
                "provider_auto_renew_authoritative": False,
                "backend_auto_renew_consent_preserved": True,
            },
            reconciled_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(reconciliation)
    else:
        if reconciliation.reconciliation_state != "mapped" or reconciliation.numeric_user_id != numeric_id:
            raise RemnawaveIdentityAccessConflict("Remnawave reconciliation conflicts with the runtime identity")
        reconciled_legacy_uuid = _parse_optional_legacy_uuid(reconciliation.legacy_uuid)
        if reconciled_legacy_uuid != legacy_uuid:
            raise RemnawaveIdentityAccessConflict("Remnawave reconciliation conflicts with the runtime identity")
        legacy_uuid = reconciled_legacy_uuid

    await session.flush()
    return RemnawaveUserRef(id=numeric_id, legacy_uuid=legacy_uuid)


async def persist_runtime_mapped_mobile_identity(
    session: AsyncSession,
    *,
    customer: MobileUserModel,
    remnawave_user_id: object,
    remnawave_uuid: object,
    source: str,
) -> RemnawaveUserRef:
    """Persist a mobile identity and its mapped ledger row atomically."""

    target = _normalize_runtime_identity(
        numeric_user_id=remnawave_user_id,
        legacy_uuid_raw=remnawave_uuid,
    )
    target = _assert_local_binding_is_empty_or_exact(
        current_numeric_user_id=customer.remnawave_user_id,
        current_legacy_uuid_raw=customer.remnawave_uuid,
        target=target,
    )
    user_ref = await _persist_runtime_mapping(
        session,
        subject_type="mobile_user",
        subject_id=customer.id,
        customer_account_id=customer.id,
        numeric_user_id=target.require_numeric_id(),
        legacy_uuid_raw=target.legacy_uuid,
        source=source,
    )
    customer.remnawave_user_id = user_ref.require_numeric_id()
    customer.remnawave_uuid = str(user_ref.legacy_uuid) if user_ref.legacy_uuid is not None else None
    await session.flush()
    return user_ref


async def persist_runtime_mapped_service_identity(
    session: AsyncSession,
    *,
    service_identity: ServiceIdentityModel,
    remnawave_user_id: object,
    remnawave_uuid: object,
    source: str,
) -> RemnawaveUserRef:
    """Persist a service identity and its mapped ledger row atomically."""

    if service_identity.provider_name != "remnawave":
        raise ValueError("Runtime Remnawave mapping requires a Remnawave service identity")
    customer_account_id = service_identity.customer_account_id
    if not isinstance(customer_account_id, UUID):
        raise RemnawaveIdentityAccessConflict("Remnawave identity subject owner is invalid")
    target = _normalize_runtime_identity(
        numeric_user_id=remnawave_user_id,
        legacy_uuid_raw=remnawave_uuid,
    )
    target = _assert_local_binding_is_empty_or_exact(
        current_numeric_user_id=service_identity.provider_numeric_subject_id,
        current_legacy_uuid_raw=service_identity.provider_subject_ref,
        target=target,
    )
    user_ref = await _persist_runtime_mapping(
        session,
        subject_type="service_identity",
        subject_id=service_identity.id,
        customer_account_id=customer_account_id,
        numeric_user_id=target.require_numeric_id(),
        legacy_uuid_raw=target.legacy_uuid,
        source=source,
    )
    service_identity.provider_numeric_subject_id = user_ref.require_numeric_id()
    service_identity.provider_subject_ref = str(user_ref.legacy_uuid) if user_ref.legacy_uuid is not None else None
    await session.flush()
    return user_ref


async def resolve_exact_mapped_remnawave_ref(
    session: AsyncSession,
    *,
    subject_type: RemnawaveReconciliationSubjectType,
    subject_id: UUID,
    numeric_user_id: object,
    legacy_uuid_raw: object,
) -> RemnawaveUserRef | None:
    """Return a numeric ref only when the cutover ledger exactly matches.

    A subject with no provider identity returns ``None``. Partial, pending,
    duplicate, or conflicting identities are security failures. Legacy UUID
    and Telegram searches belong only in an explicitly selected rollback
    adapter and are intentionally unavailable here.
    """

    if numeric_user_id is None and (legacy_uuid_raw is None or legacy_uuid_raw == ""):
        return None
    user_ref = _normalize_runtime_identity(
        numeric_user_id=numeric_user_id,
        legacy_uuid_raw=legacy_uuid_raw,
    )
    numeric_id = user_ref.require_numeric_id()
    local_legacy_uuid = user_ref.legacy_uuid

    identity_filters = [
        and_(
            RemnawaveIdentityReconciliationModel.subject_type == subject_type,
            RemnawaveIdentityReconciliationModel.subject_id == subject_id,
        ),
        RemnawaveIdentityReconciliationModel.numeric_user_id == numeric_id,
    ]
    if local_legacy_uuid is not None:
        identity_filters.append(
            func.lower(func.trim(RemnawaveIdentityReconciliationModel.legacy_uuid)) == str(local_legacy_uuid)
        )
    result = await session.execute(select(RemnawaveIdentityReconciliationModel).where(or_(*identity_filters)))
    candidates = list(result.scalars().all())
    subject_rows = [row for row in candidates if row.subject_type == subject_type and row.subject_id == subject_id]
    if len(subject_rows) > 1:
        raise RemnawaveIdentityAccessConflict("Remnawave reconciliation is not unique")
    reconciliation = subject_rows[0] if subject_rows else None
    if (
        reconciliation is None
        or reconciliation.reconciliation_state != "mapped"
        or reconciliation.numeric_user_id != numeric_id
    ):
        raise RemnawaveIdentityAccessConflict("Remnawave reconciliation is incomplete")
    reconciled_legacy_uuid = _parse_optional_legacy_uuid(reconciliation.legacy_uuid)
    if reconciled_legacy_uuid != local_legacy_uuid:
        raise RemnawaveIdentityAccessConflict("Remnawave reconciliation conflicts with the local subject")
    if not any(row.subject_type != subject_type or row.subject_id != subject_id for row in candidates):
        return user_ref
    if subject_type == "service_identity":
        owners = await _load_service_identity_owners(session, {subject_id})
        customer_account_id = owners.get(subject_id)
        if customer_account_id is None:
            raise RemnawaveIdentityAccessConflict("Remnawave identity subject owner is invalid")
    else:
        customer_account_id = subject_id
    await _assert_cross_type_aliases_are_same_owner(
        session,
        subject_type=subject_type,
        subject_id=subject_id,
        customer_account_id=customer_account_id,
        numeric_user_id=numeric_id,
        legacy_uuid=local_legacy_uuid,
        candidates=candidates,
    )
    return user_ref
