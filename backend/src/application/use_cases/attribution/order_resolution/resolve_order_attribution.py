from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService
from src.domain.enums import CommercialOwnerSource, CommercialOwnerType, CustomerCommercialBindingType
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.customer_commercial_binding_model import (
    CustomerCommercialBindingModel,
)
from src.infrastructure.database.models.order_attribution_result_model import OrderAttributionResultModel
from src.infrastructure.database.models.order_model import OrderModel
from src.infrastructure.database.models.partner_model import PartnerCodeModel
from src.infrastructure.database.repositories.attribution_touchpoint_repo import AttributionTouchpointRepository
from src.infrastructure.database.repositories.customer_commercial_binding_repo import (
    CustomerCommercialBindingRepository,
)
from src.infrastructure.database.repositories.order_attribution_result_repo import (
    OrderAttributionResultRepository,
)
from src.infrastructure.database.repositories.order_repo import OrderRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository


@dataclass(frozen=True)
class _ResolvedCandidate:
    owner_type: str
    owner_source: str
    partner_account_id: UUID | None
    partner_code_id: UUID | None
    winning_touchpoint_id: UUID | None
    winning_binding_id: UUID | None
    rule_path: list[str]


class ResolveOrderAttributionUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._results = OrderAttributionResultRepository(session)
        self._touchpoints = AttributionTouchpointRepository(session)
        self._bindings = CustomerCommercialBindingRepository(session)
        self._partners = PartnerRepository(session)
        self._outbox = EventOutboxService(session)

    async def execute(
        self,
        *,
        order_id: UUID,
        commit: bool = True,
    ) -> OrderAttributionResultModel:
        existing = await self._results.get_by_order_id(order_id)
        if existing is not None:
            return existing

        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        touchpoints = await self._touchpoints.list_for_resolution_context(
            quote_session_id=order.quote_session_id,
            checkout_session_id=order.checkout_session_id,
            order_id=order.id,
        )
        bindings = await self._bindings.list_active_for_user(
            user_id=order.user_id,
            storefront_id=order.storefront_id,
        )

        candidate = await self._resolve_candidate(order=order, touchpoints=touchpoints, bindings=bindings)
        evidence_snapshot = _build_evidence_snapshot(
            order=order,
            touchpoints=touchpoints,
            bindings=bindings,
            candidate=candidate,
        )
        explainability_snapshot = _build_explainability_snapshot(
            order=order,
            touchpoints=touchpoints,
            bindings=bindings,
            candidate=candidate,
        )
        policy_snapshot = {
            "resolver_version": "phase3_t3_3_v1",
            "order_policy_snapshot": dict(order.policy_snapshot or {}),
        }

        model = OrderAttributionResultModel(
            order_id=order.id,
            user_id=order.user_id,
            auth_realm_id=order.auth_realm_id,
            storefront_id=order.storefront_id,
            owner_type=candidate.owner_type if candidate is not None else CommercialOwnerType.NONE.value,
            owner_source=candidate.owner_source if candidate is not None else None,
            partner_account_id=candidate.partner_account_id if candidate is not None else None,
            partner_code_id=candidate.partner_code_id if candidate is not None else None,
            winning_touchpoint_id=candidate.winning_touchpoint_id if candidate is not None else None,
            winning_binding_id=candidate.winning_binding_id if candidate is not None else None,
            rule_path=candidate.rule_path if candidate is not None else ["no_owner_resolved"],
            evidence_snapshot=evidence_snapshot,
            explainability_snapshot=explainability_snapshot,
            policy_snapshot=policy_snapshot,
            resolved_at=datetime.now(UTC),
        )
        created = await self._results.create(model)
        await self._outbox.append_event(
            event_name="attribution.result.finalized",
            aggregate_type="order_attribution_result",
            aggregate_id=str(created.id),
            partition_key=str(order.user_id),
            event_payload={
                "order_id": str(order.id),
                "result_id": str(created.id),
                "owner_type": created.owner_type,
                "owner_source": created.owner_source,
                "partner_account_id": str(created.partner_account_id) if created.partner_account_id else None,
                "partner_code_id": str(created.partner_code_id) if created.partner_code_id else None,
                "winning_touchpoint_id": str(created.winning_touchpoint_id) if created.winning_touchpoint_id else None,
                "winning_binding_id": str(created.winning_binding_id) if created.winning_binding_id else None,
            },
            source_context={
                "source_use_case": "ResolveOrderAttributionUseCase",
                "order_id": str(order.id),
            },
        )
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        return created

    async def _resolve_candidate(
        self,
        *,
        order: OrderModel,
        touchpoints: list[AttributionTouchpointModel],
        bindings: list[CustomerCommercialBindingModel],
    ) -> _ResolvedCandidate | None:
        binding_by_type = _latest_binding_by_type(bindings)
        explicit_touchpoint = _latest_touchpoint(touchpoints, touchpoint_type="explicit_code")
        passive_click = _latest_touchpoint(touchpoints, touchpoint_type="passive_click")

        if binding_by_type.manual_override is not None:
            return _candidate_from_binding(
                binding_by_type.manual_override,
                owner_source=CommercialOwnerSource.MANUAL_OVERRIDE.value,
                rule_path=["manual_override_binding_selected"],
            )

        if binding_by_type.contract_assignment is not None:
            return _candidate_from_binding(
                binding_by_type.contract_assignment,
                owner_source=CommercialOwnerSource.CONTRACT_ASSIGNMENT.value,
                rule_path=["contract_assignment_binding_selected"],
            )

        if explicit_touchpoint is not None:
            return await self._candidate_from_touchpoint(
                explicit_touchpoint,
                owner_source=CommercialOwnerSource.EXPLICIT_CODE.value,
                fallback_rule_path=["explicit_code_touchpoint_selected"],
            )

        if binding_by_type.reseller_binding is not None:
            return _candidate_from_binding(
                binding_by_type.reseller_binding,
                owner_source=CommercialOwnerSource.PERSISTENT_RESELLER_BINDING.value,
                rule_path=["persistent_reseller_binding_selected"],
            )

        if passive_click is not None:
            return await self._candidate_from_touchpoint(
                passive_click,
                owner_source=CommercialOwnerSource.PASSIVE_CLICK.value,
                fallback_rule_path=["passive_click_touchpoint_selected"],
            )

        if binding_by_type.storefront_default is not None:
            rule_path = ["storefront_default_binding_selected"]
            if binding_by_type.storefront_default.storefront_id == order.storefront_id:
                rule_path.append("storefront_scoped_default_owner")
            return _candidate_from_binding(
                binding_by_type.storefront_default,
                owner_source=CommercialOwnerSource.STOREFRONT_DEFAULT.value,
                rule_path=rule_path,
            )

        return None

    async def _candidate_from_touchpoint(
        self,
        touchpoint: AttributionTouchpointModel,
        *,
        owner_source: str,
        fallback_rule_path: list[str],
    ) -> _ResolvedCandidate:
        if touchpoint.partner_code_id is None:
            raise ValueError("Touchpoint selected for attribution is missing partner_code_id")
        code_model = await self._partners.get_code_by_id(touchpoint.partner_code_id)
        if code_model is None:
            raise ValueError("Partner code referenced by touchpoint was not found")
        owner_type = _infer_owner_type_from_code(code_model)
        rule_path = list(fallback_rule_path)
        if owner_type == CommercialOwnerType.RESELLER.value:
            rule_path.append("owner_type_inferred_from_partner_account")
        else:
            rule_path.append("owner_type_inferred_as_affiliate")
        return _ResolvedCandidate(
            owner_type=owner_type,
            owner_source=owner_source,
            partner_account_id=code_model.partner_account_id,
            partner_code_id=code_model.id,
            winning_touchpoint_id=touchpoint.id,
            winning_binding_id=None,
            rule_path=rule_path,
        )


@dataclass(frozen=True)
class _BindingSelections:
    manual_override: CustomerCommercialBindingModel | None
    contract_assignment: CustomerCommercialBindingModel | None
    reseller_binding: CustomerCommercialBindingModel | None
    storefront_default: CustomerCommercialBindingModel | None


def _latest_binding_by_type(bindings: list[CustomerCommercialBindingModel]) -> _BindingSelections:
    def _pick(binding_type: str) -> CustomerCommercialBindingModel | None:
        for binding in bindings:
            if binding.binding_type == binding_type:
                return binding
        return None

    return _BindingSelections(
        manual_override=_pick(CustomerCommercialBindingType.MANUAL_OVERRIDE.value),
        contract_assignment=_pick(CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value),
        reseller_binding=_pick(CustomerCommercialBindingType.RESELLER_BINDING.value),
        storefront_default=_pick(CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value),
    )


def _latest_touchpoint(
    touchpoints: list[AttributionTouchpointModel],
    *,
    touchpoint_type: str,
) -> AttributionTouchpointModel | None:
    matching = [touchpoint for touchpoint in touchpoints if touchpoint.touchpoint_type == touchpoint_type]
    if not matching:
        return None
    return sorted(
        matching,
        key=lambda item: (
            _normalize_utc(item.occurred_at),
            _normalize_utc(item.created_at),
        ),
    )[-1]


def _candidate_from_binding(
    binding: CustomerCommercialBindingModel,
    *,
    owner_source: str,
    rule_path: list[str],
) -> _ResolvedCandidate:
    return _ResolvedCandidate(
        owner_type=binding.owner_type,
        owner_source=owner_source,
        partner_account_id=binding.partner_account_id,
        partner_code_id=binding.partner_code_id,
        winning_touchpoint_id=None,
        winning_binding_id=binding.id,
        rule_path=rule_path,
    )


def _infer_owner_type_from_code(code_model: PartnerCodeModel) -> str:
    if code_model.partner_account_id is not None:
        return CommercialOwnerType.RESELLER.value
    return CommercialOwnerType.AFFILIATE.value


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_evidence_snapshot(
    *,
    order: OrderModel,
    touchpoints: list[AttributionTouchpointModel],
    bindings: list[CustomerCommercialBindingModel],
    candidate: _ResolvedCandidate | None,
) -> dict:
    return {
        "order_context": {
            "order_id": str(order.id),
            "quote_session_id": str(order.quote_session_id) if order.quote_session_id else None,
            "checkout_session_id": str(order.checkout_session_id),
            "partner_code_id": str(order.partner_code_id) if order.partner_code_id else None,
            "storefront_id": str(order.storefront_id),
        },
        "touchpoint_ids": [str(item.id) for item in touchpoints],
        "binding_ids": [str(item.id) for item in bindings],
        "winning_touchpoint_id": str(candidate.winning_touchpoint_id) if candidate else None,
        "winning_binding_id": str(candidate.winning_binding_id) if candidate else None,
    }


def _build_explainability_snapshot(
    *,
    order: OrderModel,
    touchpoints: list[AttributionTouchpointModel],
    bindings: list[CustomerCommercialBindingModel],
    candidate: _ResolvedCandidate | None,
) -> dict:
    return {
        "resolution_precedence": [
            "manual_override",
            "contract_assignment",
            "explicit_code",
            "persistent_reseller_binding",
            "passive_click",
            "storefront_default",
            "none",
        ],
        "winning_candidate": (
            {
                "owner_type": candidate.owner_type,
                "owner_source": candidate.owner_source,
                "partner_account_id": str(candidate.partner_account_id) if candidate.partner_account_id else None,
                "partner_code_id": str(candidate.partner_code_id) if candidate.partner_code_id else None,
                "winning_touchpoint_id": (
                    str(candidate.winning_touchpoint_id) if candidate.winning_touchpoint_id else None
                ),
                "winning_binding_id": str(candidate.winning_binding_id) if candidate.winning_binding_id else None,
                "rule_path": list(candidate.rule_path),
            }
            if candidate is not None
            else None
        ),
        "evaluated_touchpoints": [
            {
                "id": str(touchpoint.id),
                "touchpoint_type": touchpoint.touchpoint_type,
                "partner_code_id": str(touchpoint.partner_code_id) if touchpoint.partner_code_id else None,
                "occurred_at": _normalize_utc(touchpoint.occurred_at).isoformat(),
                "campaign_params": dict(touchpoint.campaign_params or {}),
                "evidence_payload": dict(touchpoint.evidence_payload or {}),
            }
            for touchpoint in touchpoints
        ],
        "evaluated_bindings": [
            {
                "id": str(binding.id),
                "binding_type": binding.binding_type,
                "owner_type": binding.owner_type,
                "partner_account_id": str(binding.partner_account_id) if binding.partner_account_id else None,
                "partner_code_id": str(binding.partner_code_id) if binding.partner_code_id else None,
                "storefront_id": str(binding.storefront_id) if binding.storefront_id else None,
                "effective_from": _normalize_utc(binding.effective_from).isoformat(),
                "reason_code": binding.reason_code,
            }
            for binding in bindings
        ],
        "order_snapshot_refs": {
            "merchant_snapshot_present": bool(order.merchant_snapshot),
            "pricing_snapshot_present": bool(order.pricing_snapshot),
            "policy_snapshot_present": bool(order.policy_snapshot),
        },
    }
