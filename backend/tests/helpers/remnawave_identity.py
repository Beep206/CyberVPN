"""Exact Remnawave 3.x identity fixtures for synchronous integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.remnawave_upgrade_model import RemnawaveIdentityReconciliationModel


def seed_exact_mobile_user_mapping(
    session: Session,
    customer: MobileUserModel,
    *,
    numeric_user_id: int,
    legacy_uuid: UUID | None,
    source: str,
) -> None:
    """Persist matching model fields and reconciliation-ledger evidence."""

    if isinstance(numeric_user_id, bool) or numeric_user_id <= 0:
        raise ValueError("numeric_user_id must be a positive integer")
    normalized_source = source.strip()
    if not normalized_source:
        raise ValueError("source is required")

    customer.remnawave_user_id = numeric_user_id
    customer.remnawave_uuid = str(legacy_uuid) if legacy_uuid is not None else None
    session.add(
        RemnawaveIdentityReconciliationModel(
            subject_type="mobile_user",
            subject_id=customer.id,
            legacy_uuid=customer.remnawave_uuid,
            numeric_user_id=numeric_user_id,
            reconciliation_state="mapped",
            evidence={"source": normalized_source},
            reconciled_at=datetime.now(UTC),
        )
    )
