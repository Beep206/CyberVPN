from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CommercialOwnerType, CommissionabilityStatus, PaymentDisputeOutcomeClass, PrincipalClass
from src.infrastructure.database.models.commissionability_evaluation_model import CommissionabilityEvaluationModel
from src.infrastructure.database.repositories.commissionability_evaluation_repo import (
    CommissionabilityEvaluationRepository,
)
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.payment_dispute_repo import PaymentDisputeRepository
from src.infrastructure.database.repositories.refund_repo import RefundRepository
from src.infrastructure.database.repositories.renewal_order_repo import RenewalOrderRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository


@dataclass(frozen=True)
class OrderExplainabilityResult:
    order: object
    commissionability_evaluation: CommissionabilityEvaluationModel
    refunds: list[object]
    payment_disputes: list[object]
    explainability_payload: dict


class GetOrderExplainabilityUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._attribution_results = OrderAttributionResultRepository(session)
        self._evaluations = CommissionabilityEvaluationRepository(session)
        self._refunds = RefundRepository(session)
        self._payment_disputes = PaymentDisputeRepository(session)
        self._renewal_orders = RenewalOrderRepository(session)
        self._risk = RiskSubjectGraphRepository(session)
        self._growth_rewards = GrowthRewardAllocationRepository(session)

    async def execute(self, *, order_id):
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        refunds = await self._refunds.list_for_order(order.id)
        payment_disputes = await self._payment_disputes.list_for_order(order.id)
        growth_reward_allocations = await self._growth_rewards.list_for_order(order.id)
        attribution_result = await self._attribution_results.get_by_order_id(order.id)
        renewal_order = await self._renewal_orders.get_by_order_id(order.id)
        resolved_owner_type = (
            renewal_order.effective_owner_type
            if renewal_order is not None
            else attribution_result.owner_type
            if attribution_result is not None
            else CommercialOwnerType.NONE.value
        )
        resolved_owner_source = (
            renewal_order.effective_owner_source
            if renewal_order is not None
            else attribution_result.owner_source
            if attribution_result is not None
            else None
        )
        resolved_partner_account_id = (
            renewal_order.effective_partner_account_id
            if renewal_order is not None
            else attribution_result.partner_account_id
            if attribution_result is not None
            else None
        )
        resolved_partner_code_id = (
            renewal_order.effective_partner_code_id
            if renewal_order is not None
            else attribution_result.partner_code_id
            if attribution_result is not None
            else None
        )
        active_growth_allocations = [
            allocation
            for allocation in growth_reward_allocations
            if allocation.allocation_status == "allocated"
        ]
        growth_reward_types = sorted({allocation.reward_type for allocation in growth_reward_allocations})
        active_growth_reward_types = sorted({allocation.reward_type for allocation in active_growth_allocations})

        risk_subject = await self._risk.get_subject_by_principal(
            principal_class=PrincipalClass.CUSTOMER.value,
            principal_subject=str(order.user_id),
            auth_realm_id=order.auth_realm_id,
        )
        risk_reason_codes: list[str] = []
        risk_allowed = True
        if risk_subject is not None:
            open_reviews = await self._risk.list_open_reviews_for_subject(risk_subject.id)
            risk_reason_codes = sorted(
                {
                    (
                        "risk_review_block"
                        if review.decision == "block"
                        else "risk_review_hold"
                        if review.decision == "hold"
                        else ""
                    )
                    for review in open_reviews
                }
                - {""}
            )
            risk_allowed = not risk_reason_codes

        program_policy = dict((order.policy_snapshot or {}).get("program_eligibility_policy") or {})
        program_allows_commissionability = any(
            bool(program_policy.get(flag))
            for flag in (
                "creator_affiliate_allowed",
                "performance_allowed",
                "reseller_allowed",
                "renewal_commissionable",
                "addon_commissionable",
            )
        )
        renewal_payout_reason_codes = (
            list(renewal_order.payout_block_reason_codes or []) if renewal_order is not None else []
        )
        partner_context_present = bool(
            order.partner_code_id or (renewal_order is not None and renewal_order.effective_partner_code_id)
        )
        positive_commission_base = float(order.commission_base_amount) > 0
        paid_status = order.settlement_status in {"paid", "partially_refunded", "refunded"}
        fully_refunded = order.settlement_status == "refunded"
        open_payment_dispute_present = any(
            dispute.outcome_class == PaymentDisputeOutcomeClass.OPEN.value or dispute.lifecycle_status != "closed"
            for dispute in payment_disputes
        )

        reason_codes: list[str] = []
        if not partner_context_present:
            reason_codes.append("missing_partner_context")
        if not program_allows_commissionability:
            reason_codes.append("program_policy_disallows_commissionability")
        if not positive_commission_base:
            reason_codes.append("non_positive_commission_base")
        if not paid_status:
            reason_codes.append("order_not_paid")
        if fully_refunded:
            reason_codes.append("order_fully_refunded")
        if open_payment_dispute_present:
            reason_codes.append("open_payment_dispute")
        reason_codes.extend(renewal_payout_reason_codes)
        reason_codes.extend(risk_reason_codes)
        reason_codes = sorted(set(reason_codes))

        commissionability_status = _resolve_commissionability_status(
            paid_status=paid_status,
            fully_refunded=fully_refunded,
            reason_codes=reason_codes,
        )
        evaluation_snapshot = {
            "order_id": str(order.id),
            "checkout_session_id": str(order.checkout_session_id),
            "sale_channel": order.sale_channel,
            "currency_code": order.currency_code,
            "settlement_status": order.settlement_status,
            "commercial_amounts": {
                "displayed_price": float(order.displayed_price),
                "commission_base_amount": float(order.commission_base_amount),
                "discount_amount": float(order.discount_amount),
                "wallet_amount": float(order.wallet_amount),
                "gateway_amount": float(order.gateway_amount),
                "partner_markup": float(order.partner_markup),
            },
            "preconditions": {
                "partner_context_present": partner_context_present,
                "program_allows_commissionability": program_allows_commissionability,
                "positive_commission_base": positive_commission_base,
                "paid_status": paid_status,
                "fully_refunded": fully_refunded,
                "open_payment_dispute_present": open_payment_dispute_present,
                "renewal_payout_reason_codes": renewal_payout_reason_codes,
                "risk_allowed": risk_allowed,
                "risk_reason_codes": risk_reason_codes,
            },
        }
        commercial_resolution_summary = {
            "resolved_owner_type": resolved_owner_type,
            "resolved_owner_source": resolved_owner_source,
            "resolved_partner_account_id": str(resolved_partner_account_id) if resolved_partner_account_id else None,
            "resolved_partner_code_id": str(resolved_partner_code_id) if resolved_partner_code_id else None,
            "attribution_result_id": str(attribution_result.id) if attribution_result is not None else None,
            "renewal_order_id": str(renewal_order.id) if renewal_order is not None else None,
            "renewal_override_applied": (
                renewal_order is not None
                and (
                    renewal_order.effective_owner_type != renewal_order.provenance_owner_type
                    or renewal_order.effective_owner_source != renewal_order.provenance_owner_source
                )
            ),
            "winner_reference": {
                "winning_touchpoint_id": (
                    str(attribution_result.winning_touchpoint_id)
                    if attribution_result is not None and attribution_result.winning_touchpoint_id
                    else None
                ),
                "winning_binding_id": (
                    str(attribution_result.winning_binding_id)
                    if attribution_result is not None and attribution_result.winning_binding_id
                    else str(renewal_order.winning_binding_id)
                    if renewal_order is not None and renewal_order.winning_binding_id
                    else None
                ),
            },
            "reason_path": (
                list(renewal_order.explainability_snapshot.get("effective_owner", {}).get("reason_path", []))
                if renewal_order is not None
                else list(attribution_result.rule_path or [])
                if attribution_result is not None
                else ["no_owner_resolved"]
            ),
            "payout_block_reason_codes": list(renewal_order.payout_block_reason_codes or [])
            if renewal_order is not None
            else [],
        }
        growth_reward_summary = {
            "allocation_count": len(growth_reward_allocations),
            "active_allocation_count": len(active_growth_allocations),
            "reward_types": growth_reward_types,
            "active_reward_types": active_growth_reward_types,
            "allocation_ids": [str(allocation.id) for allocation in growth_reward_allocations],
        }
        lane_views = {
            "invite_gift": {
                "active": any(
                    reward_type in {"invite_reward", "gift_bonus", "bonus_days"}
                    for reward_type in active_growth_reward_types
                ),
                "reward_types": [
                    reward_type
                    for reward_type in active_growth_reward_types
                    if reward_type in {"invite_reward", "gift_bonus", "bonus_days"}
                ],
                "evidence_refs": [
                    str(allocation.id)
                    for allocation in active_growth_allocations
                    if allocation.reward_type in {"invite_reward", "gift_bonus", "bonus_days"}
                ],
            },
            "consumer_referral": {
                "active": "referral_credit" in active_growth_reward_types,
                "reward_types": [
                    reward_type for reward_type in active_growth_reward_types if reward_type == "referral_credit"
                ],
                "evidence_refs": [
                    str(allocation.id)
                    for allocation in active_growth_allocations
                    if allocation.reward_type == "referral_credit"
                ],
            },
            "creator_affiliate": {
                "active": resolved_owner_type == CommercialOwnerType.AFFILIATE.value,
                "owner_type": resolved_owner_type,
                "owner_source": resolved_owner_source,
                "partner_code_id": str(resolved_partner_code_id) if resolved_partner_code_id else None,
                "partner_account_id": str(resolved_partner_account_id) if resolved_partner_account_id else None,
            },
            "performance_media_buyer": {
                "active": resolved_owner_type == CommercialOwnerType.PERFORMANCE.value,
                "owner_type": resolved_owner_type,
                "owner_source": resolved_owner_source,
                "partner_code_id": str(resolved_partner_code_id) if resolved_partner_code_id else None,
            },
            "reseller_distribution": {
                "active": resolved_owner_type == CommercialOwnerType.RESELLER.value,
                "owner_type": resolved_owner_type,
                "owner_source": resolved_owner_source,
                "partner_code_id": str(resolved_partner_code_id) if resolved_partner_code_id else None,
                "partner_account_id": str(resolved_partner_account_id) if resolved_partner_account_id else None,
                "binding_id": (
                    str(attribution_result.winning_binding_id)
                    if attribution_result is not None and attribution_result.winning_binding_id
                    else str(renewal_order.winning_binding_id)
                    if renewal_order is not None and renewal_order.winning_binding_id
                    else None
                ),
            },
            "renewal_chain": {
                "active": renewal_order is not None,
                "renewal_order_id": str(renewal_order.id) if renewal_order is not None else None,
                "renewal_sequence_number": (
                    renewal_order.renewal_sequence_number if renewal_order is not None else None
                ),
                "renewal_mode": renewal_order.renewal_mode if renewal_order is not None else None,
                "payout_eligible": bool(renewal_order.payout_eligible) if renewal_order is not None else False,
            },
        }
        explainability_payload = {
            "merchant_snapshot": order.merchant_snapshot or {},
            "pricing_snapshot": order.pricing_snapshot or {},
            "policy_snapshot": order.policy_snapshot or {},
            "entitlements_snapshot": order.entitlements_snapshot or {},
            "commercial_resolution_summary": commercial_resolution_summary,
            "growth_reward_summary": growth_reward_summary,
            "lane_views": lane_views,
            "linked_refunds": [
                {
                    "id": str(refund.id),
                    "refund_status": refund.refund_status,
                    "amount": float(refund.amount),
                    "currency_code": refund.currency_code,
                    "external_reference": refund.external_reference,
                }
                for refund in refunds
            ],
            "linked_payment_disputes": [
                {
                    "id": str(dispute.id),
                    "subtype": dispute.subtype,
                    "outcome_class": dispute.outcome_class,
                    "lifecycle_status": dispute.lifecycle_status,
                    "disputed_amount": float(dispute.disputed_amount),
                    "fee_amount": float(dispute.fee_amount),
                }
                for dispute in payment_disputes
            ],
            "linked_growth_reward_allocations": [
                {
                    "id": str(allocation.id),
                    "reward_type": allocation.reward_type,
                    "allocation_status": allocation.allocation_status,
                    "beneficiary_user_id": str(allocation.beneficiary_user_id),
                    "quantity": float(allocation.quantity),
                    "unit": allocation.unit,
                    "currency_code": allocation.currency_code,
                    "source_key": allocation.source_key,
                    "allocated_at": allocation.allocated_at.isoformat(),
                }
                for allocation in growth_reward_allocations
            ],
            "renewal_order": (
                {
                    "id": str(renewal_order.id),
                    "initial_order_id": str(renewal_order.initial_order_id),
                    "prior_order_id": str(renewal_order.prior_order_id),
                    "renewal_sequence_number": renewal_order.renewal_sequence_number,
                    "renewal_mode": renewal_order.renewal_mode,
                    "provenance_owner_type": renewal_order.provenance_owner_type,
                    "effective_owner_type": renewal_order.effective_owner_type,
                    "effective_owner_source": renewal_order.effective_owner_source,
                    "effective_partner_code_id": (
                        str(renewal_order.effective_partner_code_id)
                        if renewal_order.effective_partner_code_id
                        else None
                    ),
                    "payout_eligible": bool(renewal_order.payout_eligible),
                    "payout_block_reason_codes": list(renewal_order.payout_block_reason_codes or []),
                    "lineage_snapshot": renewal_order.lineage_snapshot or {},
                    "explainability_snapshot": renewal_order.explainability_snapshot or {},
                }
                if renewal_order is not None
                else None
            ),
            "future_phase_placeholders": {
                "attribution_result_present": attribution_result is not None,
                "growth_reward_allocation_count": len(growth_reward_allocations),
                "renewal_order_present": renewal_order is not None,
                "payout_owner_computed": (
                    (
                        attribution_result is not None
                        and attribution_result.owner_type != CommercialOwnerType.NONE.value
                    )
                    or (
                        renewal_order is not None
                        and renewal_order.effective_owner_type != CommercialOwnerType.NONE.value
                    )
                ),
            },
            "attribution_result": (
                {
                    "id": str(attribution_result.id),
                    "owner_type": attribution_result.owner_type,
                    "owner_source": attribution_result.owner_source,
                    "partner_account_id": (
                        str(attribution_result.partner_account_id) if attribution_result.partner_account_id else None
                    ),
                    "partner_code_id": (
                        str(attribution_result.partner_code_id) if attribution_result.partner_code_id else None
                    ),
                    "winning_touchpoint_id": (
                        str(attribution_result.winning_touchpoint_id)
                        if attribution_result.winning_touchpoint_id
                        else None
                    ),
                    "winning_binding_id": (
                        str(attribution_result.winning_binding_id) if attribution_result.winning_binding_id else None
                    ),
                    "rule_path": list(attribution_result.rule_path or []),
                }
                if attribution_result is not None
                else None
            ),
            "commissionability_reasons": reason_codes,
        }

        evaluation = await self._evaluations.get_by_order_id(order.id)
        if evaluation is None:
            evaluation = CommissionabilityEvaluationModel(
                order_id=order.id,
                commissionability_status=commissionability_status,
                reason_codes=reason_codes,
                partner_context_present=partner_context_present,
                program_allows_commissionability=program_allows_commissionability,
                positive_commission_base=positive_commission_base,
                paid_status=paid_status,
                fully_refunded=fully_refunded,
                open_payment_dispute_present=open_payment_dispute_present,
                risk_allowed=risk_allowed,
                evaluation_snapshot=evaluation_snapshot,
                explainability_snapshot=explainability_payload,
                evaluated_at=datetime.now(UTC),
            )
            await self._evaluations.create(evaluation)
        else:
            evaluation.commissionability_status = commissionability_status
            evaluation.reason_codes = reason_codes
            evaluation.partner_context_present = partner_context_present
            evaluation.program_allows_commissionability = program_allows_commissionability
            evaluation.positive_commission_base = positive_commission_base
            evaluation.paid_status = paid_status
            evaluation.fully_refunded = fully_refunded
            evaluation.open_payment_dispute_present = open_payment_dispute_present
            evaluation.risk_allowed = risk_allowed
            evaluation.evaluation_snapshot = evaluation_snapshot
            evaluation.explainability_snapshot = explainability_payload
            evaluation.evaluated_at = datetime.now(UTC)

        await self._session.commit()
        refreshed = await self._evaluations.get_by_order_id(order.id)
        if refreshed is None:
            raise ValueError("Commissionability evaluation was saved but could not be reloaded")

        return OrderExplainabilityResult(
            order=order,
            commissionability_evaluation=refreshed,
            refunds=refunds,
            payment_disputes=payment_disputes,
            explainability_payload=explainability_payload,
        )


def _resolve_commissionability_status(*, paid_status: bool, fully_refunded: bool, reason_codes: list[str]) -> str:
    if not paid_status and not fully_refunded:
        return CommissionabilityStatus.PENDING.value
    if reason_codes:
        return CommissionabilityStatus.INELIGIBLE.value
    return CommissionabilityStatus.ELIGIBLE.value
