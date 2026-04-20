from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CommercialOwnerSource, CommercialOwnerType, CustomerCommercialBindingType
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.renewal_order_model import RenewalOrderModel
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.renewal_order_repo import RenewalOrderRepository

COMMERCIAL_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}


@dataclass(frozen=True)
class _ResolvedOwner:
    owner_type: str
    owner_source: str | None
    partner_account_id: UUID | None
    partner_code_id: UUID | None
    winning_binding_id: UUID | None
    reason_path: list[str]


class ResolveRenewalOrderUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._attribution_results = OrderAttributionResultRepository(session)
        self._renewal_orders = RenewalOrderRepository(session)
        self._bindings = CustomerCommercialBindingRepository(session)
        self._partners = PartnerRepository(session)
        self._partner_accounts = PartnerAccountRepository(session)
        self._users = MobileUserRepository(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        prior_order_id: UUID,
        renewal_mode: str,
        commit: bool = True,
    ) -> RenewalOrderModel:
        existing = await self._renewal_orders.get_by_order_id(order_id)
        if existing is not None:
            return existing

        order = await self._orders.get_by_id(order_id)
        prior_order = await self._orders.get_by_id(prior_order_id)
        if order is None or prior_order is None:
            raise ValueError("Order not found")
        if order.id == prior_order.id:
            raise ValueError("Renewal order and prior order must be different")
        if order.user_id != prior_order.user_id:
            raise ValueError("Renewal order must belong to the same customer as the prior order")
        if str(order.auth_realm_id) != str(prior_order.auth_realm_id):
            raise ValueError("Renewal order must stay within the same auth realm")
        if _normalize_utc(order.created_at) <= _normalize_utc(prior_order.created_at):
            raise ValueError("Renewal order must be created after the prior order")
        if renewal_mode not in {"manual", "auto"}:
            raise ValueError("Unsupported renewal mode")

        prior_renewal = await self._renewal_orders.get_by_order_id(prior_order.id)
        if prior_renewal is not None:
            initial_order_id = prior_renewal.initial_order_id
            originating_attribution_result_id = prior_renewal.originating_attribution_result_id
            provenance = _ResolvedOwner(
                owner_type=prior_renewal.provenance_owner_type,
                owner_source=prior_renewal.provenance_owner_source,
                partner_account_id=prior_renewal.provenance_partner_account_id,
                partner_code_id=prior_renewal.provenance_partner_code_id,
                winning_binding_id=None,
                reason_path=["inherited_from_prior_renewal_chain"],
            )
            renewal_sequence_number = prior_renewal.renewal_sequence_number + 1
            provenance_source = "prior_renewal_chain"
        else:
            prior_attribution = await self._attribution_results.get_by_order_id(prior_order.id)
            initial_order_id = prior_order.id
            originating_attribution_result_id = prior_attribution.id if prior_attribution is not None else None
            provenance = _resolved_owner_from_attribution(prior_attribution)
            renewal_sequence_number = 1
            provenance_source = "initial_acquisition_order"

        bindings = await self._bindings.list_active_for_user(
            user_id=order.user_id,
            storefront_id=order.storefront_id,
        )
        override = _resolve_binding_override(bindings)
        effective_owner = override or provenance

        payout_block_reason_codes = await self._resolve_payout_block_reason_codes(
            owner=effective_owner,
            order=order,
        )
        payout_eligible = not payout_block_reason_codes

        lineage_snapshot = {
            "order_id": str(order.id),
            "prior_order_id": str(prior_order.id),
            "initial_order_id": str(initial_order_id),
            "renewal_sequence_number": renewal_sequence_number,
            "renewal_mode": renewal_mode,
            "provenance_source": provenance_source,
            "prior_order_is_renewal": prior_renewal is not None,
            "originating_attribution_result_id": (
                str(originating_attribution_result_id) if originating_attribution_result_id else None
            ),
        }
        explainability_snapshot = {
            "renewal_precedence": [
                "manual_override",
                "contract_assignment",
                "persistent_reseller_binding",
                "originating_commissionable_chain",
                "none",
            ],
            "provenance_owner": _serialize_owner(provenance),
            "effective_owner": _serialize_owner(effective_owner),
            "override_binding_applied": override is not None,
            "payout_eligible": payout_eligible,
            "payout_block_reason_codes": list(payout_block_reason_codes),
            "lineage_flags": {
                "plan_changed_since_prior_order": order.subscription_plan_id != prior_order.subscription_plan_id,
                "storefront_changed_since_prior_order": order.storefront_id != prior_order.storefront_id,
            },
        }
        policy_snapshot = {
            "current_order_policy_snapshot": dict(order.policy_snapshot or {}),
            "renewal_mode": renewal_mode,
            "renewal_sequence_number": renewal_sequence_number,
        }

        model = RenewalOrderModel(
            order_id=order.id,
            initial_order_id=initial_order_id,
            prior_order_id=prior_order.id,
            user_id=order.user_id,
            auth_realm_id=order.auth_realm_id,
            storefront_id=order.storefront_id,
            originating_attribution_result_id=originating_attribution_result_id,
            winning_binding_id=effective_owner.winning_binding_id,
            renewal_sequence_number=renewal_sequence_number,
            renewal_mode=renewal_mode,
            provenance_owner_type=provenance.owner_type,
            provenance_owner_source=provenance.owner_source,
            provenance_partner_account_id=provenance.partner_account_id,
            provenance_partner_code_id=provenance.partner_code_id,
            effective_owner_type=effective_owner.owner_type,
            effective_owner_source=effective_owner.owner_source,
            effective_partner_account_id=effective_owner.partner_account_id,
            effective_partner_code_id=effective_owner.partner_code_id,
            payout_eligible=payout_eligible,
            payout_block_reason_codes=payout_block_reason_codes,
            lineage_snapshot=lineage_snapshot,
            explainability_snapshot=explainability_snapshot,
            policy_snapshot=policy_snapshot,
            resolved_at=datetime.now(UTC),
        )
        created = await self._renewal_orders.create(model)
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        return created

    async def _resolve_payout_block_reason_codes(
        self,
        *,
        owner: _ResolvedOwner,
        order: OrderModel,
    ) -> list[str]:
        reason_codes: list[str] = []
        program_policy = dict((order.policy_snapshot or {}).get("program_eligibility_policy") or {})

        if owner.owner_type not in COMMERCIAL_OWNER_TYPES:
            reason_codes.append("no_effective_owner")
        if not program_policy.get("renewal_commissionable"):
            reason_codes.append("renewal_policy_disallows_commissionability")
        if owner.owner_type == CommercialOwnerType.AFFILIATE.value and not program_policy.get(
            "creator_affiliate_allowed"
        ):
            reason_codes.append("program_policy_disallows_owner_type")
        if owner.owner_type == CommercialOwnerType.PERFORMANCE.value and not program_policy.get("performance_allowed"):
            reason_codes.append("program_policy_disallows_owner_type")
        if owner.owner_type == CommercialOwnerType.RESELLER.value and not program_policy.get("reseller_allowed"):
            reason_codes.append("program_policy_disallows_owner_type")

        if owner.owner_type in COMMERCIAL_OWNER_TYPES:
            if owner.partner_code_id is None:
                reason_codes.append("missing_effective_partner_code")
            else:
                code = await self._partners.get_code_by_id(owner.partner_code_id)
                if code is None:
                    reason_codes.append("effective_partner_code_missing")
                else:
                    if not code.is_active:
                        reason_codes.append("partner_code_inactive")
                    partner_user = await self._users.get_by_id(code.partner_user_id)
                    if partner_user is None or not partner_user.is_active or partner_user.status != "active":
                        reason_codes.append("partner_user_inactive")
                    if code.partner_account_id is not None:
                        partner_account = await self._partner_accounts.get_account_by_id(code.partner_account_id)
                        if partner_account is None or partner_account.status != "active":
                            reason_codes.append("partner_account_inactive")

        return sorted(set(reason_codes))


def _resolved_owner_from_attribution(
    attribution_result: OrderAttributionResultModel | None,
) -> _ResolvedOwner:
    if attribution_result is None or attribution_result.owner_type not in COMMERCIAL_OWNER_TYPES:
        return _ResolvedOwner(
            owner_type=CommercialOwnerType.NONE.value,
            owner_source=None,
            partner_account_id=None,
            partner_code_id=None,
            winning_binding_id=None,
            reason_path=["no_originating_commissionable_owner"],
        )
    return _ResolvedOwner(
        owner_type=attribution_result.owner_type,
        owner_source=attribution_result.owner_source,
        partner_account_id=attribution_result.partner_account_id,
        partner_code_id=attribution_result.partner_code_id,
        winning_binding_id=None,
        reason_path=["inherited_from_initial_order_attribution"],
    )


def _resolve_binding_override(bindings: list[CustomerCommercialBindingModel]) -> _ResolvedOwner | None:
    def _pick(binding_type: str) -> CustomerCommercialBindingModel | None:
        for binding in bindings:
            if binding.binding_type == binding_type:
                return binding
        return None

    manual_override = _pick(CustomerCommercialBindingType.MANUAL_OVERRIDE.value)
    if manual_override is not None:
        return _resolved_owner_from_binding(
            manual_override,
            owner_source=CommercialOwnerSource.MANUAL_OVERRIDE.value,
            reason_path=["manual_override_binding_selected_for_renewal"],
        )

    contract_assignment = _pick(CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value)
    if contract_assignment is not None:
        return _resolved_owner_from_binding(
            contract_assignment,
            owner_source=CommercialOwnerSource.CONTRACT_ASSIGNMENT.value,
            reason_path=["contract_assignment_binding_selected_for_renewal"],
        )

    reseller_binding = _pick(CustomerCommercialBindingType.RESELLER_BINDING.value)
    if reseller_binding is not None:
        return _resolved_owner_from_binding(
            reseller_binding,
            owner_source=CommercialOwnerSource.PERSISTENT_RESELLER_BINDING.value,
            reason_path=["persistent_reseller_binding_selected_for_renewal"],
        )

    return None


def _resolved_owner_from_binding(
    binding: CustomerCommercialBindingModel,
    *,
    owner_source: str,
    reason_path: list[str],
) -> _ResolvedOwner:
    return _ResolvedOwner(
        owner_type=binding.owner_type,
        owner_source=owner_source,
        partner_account_id=binding.partner_account_id,
        partner_code_id=binding.partner_code_id,
        winning_binding_id=binding.id,
        reason_path=reason_path,
    )


def _serialize_owner(owner: _ResolvedOwner) -> dict:
    return {
        "owner_type": owner.owner_type,
        "owner_source": owner.owner_source,
        "partner_account_id": str(owner.partner_account_id) if owner.partner_account_id else None,
        "partner_code_id": str(owner.partner_code_id) if owner.partner_code_id else None,
        "winning_binding_id": str(owner.winning_binding_id) if owner.winning_binding_id else None,
        "reason_path": list(owner.reason_path),
    }


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
