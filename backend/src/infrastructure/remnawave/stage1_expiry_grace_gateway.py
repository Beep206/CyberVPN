"""Remnawave gateway for Stage 1 expiry/grace disable operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_remnawave_ref,
)
from src.application.use_cases.subscriptions.stage1_expiry_grace_disable import (
    Stage1ExpiryGraceAccessRecord,
    Stage1ExpiryGraceDisableResult,
    Stage1ExpiryGraceError,
)
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class RemnawaveStage1ExpiryGraceGateway:
    """Disable Remnawave users after the S1 expiry/grace policy permits it."""

    def __init__(self, user_gateway: RemnawaveUserGateway, *, session: AsyncSession) -> None:
        self._user_gateway = user_gateway
        self._session = session

    async def disable_expired_access(
        self,
        record: Stage1ExpiryGraceAccessRecord,
        *,
        disabled_at: datetime,
    ) -> Stage1ExpiryGraceDisableResult:
        try:
            target = await resolve_exact_mapped_remnawave_ref(
                self._session,
                subject_type="mobile_user",
                subject_id=record.customer_account_id,
                numeric_user_id=record.remnawave_user_id,
                legacy_uuid_raw=record.remnawave_uuid,
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise Stage1ExpiryGraceError("Cannot disable access without an exact mapped identity") from exc
        if target is None:
            raise Stage1ExpiryGraceError("Cannot disable expired access without Remnawave identity")
        user = await self._user_gateway.update(target, status=UserStatus.DISABLED)
        status = user.status if isinstance(user.status, UserStatus) else UserStatus(str(user.status).lower())
        return Stage1ExpiryGraceDisableResult(
            customer_account_id=record.customer_account_id,
            remnawave_uuid=str(user.uuid) if user.uuid is not None else record.remnawave_uuid,
            status=status,
            disabled_at=disabled_at,
            remnawave_user_id=getattr(user, "remnawave_id", None),
        )
