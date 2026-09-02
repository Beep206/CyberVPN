"""Bounded, portable reads over partner Remnawave resource grants."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.partner_permission import PartnerPermission
from src.infrastructure.database.models.remnawave_upgrade_model import PartnerRemnawaveResourceGrantModel

MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS = 10_000


def _has_read_permission(grant: PartnerRemnawaveResourceGrantModel) -> bool:
    keys = grant.permission_keys
    return isinstance(keys, list) and PartnerPermission.REMNAWAVE_READ.value in keys


async def load_readable_partner_remnawave_grants(
    *,
    db: AsyncSession,
    workspace_id: UUID,
) -> list[PartnerRemnawaveResourceGrantModel]:
    """Return active readable grants with an explicit workspace cardinality cap.

    ``permission_keys`` is a portable SQLAlchemy ``JSON`` column. Its generic
    ``contains`` comparator compiles to an invalid PostgreSQL JSON ``LIKE``
    expression, so the bounded active set is filtered by an exact allowlist in
    Python. The +1 query limit also catches a concurrent growth race.
    """

    filters = (
        PartnerRemnawaveResourceGrantModel.workspace_id == workspace_id,
        PartnerRemnawaveResourceGrantModel.revoked_at.is_(None),
    )
    active_count = int(
        (await db.execute(select(func.count(PartnerRemnawaveResourceGrantModel.id)).where(*filters))).scalar_one()
    )
    if active_count > MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Remnawave resource inventory exceeds safe limit",
        )

    active_grants = list(
        (
            await db.execute(
                select(PartnerRemnawaveResourceGrantModel)
                .where(*filters)
                .order_by(
                    PartnerRemnawaveResourceGrantModel.resource_type.asc(),
                    PartnerRemnawaveResourceGrantModel.resource_uuid.asc(),
                )
                .limit(MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS + 1)
            )
        )
        .scalars()
        .all()
    )
    if len(active_grants) > MAX_ACTIVE_PARTNER_REMNAWAVE_GRANTS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Remnawave resource inventory exceeds safe limit",
        )
    return [grant for grant in active_grants if _has_read_permission(grant)]
