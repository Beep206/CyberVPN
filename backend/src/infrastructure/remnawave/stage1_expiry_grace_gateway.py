"""Remnawave gateway for Stage 1 expiry/grace disable operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.use_cases.subscriptions.stage1_expiry_grace_disable import (
    Stage1ExpiryGraceAccessRecord,
    Stage1ExpiryGraceDisableResult,
    Stage1ExpiryGraceError,
)
from src.domain.enums import UserStatus
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class RemnawaveStage1ExpiryGraceGateway:
    """Disable Remnawave users after the S1 expiry/grace policy permits it."""

    def __init__(self, user_gateway: RemnawaveUserGateway) -> None:
        self._user_gateway = user_gateway

    async def disable_expired_access(
        self,
        record: Stage1ExpiryGraceAccessRecord,
        *,
        disabled_at: datetime,
    ) -> Stage1ExpiryGraceDisableResult:
        if record.remnawave_uuid is None:
            raise Stage1ExpiryGraceError("Cannot disable expired access without Remnawave UUID")
        try:
            remnawave_uuid = UUID(record.remnawave_uuid)
        except ValueError as exc:
            raise Stage1ExpiryGraceError("Cannot disable expired access with invalid Remnawave UUID") from exc

        user = await self._user_gateway.update(remnawave_uuid, status=UserStatus.DISABLED)
        status = user.status if isinstance(user.status, UserStatus) else UserStatus(str(user.status).lower())
        return Stage1ExpiryGraceDisableResult(
            customer_account_id=record.customer_account_id,
            remnawave_uuid=str(user.uuid),
            status=status,
            disabled_at=disabled_at,
        )
