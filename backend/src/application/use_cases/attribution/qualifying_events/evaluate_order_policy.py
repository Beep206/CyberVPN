from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CommercialOwnerType, PaymentDisputeOutcomeClass, PrincipalClass
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository
from src.infrastructure.database.repositories.renewal_order_repo import RenewalOrderRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository

PAID_ORDER_SETTLEMENT_STATUSES = {"paid", "partially_refunded", "refunded"}
COMMERCIAL_OWNER_TYPES = {
    CommercialOwnerType.AFFILIATE.value,
    CommercialOwnerType.PERFORMANCE.value,
    CommercialOwnerType.RESELLER.value,
}


@dataclass(frozen=True)
class OrderPolicyStackingResult:
    commercial_discount_instruments: list[str]
    settlement_instruments: list[str]
    stacking_valid: bool
    reason_codes: list[str]


@dataclass(frozen=True)
class OrderPolicyQualifyingEventResult:
    qualifying_first_payment: bool
    first_paid_order: bool
    order_is_paid: bool
    fully_refunded: bool
    risk_blocked: bool
    positive_paid_economic_amount: bool
    paid_economic_amount: float
    excluded_credit_amount: float
    reason_codes: list[str]


@dataclass(frozen=True)
class OrderPolicyPayoutRulesResult:
    commercial_owner_type: str
    commercial_owner_present: bool
    program_allows_commercial_owner: bool
    program_allows_referral_credit: bool
    referral_cash_payout_allowed: bool
    partner_cash_payout_allowed: bool
    no_double_payout: bool
    referral_reason_codes: list[str]
    partner_reason_codes: list[str]


@dataclass(frozen=True)
class OrderPolicyEvaluationResult:
    order: object
    stacking: OrderPolicyStackingResult
    qualifying_event: OrderPolicyQualifyingEventResult
    payout_rules: OrderPolicyPayoutRulesResult
    evaluated_at: datetime


class EvaluateOrderPolicyUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._orders = OrderRepository(session)
        self._attribution_results = OrderAttributionResultRepository(session)
        self._payment_disputes = PaymentDisputeRepository(session)
        self._renewal_orders = RenewalOrderRepository(session)
        self._risk = RiskSubjectGraphRepository(session)

    async def execute(self, *, order_id):
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        attribution_result = await self._attribution_results.get_by_order_id(order.id)
        renewal_order = await self._renewal_orders.get_by_order_id(order.id)
        payment_disputes = await self._payment_disputes.list_for_order(order.id)
        program_policy = dict((order.policy_snapshot or {}).get("program_eligibility_policy") or {})

        stacking = _evaluate_stacking(
            promo_present=order.promo_code_id is not None,
            partner_code_present=order.partner_code_id is not None,
            wallet_present=float(order.wallet_amount) > 0,
        )

        risk_blocked = await self._is_risk_blocked(order=order)
        open_dispute_present = any(
            dispute.outcome_class == PaymentDisputeOutcomeClass.OPEN.value or dispute.lifecycle_status != "closed"
            for dispute in payment_disputes
        )
        order_is_paid = order.settlement_status in PAID_ORDER_SETTLEMENT_STATUSES
        fully_refunded = order.settlement_status == "refunded"
        paid_economic_amount = float(order.gateway_amount) + float(order.wallet_amount)
        positive_paid_economic_amount = paid_economic_amount > 0
        excluded_credit_amount = 0.0

        user_orders = await self._orders.list_for_user(user_id=order.user_id, limit=500, offset=0)
        previous_paid_orders = [
            candidate
            for candidate in user_orders
            if candidate.id != order.id
            and candidate.settlement_status in PAID_ORDER_SETTLEMENT_STATUSES
            and candidate.created_at < order.created_at
        ]
        first_paid_order = order_is_paid and not previous_paid_orders

        qualifying_reason_codes: list[str] = []
        if not stacking.stacking_valid:
            qualifying_reason_codes.extend(stacking.reason_codes)
        if not order_is_paid:
            qualifying_reason_codes.append("order_not_paid")
        if fully_refunded:
            qualifying_reason_codes.append("order_fully_refunded")
        if not positive_paid_economic_amount:
            qualifying_reason_codes.append("non_positive_paid_economic_amount")
        if risk_blocked:
            qualifying_reason_codes.append("risk_policy_blocked")
        if open_dispute_present:
            qualifying_reason_codes.append("open_payment_dispute")
        qualifying_reason_codes = sorted(set(qualifying_reason_codes))

        owner_type = (
            renewal_order.effective_owner_type
            if renewal_order is not None
            else attribution_result.owner_type
            if attribution_result is not None
            else CommercialOwnerType.NONE.value
        )
        commercial_owner_present = owner_type in COMMERCIAL_OWNER_TYPES
        program_allows_commercial_owner = _program_allows_owner_type(
            owner_type=owner_type,
            program_policy=program_policy,
        )
        program_allows_referral_credit = bool(program_policy.get("referral_credit_allowed"))

        referral_reason_codes = list(qualifying_reason_codes)
        if commercial_owner_present:
            referral_reason_codes.append("commercial_owner_already_resolved")
        if not first_paid_order:
            referral_reason_codes.append("not_first_paid_order")
        if not program_allows_referral_credit:
            referral_reason_codes.append("program_policy_disallows_referral_credit")
        referral_reason_codes = sorted(set(referral_reason_codes))

        partner_reason_codes = list(qualifying_reason_codes)
        if not commercial_owner_present:
            partner_reason_codes.append("no_commercial_owner")
        if renewal_order is not None:
            partner_reason_codes.extend(list(renewal_order.payout_block_reason_codes or []))
        elif commercial_owner_present and not program_allows_commercial_owner:
            partner_reason_codes.append("program_policy_disallows_owner_type")
        partner_reason_codes = sorted(set(partner_reason_codes))

        qualifying_first_payment = not referral_reason_codes
        referral_cash_payout_allowed = not referral_reason_codes
        partner_cash_payout_allowed = not partner_reason_codes

        return OrderPolicyEvaluationResult(
            order=order,
            stacking=stacking,
            qualifying_event=OrderPolicyQualifyingEventResult(
                qualifying_first_payment=qualifying_first_payment,
                first_paid_order=first_paid_order,
                order_is_paid=order_is_paid,
                fully_refunded=fully_refunded,
                risk_blocked=risk_blocked,
                positive_paid_economic_amount=positive_paid_economic_amount,
                paid_economic_amount=paid_economic_amount,
                excluded_credit_amount=excluded_credit_amount,
                reason_codes=qualifying_reason_codes,
            ),
            payout_rules=OrderPolicyPayoutRulesResult(
                commercial_owner_type=owner_type,
                commercial_owner_present=commercial_owner_present,
                program_allows_commercial_owner=program_allows_commercial_owner,
                program_allows_referral_credit=program_allows_referral_credit,
                referral_cash_payout_allowed=referral_cash_payout_allowed,
                partner_cash_payout_allowed=partner_cash_payout_allowed,
                no_double_payout=not (referral_cash_payout_allowed and partner_cash_payout_allowed),
                referral_reason_codes=referral_reason_codes,
                partner_reason_codes=partner_reason_codes,
            ),
            evaluated_at=datetime.now(UTC),
        )

    async def _is_risk_blocked(self, *, order) -> bool:
        risk_subject = await self._risk.get_subject_by_principal(
            principal_class=PrincipalClass.CUSTOMER.value,
            principal_subject=str(order.user_id),
            auth_realm_id=order.auth_realm_id,
        )
        if risk_subject is None:
            return False
        open_reviews = await self._risk.list_open_reviews_for_subject(risk_subject.id)
        return any(review.decision in {"hold", "block"} for review in open_reviews)


def _evaluate_stacking(
    *,
    promo_present: bool,
    partner_code_present: bool,
    wallet_present: bool,
) -> OrderPolicyStackingResult:
    commercial_discount_instruments: list[str] = []
    settlement_instruments: list[str] = []
    reason_codes: list[str] = []

    if promo_present:
        commercial_discount_instruments.append("promo")
    if partner_code_present:
        commercial_discount_instruments.append("partner_code")
    if wallet_present:
        settlement_instruments.append("wallet_spend")

    if promo_present and partner_code_present:
        reason_codes.append("promo_and_partner_code_blocked")

    return OrderPolicyStackingResult(
        commercial_discount_instruments=commercial_discount_instruments,
        settlement_instruments=settlement_instruments,
        stacking_valid=not reason_codes,
        reason_codes=sorted(set(reason_codes)),
    )


def _program_allows_owner_type(*, owner_type: str, program_policy: dict) -> bool:
    if owner_type == CommercialOwnerType.AFFILIATE.value:
        return bool(program_policy.get("creator_affiliate_allowed"))
    if owner_type == CommercialOwnerType.PERFORMANCE.value:
        return bool(program_policy.get("performance_allowed"))
    if owner_type == CommercialOwnerType.RESELLER.value:
        return bool(program_policy.get("reseller_allowed"))
    return False
