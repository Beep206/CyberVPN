from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.services.remnawave_identity_access import RemnawaveIdentityAccessConflict
from src.application.services.remnawave_identity_retirement import (
    RemnawaveOwnerIdentityRetirementPlan,
    _validate_owner_bindings,
    apply_remnawave_owner_identity_retirement,
)
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.remnawave_upgrade_model import (
    PartnerRemnawaveResourceGrantModel,
    RemnawaveIdentityReconciliationModel,
)


def _ledger(*, subject_type: str, subject_id, numeric_id: int, legacy_uuid) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        subject_type=subject_type,
        subject_id=subject_id,
        numeric_user_id=numeric_id,
        legacy_uuid=str(legacy_uuid) if legacy_uuid is not None else None,
        reconciliation_state="mapped",
    )


def _owner_pair(*, service_numeric_id: int = 73, service_legacy_uuid=None):
    customer_id = uuid4()
    service_id = uuid4()
    mobile_legacy_uuid = uuid4()
    service_legacy_uuid = service_legacy_uuid or mobile_legacy_uuid
    customer = SimpleNamespace(
        id=customer_id,
        remnawave_user_id=73,
        remnawave_uuid=str(mobile_legacy_uuid),
    )
    service_identity = SimpleNamespace(
        id=service_id,
        customer_account_id=customer_id,
        provider_name="remnawave",
        provider_numeric_subject_id=service_numeric_id,
        provider_subject_ref=str(service_legacy_uuid),
        identity_status="active",
        service_context={},
        updated_at=None,
    )
    rows = [
        _ledger(
            subject_type="mobile_user",
            subject_id=customer_id,
            numeric_id=73,
            legacy_uuid=mobile_legacy_uuid,
        ),
        _ledger(
            subject_type="service_identity",
            subject_id=service_id,
            numeric_id=service_numeric_id,
            legacy_uuid=service_legacy_uuid,
        ),
    ]
    return customer, service_identity, rows


@pytest.mark.unit
def test_owner_retirement_accepts_only_exact_same_owner_provider_alias() -> None:
    customer, service_identity, rows = _owner_pair()

    result = _validate_owner_bindings(
        customer=customer,
        service_identities=[service_identity],
        reconciliations=rows,
    )

    assert len(result) == 1
    assert result[0].require_numeric_id() == 73


@pytest.mark.unit
@pytest.mark.parametrize("collision", ["numeric", "legacy"])
def test_owner_retirement_rejects_partial_provider_pair_collision(collision: str) -> None:
    legacy_uuid = uuid4() if collision == "legacy" else None
    numeric_id = 74 if collision == "numeric" else 73
    customer, service_identity, rows = _owner_pair(
        service_numeric_id=numeric_id,
        service_legacy_uuid=legacy_uuid,
    )

    with pytest.raises(RemnawaveIdentityAccessConflict, match="provider pairs are inconsistent"):
        _validate_owner_bindings(
            customer=customer,
            service_identities=[service_identity],
            reconciliations=rows,
        )


@pytest.mark.unit
def test_owner_retirement_inventories_fully_distinct_subscription_provider_pair() -> None:
    customer, service_identity, rows = _owner_pair(
        service_numeric_id=74,
        service_legacy_uuid=uuid4(),
    )
    refs = _validate_owner_bindings(
        customer=customer,
        service_identities=[service_identity],
        reconciliations=rows,
    )

    assert len(refs) == 2


@pytest.mark.unit
def test_owner_retirement_rejects_mapped_ledger_without_local_binding() -> None:
    customer_id = uuid4()
    customer = SimpleNamespace(id=customer_id, remnawave_user_id=None, remnawave_uuid=None)
    row = _ledger(
        subject_type="mobile_user",
        subject_id=customer_id,
        numeric_id=73,
        legacy_uuid=uuid4(),
    )

    with pytest.raises(RemnawaveIdentityAccessConflict, match="without a local binding"):
        _validate_owner_bindings(
            customer=customer,
            service_identities=[],
            reconciliations=[row],
        )


class _ApplySession:
    def __init__(self) -> None:
        self.deleted = []
        self.added = []
        self.flushes = 0

    def add(self, value) -> None:
        self.added.append(value)

    async def delete(self, value) -> None:
        self.deleted.append(value)

    async def flush(self) -> None:
        self.flushes += 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_owner_retirement_revokes_alias_grant_and_removes_ledger_atomically() -> None:
    customer, service_identity, rows = _owner_pair()
    grant = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        resource_type="service_identity",
        resource_uuid=service_identity.id,
        revoked_at=None,
        revoked_by_admin_user_id=uuid4(),
        audit_reason="Initial grant",
    )
    session = _ApplySession()
    retired_at = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    plan = RemnawaveOwnerIdentityRetirementPlan(
        customer=customer,
        user_ref=None,
        provider_refs=(),
        service_identities=(service_identity,),
        reconciliations=tuple(rows),
        active_grants=(grant,),
    )

    await apply_remnawave_owner_identity_retirement(session, plan=plan, retired_at=retired_at)

    assert service_identity.identity_status == "revoked"
    assert service_identity.provider_numeric_subject_id is None
    assert service_identity.provider_subject_ref is None
    assert service_identity.service_context["remnawave_identity_retirement"] == {
        "reason": "customer_account_deleted",
        "retired_at": retired_at.isoformat(),
    }
    assert grant.revoked_at == retired_at
    assert grant.revoked_by_admin_user_id is None
    assert grant.audit_reason == "Owning customer account deleted"
    assert session.deleted == rows
    assert len(session.added) == 1
    audit = session.added[0]
    assert isinstance(audit, AuditLog)
    assert audit.admin_id is None
    assert audit.action == "partner_remnawave_resource_grant.revoked_by_account_deletion"
    assert audit.old_value["issuance_reason"] == "Initial grant"
    assert session.flushes == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_owner_retirement_rejects_grant_outside_locked_service_scope() -> None:
    customer, service_identity, rows = _owner_pair()
    foreign_grant = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        resource_type="service_identity",
        resource_uuid=uuid4(),
        revoked_at=None,
        revoked_by_admin_user_id=None,
        audit_reason="Initial grant",
    )
    plan = RemnawaveOwnerIdentityRetirementPlan(
        customer=customer,
        user_ref=None,
        provider_refs=(),
        service_identities=(service_identity,),
        reconciliations=tuple(rows),
        active_grants=(foreign_grant,),
    )

    with pytest.raises(RemnawaveIdentityAccessConflict, match="grant scope"):
        await apply_remnawave_owner_identity_retirement(
            _ApplySession(),
            plan=plan,
            retired_at=datetime.now(UTC),
        )

    assert foreign_grant.revoked_at is None


assert PartnerRemnawaveResourceGrantModel.__tablename__ == "partner_remnawave_resource_grants"
assert RemnawaveIdentityReconciliationModel.__tablename__ == "remnawave_identity_reconciliations"
