from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from httpx import HTTPStatusError, RequestError
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.remnawave_identity_access import (
    RemnawaveIdentityAccessConflict,
    resolve_exact_mapped_remnawave_ref,
)
from src.application.services.vpn_product_readiness import (
    SMART_RU_PRODUCT_CODE,
    SPB_DE_EXCEPTIONS_PRODUCT_CODE,
    VpnProductReadinessError,
    ensure_spb_de_exceptions_data_plane_ready,
    resolve_gateway_product_plan_code,
)
from src.config.settings import settings
from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository
from src.infrastructure.remnawave.client import RemnawaveClient

SHORT_UUID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
SUPPORTED_PRODUCT_CODES = frozenset({SMART_RU_PRODUCT_CODE, SPB_DE_EXCEPTIONS_PRODUCT_CODE})
EXTERNAL_SQUAD_MISMATCH_REASON = "subscription_gateway_external_squad_mismatch"
EXTERNAL_SQUAD_UNCONFIGURED_REASON = "subscription_gateway_external_squad_unconfigured"
PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY = "premium_smart_ru_xray_failover_canary"


class SubscriptionGatewayNotFoundError(Exception):
    """The public token has no active, unambiguous CyberVPN product."""


class SubscriptionGatewayUnavailableError(Exception):
    """The authoritative subscription lookup cannot be completed safely."""

    def __init__(self, reason: str = "subscription_gateway_unavailable") -> None:
        self.reason = reason
        super().__init__(reason)


class _RemnawaveUser(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: StrictInt = Field(gt=0)
    uuid: str | None = None
    status: str
    external_squad_uuid: str | None = Field(default=None, alias="externalSquadUuid")


@dataclass(frozen=True)
class ResolvedSubscriptionProduct:
    product_code: str
    xray_failover_canary: bool = False


class ResolveSubscriptionProductUseCase:
    """Resolve a public Remnawave token to one active CyberVPN product."""

    def __init__(self, session: AsyncSession, remnawave_client: RemnawaveClient) -> None:
        self._session = session
        self._repo = ServiceAccessRepository(session)
        self._remnawave_client = remnawave_client

    async def execute(self, short_uuid: str) -> ResolvedSubscriptionProduct:
        if not SHORT_UUID_PATTERN.fullmatch(short_uuid):
            raise SubscriptionGatewayNotFoundError

        provider_user = await self._get_provider_user(short_uuid)
        if provider_user.status.upper() != "ACTIVE":
            raise SubscriptionGatewayNotFoundError

        identities = await self._repo.list_active_subscription_identities_by_provider_numeric_subject(
            provider_name="remnawave",
            provider_numeric_subject_id=provider_user.id,
        )
        if not identities:
            raise SubscriptionGatewayNotFoundError
        if len(identities) != 1:
            # Never attempt to pick a winner from an ambiguous local binding.
            raise SubscriptionGatewayUnavailableError

        identity = identities[0]
        try:
            local_ref = await resolve_exact_mapped_remnawave_ref(
                self._session,
                subject_type="service_identity",
                subject_id=identity.id,
                numeric_user_id=identity.provider_numeric_subject_id,
                legacy_uuid_raw=identity.provider_subject_ref,
            )
        except RemnawaveIdentityAccessConflict as exc:
            raise SubscriptionGatewayUnavailableError from exc
        if local_ref is None or local_ref.require_numeric_id() != provider_user.id:
            raise SubscriptionGatewayUnavailableError

        provider_legacy_uuid = _provider_legacy_uuid_or_unavailable(provider_user.uuid)
        if provider_legacy_uuid is not None and local_ref.legacy_uuid != provider_legacy_uuid:
            raise SubscriptionGatewayUnavailableError

        now = datetime.now(UTC)
        grant = await self._repo.get_active_entitlement_grant_for_service_identity(
            service_identity_id=identity.id,
            now=now,
        )
        if grant is None:
            raise SubscriptionGatewayNotFoundError
        if grant.customer_account_id != identity.customer_account_id or grant.auth_realm_id != identity.auth_realm_id:
            raise SubscriptionGatewayUnavailableError

        try:
            product_code = resolve_gateway_product_plan_code(
                grant_snapshot=getattr(grant, "grant_snapshot", None),
                service_context=identity.service_context,
            )
        except VpnProductReadinessError as exc:
            raise SubscriptionGatewayUnavailableError(exc.reason) from exc
        if product_code not in SUPPORTED_PRODUCT_CODES:
            raise SubscriptionGatewayNotFoundError

        xray_failover_canary = _is_premium_smart_ru_xray_failover_canary(
            product_code=product_code,
            service_context=identity.service_context,
        )
        try:
            ensure_spb_de_exceptions_data_plane_ready(product_code)
        except VpnProductReadinessError as exc:
            raise SubscriptionGatewayUnavailableError(exc.reason) from exc
        _ensure_provider_external_squad_matches_product(
            actual_external_squad_uuid=provider_user.external_squad_uuid,
            product_code=product_code,
        )

        return ResolvedSubscriptionProduct(
            product_code=product_code,
            xray_failover_canary=xray_failover_canary,
        )

    async def _get_provider_user(self, short_uuid: str) -> _RemnawaveUser:
        try:
            payload = await self._remnawave_client.get(f"/users/by-short-uuid/{short_uuid}")
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise SubscriptionGatewayNotFoundError from exc
            raise SubscriptionGatewayUnavailableError from exc
        except RequestError as exc:
            raise SubscriptionGatewayUnavailableError from exc

        try:
            return _RemnawaveUser.model_validate(payload)
        except ValidationError as exc:
            raise SubscriptionGatewayUnavailableError from exc


def _ensure_provider_external_squad_matches_product(
    *,
    actual_external_squad_uuid: str | None,
    product_code: str,
) -> None:
    expected_external_squad_uuid = _expected_external_squad_uuid(product_code)
    actual_normalized = _normalize_uuid_or_unavailable(
        actual_external_squad_uuid,
        reason=EXTERNAL_SQUAD_MISMATCH_REASON,
    )
    if actual_normalized != expected_external_squad_uuid:
        raise SubscriptionGatewayUnavailableError(EXTERNAL_SQUAD_MISMATCH_REASON)


def _expected_external_squad_uuid(product_code: str) -> str:
    if product_code == SMART_RU_PRODUCT_CODE:
        configured_uuid = settings.remnawave_smart_ru_external_squad_uuid
    elif product_code == SPB_DE_EXCEPTIONS_PRODUCT_CODE:
        configured_uuid = settings.remnawave_spb_de_exceptions_external_squad_uuid
    else:
        raise SubscriptionGatewayUnavailableError
    return _normalize_uuid_or_unavailable(
        configured_uuid,
        reason=EXTERNAL_SQUAD_UNCONFIGURED_REASON,
    )


def _normalize_uuid_or_unavailable(value: str | None, *, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SubscriptionGatewayUnavailableError(reason)
    try:
        return str(UUID(value.strip()))
    except ValueError as exc:
        raise SubscriptionGatewayUnavailableError(reason) from exc


def _provider_legacy_uuid_or_unavailable(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value.strip())
    except (AttributeError, ValueError) as exc:
        raise SubscriptionGatewayUnavailableError from exc


def _is_premium_smart_ru_xray_failover_canary(*, product_code: str, service_context: object) -> bool:
    if product_code != SMART_RU_PRODUCT_CODE or not isinstance(service_context, Mapping):
        return False
    return service_context.get(PREMIUM_SMART_RU_XRAY_FAILOVER_CANARY_CONTEXT_KEY) is True
