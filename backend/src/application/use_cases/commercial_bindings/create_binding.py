from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import (
    CommercialOwnerType,
    CustomerCommercialBindingStatus,
    CustomerCommercialBindingType,
)
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class CreateCustomerCommercialBindingUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._bindings = CustomerCommercialBindingRepository(session)
        self._partners = PartnerRepository(session)
        self._storefronts = StorefrontRepository(session)

    async def execute(
        self,
        *,
        user_id: UUID,
        binding_type: str,
        owner_type: str,
        storefront_id: UUID | None = None,
        partner_code: str | None = None,
        partner_code_id: UUID | None = None,
        partner_account_id: UUID | None = None,
        reason_code: str | None = None,
        evidence_payload: dict[str, Any] | None = None,
        created_by_admin_user_id: UUID | None = None,
        effective_from: datetime | None = None,
        commit: bool = True,
    ) -> CustomerCommercialBindingModel:
        if binding_type not in {member.value for member in CustomerCommercialBindingType}:
            raise ValueError("Binding type is invalid")
        if owner_type not in {member.value for member in CommercialOwnerType}:
            raise ValueError("Owner type is invalid")
        if owner_type == CommercialOwnerType.NONE.value:
            raise ValueError("Owner type cannot be none for a commercial binding")

        user = await self._session.get(MobileUserModel, user_id)
        if user is None:
            raise ValueError("User not found")
        if user.auth_realm_id is None:
            raise ValueError("User must belong to an auth realm to receive a commercial binding")

        binding_type_enum = CustomerCommercialBindingType(binding_type)
        owner_type_enum = CommercialOwnerType(owner_type)
        normalized_reason_code = reason_code.strip() if reason_code else None

        if binding_type_enum in {
            CustomerCommercialBindingType.MANUAL_OVERRIDE,
            CustomerCommercialBindingType.CONTRACT_ASSIGNMENT,
        } and not normalized_reason_code:
            raise ValueError("reason_code is required for manual_override and contract_assignment")

        resolved_storefront_id = storefront_id
        if binding_type_enum == CustomerCommercialBindingType.RESELLER_BINDING and storefront_id is not None:
            raise ValueError("Reseller binding cannot be scoped to a storefront")
        if binding_type_enum == CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER and storefront_id is None:
            raise ValueError("storefront_id is required for storefront_default_owner")
        if storefront_id is not None:
            storefront = await self._storefronts.get_storefront_by_id(storefront_id)
            if storefront is None:
                raise ValueError("Storefront not found")
            if storefront.auth_realm_id is not None and storefront.auth_realm_id != user.auth_realm_id:
                raise ValueError("Storefront does not belong to the same auth realm as the user")
            resolved_storefront_id = storefront.id

        resolved_partner_code_id = partner_code_id
        resolved_partner_account_id = partner_account_id
        normalized_partner_code = partner_code.strip() if partner_code else None
        if normalized_partner_code and resolved_partner_code_id is None:
            code_model = await self._partners.get_active_code_by_code(normalized_partner_code)
            if code_model is None:
                raise ValueError("Partner code not found or inactive")
            resolved_partner_code_id = code_model.id
            resolved_partner_account_id = resolved_partner_account_id or code_model.partner_account_id
        elif resolved_partner_code_id is not None and normalized_partner_code is None:
            code_model = await self._partners.get_code_by_id(resolved_partner_code_id)
            if code_model is None:
                raise ValueError("Partner code not found")
            resolved_partner_account_id = resolved_partner_account_id or code_model.partner_account_id

        if (
            binding_type_enum == CustomerCommercialBindingType.RESELLER_BINDING
            and owner_type_enum != CommercialOwnerType.RESELLER
        ):
            raise ValueError("reseller_binding must use owner_type reseller")

        if owner_type_enum == CommercialOwnerType.DIRECT_STORE:
            if resolved_partner_code_id is not None or resolved_partner_account_id is not None:
                raise ValueError("direct_store bindings cannot reference partner codes or partner accounts")
        elif resolved_partner_code_id is None and resolved_partner_account_id is None:
            raise ValueError("Partner owner bindings must reference a partner_code or partner_account")

        effective_from_utc = _normalize_utc(effective_from)
        existing = await self._bindings.find_active_for_scope(
            user_id=user.id,
            binding_type=binding_type_enum.value,
            storefront_id=resolved_storefront_id,
        )
        if existing and _is_same_binding(
            existing=existing,
            owner_type=owner_type_enum.value,
            partner_account_id=resolved_partner_account_id,
            partner_code_id=resolved_partner_code_id,
            reason_code=normalized_reason_code,
        ):
            return existing
        if existing:
            await self._bindings.supersede(existing, effective_to=effective_from_utc)

        payload = dict(evidence_payload or {})
        if normalized_partner_code is not None:
            payload.setdefault("partner_code", normalized_partner_code)

        model = CustomerCommercialBindingModel(
            user_id=user.id,
            auth_realm_id=user.auth_realm_id,
            storefront_id=resolved_storefront_id,
            binding_type=binding_type_enum.value,
            binding_status=CustomerCommercialBindingStatus.ACTIVE.value,
            owner_type=owner_type_enum.value,
            partner_account_id=resolved_partner_account_id,
            partner_code_id=resolved_partner_code_id,
            reason_code=normalized_reason_code,
            evidence_payload=payload,
            created_by_admin_user_id=created_by_admin_user_id,
            effective_from=effective_from_utc,
        )
        created = await self._bindings.create(model)
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        return created


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_same_binding(
    *,
    existing: CustomerCommercialBindingModel,
    owner_type: str,
    partner_account_id: UUID | None,
    partner_code_id: UUID | None,
    reason_code: str | None,
) -> bool:
    return (
        existing.owner_type == owner_type
        and existing.partner_account_id == partner_account_id
        and existing.partner_code_id == partner_code_id
        and existing.reason_code == reason_code
    )
