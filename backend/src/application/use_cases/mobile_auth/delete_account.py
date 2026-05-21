"""Delete/anonymize a mobile customer account.

S1 customer account deletion must revoke VPN access and release unique login
identifiers so the same Telegram identity can register again if needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as redis
from httpx import HTTPStatusError

from src.application.services.jwt_revocation_service import JWTRevocationService
from src.domain.exceptions import UserNotFoundError
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MobileDeleteAccountResult:
    vpn_access_removed: bool
    jwt_sessions_revoked: int


class MobileDeleteAccountUseCase:
    """Revoke service access and anonymize a mobile customer account."""

    def __init__(
        self,
        *,
        user_repo: MobileUserRepository,
        user_gateway: RemnawaveUserGateway,
        redis_client: redis.Redis,
    ) -> None:
        self._user_repo = user_repo
        self._user_gateway = user_gateway
        self._redis_client = redis_client

    async def execute(self, user_id: UUID) -> MobileDeleteAccountResult:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        vpn_access_removed = False
        if user.remnawave_uuid:
            try:
                await self._user_gateway.delete(UUID(str(user.remnawave_uuid)))
                vpn_access_removed = True
            except HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                vpn_access_removed = True

        now = datetime.now(UTC)
        deleted_suffix = str(user.id).replace("-", "")
        user.email = f"deleted-{deleted_suffix}@deleted.cyber-vpn.net"
        user.password_hash = f"deleted:{deleted_suffix}"
        user.username = None
        user.telegram_subject = None
        user.telegram_id = None
        user.telegram_username = None
        user.notification_prefs = {}
        user.totp_secret = None
        user.totp_enabled = False
        user.remnawave_uuid = None
        user.subscription_url = None
        user.referral_code = None
        user.is_partner = False
        user.partner_promoted_at = None
        user.partner_account_id = None
        user.partner_user_id = None
        user.referred_by_user_id = None
        user.trial_activated_at = None
        user.trial_expires_at = None
        user.is_active = False
        user.status = "deleted"
        user.updated_at = now

        await self._user_repo.update(user)
        revoked_count = await JWTRevocationService(self._redis_client).revoke_all_user_tokens(str(user_id))

        logger.info(
            "mobile_account_deleted",
            extra={
                "user_id": str(user_id),
                "vpn_access_removed": vpn_access_removed,
                "jwt_sessions_revoked": revoked_count,
            },
        )
        return MobileDeleteAccountResult(
            vpn_access_removed=vpn_access_removed,
            jwt_sessions_revoked=revoked_count,
        )
