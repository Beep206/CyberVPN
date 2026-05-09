"""Stage 1 credential regeneration contract for Remnawave-backed VPN access."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from src.application.use_cases.auth.permissions import Permission, has_permission
from src.domain.enums import AdminRole

STAGE1_CREDENTIAL_REGENERATION_ACTION = "customer_vpn_credentials_regenerated"


class Stage1CredentialRegenerationError(RuntimeError):
    """Raised when S1 VPN credential regeneration cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class Stage1CredentialRegenerationRequest:
    """Provider-neutral request for S1 VPN credential regeneration."""

    customer_account_id: UUID
    remnawave_uuid: str
    actor_admin_id: UUID
    reason: str
    requested_at: datetime
    previous_short_uuid: str | None = None
    previous_subscription_url: str | None = None
    revoke_only_passwords: bool = False


@dataclass(frozen=True, slots=True)
class Stage1CredentialRegenerationResult:
    """Safe result of S1 VPN credential regeneration."""

    customer_account_id: UUID
    remnawave_uuid: str
    status: str
    regenerated_at: datetime
    previous_short_uuid: str | None
    current_short_uuid: str | None
    subscription_url: str | None
    subscription_url_changed: bool
    revoke_only_passwords: bool
    expires_at: datetime | None = None
    provider_name: str = "remnawave"

    @property
    def short_uuid_changed(self) -> bool:
        """Return whether Remnawave rotated the subscription short UUID."""

        return bool(
            self.current_short_uuid
            and self.previous_short_uuid
            and self.current_short_uuid != self.previous_short_uuid
        )

    def to_safe_dict(self) -> dict[str, str | bool | None]:
        """Serialize metadata without leaking subscription URLs or protocol secrets."""

        return {
            "customer_account_id": str(self.customer_account_id),
            "remnawave_uuid": self.remnawave_uuid,
            "status": self.status,
            "regenerated_at": self.regenerated_at.isoformat(),
            "short_uuid_changed": self.short_uuid_changed,
            "subscription_url_changed": self.subscription_url_changed,
            "revoke_only_passwords": self.revoke_only_passwords,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "provider_name": self.provider_name,
        }

    def to_audit_details(self, *, reason: str) -> dict[str, str | bool | int | None]:
        """Return audit metadata with reason length only and no raw config links."""

        return {
            **self.to_safe_dict(),
            "reason_length": len(reason.strip()),
            "audit_action": STAGE1_CREDENTIAL_REGENERATION_ACTION,
        }


class Stage1CredentialRegenerationGateway(Protocol):
    """Gateway implemented by Remnawave adapters or tests."""

    async def regenerate_credentials(
        self,
        request: Stage1CredentialRegenerationRequest,
    ) -> Stage1CredentialRegenerationResult:
        """Rotate upstream VPN credentials for a customer."""


def can_regenerate_stage1_credentials(role: AdminRole) -> bool:
    """Return whether an admin role may rotate customer VPN credentials."""

    return has_permission(role, Permission.VPN_CREDENTIAL_REGENERATE)


def require_stage1_credential_regeneration_role(role: AdminRole) -> None:
    """Raise if the role is not allowed to rotate customer VPN credentials."""

    if not can_regenerate_stage1_credentials(role):
        raise Stage1CredentialRegenerationError("VPN credential regeneration requires admin/support permission")


class Stage1CredentialRegenerationService:
    """Coordinates S1 credential rotation through an injected gateway."""

    def __init__(self, gateway: Stage1CredentialRegenerationGateway) -> None:
        self._gateway = gateway

    async def regenerate(
        self,
        request: Stage1CredentialRegenerationRequest,
    ) -> Stage1CredentialRegenerationResult:
        """Regenerate credentials and validate the returned safe contract."""

        _validate_request(request)
        result = await self._gateway.regenerate_credentials(request)
        if result.customer_account_id != request.customer_account_id:
            raise Stage1CredentialRegenerationError("Credential gateway returned an unexpected customer")
        if result.remnawave_uuid != request.remnawave_uuid:
            raise Stage1CredentialRegenerationError("Credential gateway returned an unexpected Remnawave UUID")
        if not result.current_short_uuid and not request.revoke_only_passwords:
            raise Stage1CredentialRegenerationError("Full credential regeneration returned no short UUID")
        return result


def build_stage1_credential_regeneration_request(
    *,
    customer_account_id: UUID,
    remnawave_uuid: str,
    actor_admin_id: UUID,
    reason: str,
    previous_short_uuid: str | None = None,
    previous_subscription_url: str | None = None,
    revoke_only_passwords: bool = False,
    requested_at: datetime | None = None,
) -> Stage1CredentialRegenerationRequest:
    """Build and validate the S1 credential regeneration request."""

    request = Stage1CredentialRegenerationRequest(
        customer_account_id=customer_account_id,
        remnawave_uuid=remnawave_uuid,
        actor_admin_id=actor_admin_id,
        reason=reason,
        requested_at=_ensure_aware_utc(requested_at or datetime.now(UTC)),
        previous_short_uuid=previous_short_uuid,
        previous_subscription_url=previous_subscription_url,
        revoke_only_passwords=revoke_only_passwords,
    )
    _validate_request(request)
    return request


def _validate_request(request: Stage1CredentialRegenerationRequest) -> None:
    reason = request.reason.strip()
    if len(reason) < 3:
        raise Stage1CredentialRegenerationError("Credential regeneration requires an operator reason")
    if len(reason) > 1000:
        raise Stage1CredentialRegenerationError("Credential regeneration reason is too long")
    try:
        UUID(request.remnawave_uuid)
    except ValueError as exc:
        raise Stage1CredentialRegenerationError("Credential regeneration requires a valid Remnawave UUID") from exc


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
