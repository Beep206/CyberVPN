"""Remnawave gateway for Stage 1 VPN credential regeneration."""

from __future__ import annotations

from uuid import UUID

from src.application.use_cases.subscriptions.stage1_credential_regeneration import (
    Stage1CredentialRegenerationError,
    Stage1CredentialRegenerationRequest,
    Stage1CredentialRegenerationResult,
)
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class RemnawaveStage1CredentialRegenerationGateway:
    """Rotate Remnawave subscription credentials for S1 admin/support operations."""

    def __init__(self, user_gateway: RemnawaveUserGateway) -> None:
        self._user_gateway = user_gateway

    async def regenerate_credentials(
        self,
        request: Stage1CredentialRegenerationRequest,
    ) -> Stage1CredentialRegenerationResult:
        try:
            remnawave_uuid = UUID(request.remnawave_uuid)
        except ValueError as exc:
            raise Stage1CredentialRegenerationError("Existing Remnawave UUID is invalid") from exc

        user = await self._user_gateway.revoke_subscription(
            remnawave_uuid,
            revoke_only_passwords=request.revoke_only_passwords,
        )
        subscription_url_changed = bool(
            user.subscription_url and request.previous_subscription_url != user.subscription_url
        )

        return Stage1CredentialRegenerationResult(
            customer_account_id=request.customer_account_id,
            remnawave_uuid=str(user.uuid),
            status=user.status.value.lower() if hasattr(user.status, "value") else str(user.status).lower(),
            regenerated_at=request.requested_at,
            previous_short_uuid=request.previous_short_uuid,
            current_short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            subscription_url_changed=subscription_url_changed,
            revoke_only_passwords=request.revoke_only_passwords,
            expires_at=user.expires_at,
        )
