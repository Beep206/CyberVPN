from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService
from src.application.use_cases.settlement.commission_terms import (
    attach_commission_contract_snapshot,
    build_incomplete_commission_contract_snapshot,
    with_commission_snapshot_currency,
)
from src.domain.enums import (
    AttributionTouchpointType,
    CommercialOwnerSource,
    CommercialOwnerType,
    CustomerCommercialBindingStatus,
    CustomerCommercialBindingType,
)
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
from src.infrastructure.monitoring.instrumentation.partner_runtime import (
    CUSTOMER_COMMERCE_SURFACE,
    log_partner_runtime_event,
    observe_partner_attribution_resolution,
    partner_runtime_timer,
)


@dataclass(frozen=True)
class _ResolvedCandidate:
    owner_type: str
    owner_source: str
    partner_account_id: UUID | None
    partner_code_id: UUID | None
    attribution_session_id: UUID | None
    policy_version_id: UUID | None
    commission_contract_id: UUID | None
    winning_touchpoint_id: UUID | None
    winning_binding_id: UUID | None
    attribution_model: str | None
    commercial_policy_snapshot: dict
    rule_path: list[str]


@dataclass(frozen=True)
class _TouchpointEvaluation:
    touchpoint: AttributionTouchpointModel
    eligible: bool
    reason_codes: tuple[str, ...]
    policy_reason_codes: tuple[str, ...]
    attribution_model: str


@dataclass(frozen=True)
class _BindingEvaluation:
    binding: CustomerCommercialBindingModel
    eligible: bool
    reason_codes: tuple[str, ...]


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
        started_at = partner_runtime_timer()
        existing = await self._results.get_by_order_id(order_id)
        if existing is not None:
            observe_partner_attribution_resolution(
                surface=CUSTOMER_COMMERCE_SURFACE,
                owner_type=existing.owner_type or "none",
                owner_source=existing.owner_source or "none",
                result="cached",
                reason="already_resolved",
                duration_seconds=0.0,
            )
            return existing

        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise ValueError("Order not found")

        touchpoints = await self._touchpoints.list_for_resolution_context(
            quote_session_id=order.quote_session_id,
            checkout_session_id=order.checkout_session_id,
            order_id=order.id,
        )
        bindings = await self._bindings.list_active_candidates_for_user(
            user_id=order.user_id,
            auth_realm_id=order.auth_realm_id,
        )

        candidate = await self._resolve_candidate(order=order, touchpoints=touchpoints, bindings=bindings)
        candidate = await self._ensure_candidate_commission_snapshot(
            candidate,
            order_currency_code=order.currency_code,
        )
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
            "resolved_attribution_model": candidate.attribution_model if candidate is not None else None,
            "commercial_policy_snapshot": (
                _safe_policy_snapshot(candidate.commercial_policy_snapshot) if candidate is not None else {}
            ),
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
            attribution_session_id=candidate.attribution_session_id if candidate is not None else None,
            policy_version_id=candidate.policy_version_id if candidate is not None else None,
            commission_contract_id=candidate.commission_contract_id if candidate is not None else None,
            winning_touchpoint_id=candidate.winning_touchpoint_id if candidate is not None else None,
            winning_binding_id=candidate.winning_binding_id if candidate is not None else None,
            rule_path=candidate.rule_path if candidate is not None else ["no_owner_resolved"],
            evidence_snapshot=evidence_snapshot,
            explainability_snapshot=explainability_snapshot,
            policy_snapshot=policy_snapshot,
            resolved_at=datetime.now(UTC),
        )
        try:
            async with self._session.begin_nested():
                created = await self._results.create(model)
                await self._append_result_finalized_event(created)
        except IntegrityError:
            existing = await self._results.get_by_order_id(order_id)
            if existing is None:
                raise
            observe_partner_attribution_resolution(
                surface=CUSTOMER_COMMERCE_SURFACE,
                owner_type=existing.owner_type or "none",
                owner_source=existing.owner_source or "none",
                result="cached",
                reason="concurrent_resolution_won",
                duration_seconds=0.0,
            )
            return existing
        if commit:
            await self._session.commit()
            await self._session.refresh(created)
        duration_seconds = max(partner_runtime_timer() - started_at, 0.0)
        observe_partner_attribution_resolution(
            surface=CUSTOMER_COMMERCE_SURFACE,
            owner_type=created.owner_type or "none",
            owner_source=created.owner_source or "none",
            result="success",
            reason="resolved" if created.owner_type != CommercialOwnerType.NONE.value else "no_owner_resolved",
            duration_seconds=duration_seconds,
        )
        log_partner_runtime_event(
            "partner_attribution.resolved",
            surface=CUSTOMER_COMMERCE_SURFACE,
            route_group="attribution",
            owner_type=created.owner_type,
            owner_source=created.owner_source,
            order_id=str(order.id),
            result="success",
        )
        return created

    async def _append_result_finalized_event(self, created: OrderAttributionResultModel) -> None:
        await self._outbox.append_event(
            event_name="attribution.result.finalized",
            aggregate_type="order_attribution_result",
            aggregate_id=str(created.id),
            partition_key=str(created.user_id),
            event_payload={
                "order_id": str(created.order_id),
                "result_id": str(created.id),
                "owner_type": created.owner_type,
                "owner_source": created.owner_source,
                "partner_account_id": str(created.partner_account_id) if created.partner_account_id else None,
                "partner_code_id": str(created.partner_code_id) if created.partner_code_id else None,
                "attribution_session_id": str(created.attribution_session_id)
                if created.attribution_session_id
                else None,
                "policy_version_id": str(created.policy_version_id) if created.policy_version_id else None,
                "commission_contract_id": str(created.commission_contract_id)
                if created.commission_contract_id
                else None,
                "winning_touchpoint_id": str(created.winning_touchpoint_id) if created.winning_touchpoint_id else None,
                "winning_binding_id": str(created.winning_binding_id) if created.winning_binding_id else None,
            },
            source_context={
                "source_use_case": "ResolveOrderAttributionUseCase",
                "order_id": str(created.order_id),
            },
        )

    async def _resolve_candidate(
        self,
        *,
        order: OrderModel,
        touchpoints: list[AttributionTouchpointModel],
        bindings: list[CustomerCommercialBindingModel],
    ) -> _ResolvedCandidate | None:
        eligible_bindings = [
            evaluation.binding
            for evaluation in _evaluate_bindings(order=order, bindings=bindings)
            if evaluation.eligible
        ]
        exact_storefront_immutable_binding = _exact_storefront_binding(
            order=order,
            bindings=eligible_bindings,
            binding_types=_GLOBAL_IMMUTABLE_BINDING_TYPES,
        )
        if exact_storefront_immutable_binding is not None:
            return _candidate_from_binding(
                exact_storefront_immutable_binding.binding,
                owner_source=exact_storefront_immutable_binding.owner_source,
                rule_path=exact_storefront_immutable_binding.rule_path,
            )

        global_immutable_binding = _global_immutable_binding(eligible_bindings)
        if global_immutable_binding is not None:
            return _candidate_from_binding(
                global_immutable_binding.binding,
                owner_source=global_immutable_binding.owner_source,
                rule_path=global_immutable_binding.rule_path,
            )

        exact_storefront_binding = _exact_storefront_binding(order=order, bindings=eligible_bindings)
        if exact_storefront_binding is not None:
            return _candidate_from_binding(
                exact_storefront_binding.binding,
                owner_source=exact_storefront_binding.owner_source,
                rule_path=exact_storefront_binding.rule_path,
            )

        global_partner_attribution = _global_binding_by_type(
            eligible_bindings,
            CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value,
        )
        if global_partner_attribution is not None:
            return _candidate_from_binding(
                global_partner_attribution.binding,
                owner_source=global_partner_attribution.owner_source,
                rule_path=global_partner_attribution.rule_path,
            )

        eligible_touchpoints = [
            evaluation.touchpoint
            for evaluation in _evaluate_touchpoints(order=order, touchpoints=touchpoints)
            if evaluation.eligible
        ]
        touchpoint_candidate, touchpoint_strategy = _select_touchpoint_candidate(eligible_touchpoints)

        if touchpoint_candidate is not None and touchpoint_candidate.touchpoint_type == "explicit_code":
            return await self._candidate_from_touchpoint(
                touchpoint_candidate,
                owner_source=_owner_source_for_touchpoint(touchpoint_candidate),
                fallback_rule_path=[
                    f"{touchpoint_strategy}_strategy_selected",
                    "explicit_code_touchpoint_selected",
                ],
            )

        global_reseller_binding = _global_binding_by_type(
            eligible_bindings,
            CustomerCommercialBindingType.RESELLER_BINDING.value,
        )
        if global_reseller_binding is not None:
            return _candidate_from_binding(
                global_reseller_binding.binding,
                owner_source=global_reseller_binding.owner_source,
                rule_path=global_reseller_binding.rule_path,
            )

        if touchpoint_candidate is not None:
            return await self._candidate_from_touchpoint(
                touchpoint_candidate,
                owner_source=_owner_source_for_touchpoint(touchpoint_candidate),
                fallback_rule_path=[
                    f"{touchpoint_strategy}_strategy_selected",
                    f"{touchpoint_candidate.touchpoint_type}_touchpoint_selected",
                ],
            )

        global_storefront_default = _global_binding_by_type(
            eligible_bindings,
            CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value,
        )
        if global_storefront_default is not None:
            return _candidate_from_binding(
                global_storefront_default.binding,
                owner_source=global_storefront_default.owner_source,
                rule_path=global_storefront_default.rule_path,
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
        policy_snapshot = _policy_snapshot_from_touchpoint(touchpoint)
        owner_type = _owner_type_from_snapshot(policy_snapshot) or _infer_owner_type_from_code(code_model)
        partner_account_id = (
            _uuid_from_snapshot(policy_snapshot.get("partner_account_id")) or code_model.partner_account_id
        )
        commission_contract_id = (
            _uuid_from_snapshot(policy_snapshot.get("commission_contract_id")) or code_model.commission_contract_id
        )
        policy_version_id = (
            _uuid_from_snapshot(policy_snapshot.get("policy_version_id")) or touchpoint.policy_version_id
        )
        rule_path = list(fallback_rule_path)
        rule_path.append("owner_policy_loaded_from_immutable_touchpoint_snapshot")
        return _ResolvedCandidate(
            owner_type=owner_type,
            owner_source=owner_source,
            partner_account_id=partner_account_id,
            partner_code_id=code_model.id,
            attribution_session_id=touchpoint.partner_attribution_session_id,
            policy_version_id=policy_version_id or code_model.policy_version_id,
            commission_contract_id=commission_contract_id,
            winning_touchpoint_id=touchpoint.id,
            winning_binding_id=None,
            attribution_model=str(policy_snapshot.get("attribution_model") or code_model.attribution_model),
            commercial_policy_snapshot=policy_snapshot,
            rule_path=rule_path,
        )

    async def _ensure_candidate_commission_snapshot(
        self,
        candidate: _ResolvedCandidate | None,
        *,
        order_currency_code: str | None,
    ) -> _ResolvedCandidate | None:
        if candidate is None or candidate.owner_type == CommercialOwnerType.NONE.value:
            return candidate
        commercial_snapshot = dict(candidate.commercial_policy_snapshot or {})
        existing_snapshot = commercial_snapshot.get("commission_contract_snapshot")
        if isinstance(existing_snapshot, dict) and existing_snapshot.get("snapshot_complete") is True:
            order_currency = str(order_currency_code or "").upper()
            if order_currency and str(existing_snapshot.get("currency_code") or "").upper() != order_currency:
                enriched_snapshot = attach_commission_contract_snapshot(
                    commercial_snapshot,
                    with_commission_snapshot_currency(existing_snapshot, currency_code=order_currency),
                )
                rule_path = list(candidate.rule_path)
                if "commission_contract_snapshot_currency_scoped_to_order" not in rule_path:
                    rule_path.append("commission_contract_snapshot_currency_scoped_to_order")
                return replace(
                    candidate,
                    commercial_policy_snapshot=enriched_snapshot,
                    rule_path=rule_path,
                )
            return candidate
        if isinstance(existing_snapshot, dict):
            return candidate

        code_model = (
            await self._partners.get_code_by_id(candidate.partner_code_id)
            if candidate.partner_code_id is not None
            else None
        )

        enriched_snapshot = attach_commission_contract_snapshot(
            commercial_snapshot,
            build_incomplete_commission_contract_snapshot(
                missing_terms=["commission_contract_snapshot"],
                snapshot_source="order_attribution_missing_snapshot",
                commission_contract_id=candidate.commission_contract_id,
                partner_account_id=candidate.partner_account_id,
                partner_user_id=code_model.partner_user_id if code_model is not None else None,
                partner_code_id=candidate.partner_code_id,
                owner_type=candidate.owner_type,
            ),
        )
        rule_path = list(candidate.rule_path)
        if "commission_contract_snapshot_incomplete" not in rule_path:
            rule_path.append("commission_contract_snapshot_incomplete")
        return replace(
            candidate,
            commercial_policy_snapshot=enriched_snapshot,
            rule_path=rule_path,
        )


@dataclass(frozen=True)
class _BindingSelections:
    manual_override: CustomerCommercialBindingModel | None
    contract_assignment: CustomerCommercialBindingModel | None
    partner_attribution: CustomerCommercialBindingModel | None
    reseller_binding: CustomerCommercialBindingModel | None
    storefront_default: CustomerCommercialBindingModel | None


@dataclass(frozen=True)
class _SelectedBinding:
    binding: CustomerCommercialBindingModel
    owner_source: str
    rule_path: list[str]


def _latest_binding_by_type(bindings: list[CustomerCommercialBindingModel]) -> _BindingSelections:
    def _pick(binding_type: str) -> CustomerCommercialBindingModel | None:
        for binding in bindings:
            if binding.binding_type == binding_type:
                return binding
        return None

    return _BindingSelections(
        manual_override=_pick(CustomerCommercialBindingType.MANUAL_OVERRIDE.value),
        contract_assignment=_pick(CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value),
        partner_attribution=_pick(CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value),
        reseller_binding=_pick(CustomerCommercialBindingType.RESELLER_BINDING.value),
        storefront_default=_pick(CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value),
    )


_GLOBAL_IMMUTABLE_BINDING_TYPES = frozenset(
    {
        CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
        CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value,
    }
)


def _binding_selection_by_type(bindings: list[CustomerCommercialBindingModel]) -> _BindingSelections:
    return _latest_binding_by_type(bindings)


def _selected_binding_from_model(
    binding: CustomerCommercialBindingModel,
    *,
    rule_prefix: str | None = None,
) -> _SelectedBinding:
    if binding.binding_type == CustomerCommercialBindingType.MANUAL_OVERRIDE.value:
        owner_source = CommercialOwnerSource.MANUAL_OVERRIDE.value
        rule_path = ["manual_override_binding_selected"]
    elif binding.binding_type == CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value:
        owner_source = CommercialOwnerSource.CONTRACT_ASSIGNMENT.value
        rule_path = ["contract_assignment_binding_selected"]
    elif binding.binding_type == CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value:
        owner_source = CommercialOwnerSource.CLAIMED_COMMERCIAL_BINDING.value
        rule_path = ["claimed_commercial_binding_selected"]
    elif binding.binding_type == CustomerCommercialBindingType.RESELLER_BINDING.value:
        owner_source = CommercialOwnerSource.PERSISTENT_RESELLER_BINDING.value
        rule_path = ["persistent_reseller_binding_selected"]
    elif binding.binding_type == CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value:
        owner_source = CommercialOwnerSource.STOREFRONT_DEFAULT.value
        rule_path = ["storefront_default_binding_selected"]
    else:
        owner_source = binding.binding_type
        rule_path = [f"{binding.binding_type}_binding_selected"]
    if rule_prefix is not None:
        rule_path = [rule_prefix, *rule_path]
    return _SelectedBinding(binding=binding, owner_source=owner_source, rule_path=rule_path)


def _first_selected_binding(selection: _BindingSelections) -> _SelectedBinding | None:
    for binding in (
        selection.manual_override,
        selection.contract_assignment,
        selection.partner_attribution,
        selection.reseller_binding,
        selection.storefront_default,
    ):
        if binding is not None:
            return _selected_binding_from_model(binding)
    return None


def _exact_storefront_binding(
    *,
    order: OrderModel,
    bindings: list[CustomerCommercialBindingModel],
    binding_types: frozenset[str] | None = None,
) -> _SelectedBinding | None:
    storefront_id = getattr(order, "storefront_id", None)
    if storefront_id is None:
        return None
    exact_bindings = [
        binding
        for binding in bindings
        if binding.storefront_id == storefront_id and (binding_types is None or binding.binding_type in binding_types)
    ]
    selected = _first_selected_binding(_binding_selection_by_type(exact_bindings))
    if selected is None:
        return None
    return _selected_binding_from_model(selected.binding, rule_prefix="exact_storefront_binding_selected")


def _global_immutable_binding(bindings: list[CustomerCommercialBindingModel]) -> _SelectedBinding | None:
    global_bindings = [
        binding
        for binding in bindings
        if binding.storefront_id is None and binding.binding_type in _GLOBAL_IMMUTABLE_BINDING_TYPES
    ]
    selected = _first_selected_binding(_binding_selection_by_type(global_bindings))
    if selected is None:
        return None
    return _selected_binding_from_model(selected.binding, rule_prefix="global_immutable_binding_selected")


def _global_binding_by_type(
    bindings: list[CustomerCommercialBindingModel],
    binding_type: str,
) -> _SelectedBinding | None:
    selection = _binding_selection_by_type(
        [binding for binding in bindings if binding.storefront_id is None and binding.binding_type == binding_type]
    )
    selected = _first_selected_binding(selection)
    if selected is None:
        return None
    return _selected_binding_from_model(selected.binding)


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


_ELIGIBLE_TOUCHPOINT_TYPES = frozenset(
    {
        AttributionTouchpointType.EXPLICIT_CODE.value,
        AttributionTouchpointType.PASSIVE_CLICK.value,
        AttributionTouchpointType.DEEP_LINK.value,
        AttributionTouchpointType.QR_SCAN.value,
        AttributionTouchpointType.CAMPAIGN_PARAMS.value,
    }
)
_CLICK_TOUCHPOINT_TYPES = frozenset(
    {
        AttributionTouchpointType.PASSIVE_CLICK.value,
        AttributionTouchpointType.DEEP_LINK.value,
        AttributionTouchpointType.QR_SCAN.value,
        AttributionTouchpointType.CAMPAIGN_PARAMS.value,
    }
)
_SUPPORTED_TOUCHPOINT_STRATEGIES = frozenset(
    {
        "first_eligible_touch",
        "last_eligible_touch",
        "last_eligible_click",
        "explicit_code_priority",
        "persistent_storefront_binding",
    }
)
_BINDING_PRECEDENCE_RANK = {
    CustomerCommercialBindingType.MANUAL_OVERRIDE.value: 10,
    CustomerCommercialBindingType.CONTRACT_ASSIGNMENT.value: 20,
    CustomerCommercialBindingType.PARTNER_ATTRIBUTION.value: 30,
    CustomerCommercialBindingType.RESELLER_BINDING.value: 50,
    CustomerCommercialBindingType.STOREFRONT_DEFAULT_OWNER.value: 70,
}


def _select_touchpoint_candidate(
    touchpoints: list[AttributionTouchpointModel],
) -> tuple[AttributionTouchpointModel | None, str]:
    candidates = [
        touchpoint
        for touchpoint in touchpoints
        if touchpoint.partner_code_id is not None
        and touchpoint.touchpoint_type in _ELIGIBLE_TOUCHPOINT_TYPES
        and _touchpoint_policy_allows_resolution(touchpoint)
    ]
    if not candidates:
        return None, "explicit_code_priority"

    strategy = _resolve_touchpoint_strategy(candidates)
    if strategy == "first_eligible_touch":
        return _first_touchpoint(candidates), strategy
    if strategy == "last_eligible_touch":
        return _last_touchpoint(candidates), strategy
    if strategy == "last_eligible_click":
        click_candidate = _last_touchpoint(
            [touchpoint for touchpoint in candidates if touchpoint.touchpoint_type in _CLICK_TOUCHPOINT_TYPES]
        )
        return click_candidate, strategy

    explicit_candidate = _last_touchpoint(
        [
            touchpoint
            for touchpoint in candidates
            if touchpoint.touchpoint_type == AttributionTouchpointType.EXPLICIT_CODE.value
        ]
    )
    if explicit_candidate is not None:
        return explicit_candidate, strategy
    return _last_touchpoint(candidates), strategy


def _evaluate_touchpoints(
    *,
    order: OrderModel,
    touchpoints: list[AttributionTouchpointModel],
) -> list[_TouchpointEvaluation]:
    return [
        _TouchpointEvaluation(
            touchpoint=touchpoint,
            eligible=not reason_codes,
            reason_codes=tuple(reason_codes),
            policy_reason_codes=tuple(_policy_reason_codes_from_touchpoint(touchpoint)),
            attribution_model=_touchpoint_attribution_model(touchpoint),
        )
        for touchpoint in touchpoints
        for reason_codes in [_touchpoint_exclusion_reasons(order=order, touchpoint=touchpoint)]
    ]


def _touchpoint_exclusion_reasons(
    *,
    order: OrderModel,
    touchpoint: AttributionTouchpointModel,
) -> list[str]:
    reason_codes: list[str] = []
    order_realm_id = getattr(order, "auth_realm_id", None)
    if order_realm_id is not None and touchpoint.auth_realm_id != order_realm_id:
        reason_codes.append("wrong_realm")
    if touchpoint.partner_code_id is None:
        reason_codes.append("missing_partner_code")
    if touchpoint.touchpoint_type not in _ELIGIBLE_TOUCHPOINT_TYPES:
        reason_codes.append("unsupported_touchpoint_type")
    if touchpoint.storefront_id is not None and touchpoint.storefront_id != order.storefront_id:
        reason_codes.append("wrong_storefront")

    snapshot = _policy_snapshot_from_touchpoint(touchpoint)
    policy_reason_codes = _policy_reason_codes_from_snapshot(snapshot)
    if snapshot.get("allowed") is False:
        reason_codes.extend(policy_reason_codes or ["policy_denied"])
    elif policy_reason_codes:
        reason_codes.extend(policy_reason_codes)

    expires_at = _touchpoint_expires_at(touchpoint)
    if expires_at is not None and expires_at <= _resolution_time(order):
        reason_codes.append("attribution_window_expired")
    return _dedupe_reason_codes(reason_codes)


def _evaluate_bindings(
    *,
    order: OrderModel,
    bindings: list[CustomerCommercialBindingModel],
) -> list[_BindingEvaluation]:
    return [
        _BindingEvaluation(
            binding=binding,
            eligible=not reason_codes,
            reason_codes=tuple(reason_codes),
        )
        for binding in bindings
        for reason_codes in [_binding_exclusion_reasons(order=order, binding=binding)]
    ]


def _binding_exclusion_reasons(
    *,
    order: OrderModel,
    binding: CustomerCommercialBindingModel,
) -> list[str]:
    reason_codes: list[str] = []
    resolution_time = _resolution_time(order)
    order_realm_id = getattr(order, "auth_realm_id", None)
    if order_realm_id is not None and binding.auth_realm_id != order_realm_id:
        reason_codes.append("wrong_realm")
    if binding.binding_status != CustomerCommercialBindingStatus.ACTIVE.value:
        reason_codes.append("inactive_binding")
    if binding.storefront_id is not None and binding.storefront_id != order.storefront_id:
        reason_codes.append("wrong_storefront")
    if _normalize_utc(binding.effective_from) > resolution_time:
        reason_codes.append("binding_not_yet_effective")
    if binding.effective_to is not None and _normalize_utc(binding.effective_to) <= resolution_time:
        reason_codes.append("binding_expired")
    return _dedupe_reason_codes(reason_codes)


def _resolve_touchpoint_strategy(touchpoints: list[AttributionTouchpointModel]) -> str:
    if any(
        touchpoint.touchpoint_type == AttributionTouchpointType.EXPLICIT_CODE.value
        and _touchpoint_attribution_model(touchpoint) == "explicit_code_priority"
        for touchpoint in touchpoints
    ):
        return "explicit_code_priority"
    for strategy in (
        "first_eligible_touch",
        "last_eligible_click",
        "persistent_storefront_binding",
    ):
        if any(_touchpoint_attribution_model(touchpoint) == strategy for touchpoint in touchpoints):
            return strategy
    if any(touchpoint.touchpoint_type == AttributionTouchpointType.EXPLICIT_CODE.value for touchpoint in touchpoints):
        return "explicit_code_priority"
    if any(_touchpoint_attribution_model(touchpoint) == "last_eligible_touch" for touchpoint in touchpoints):
        return "last_eligible_touch"
    return "explicit_code_priority"


def _first_touchpoint(touchpoints: list[AttributionTouchpointModel]) -> AttributionTouchpointModel | None:
    if not touchpoints:
        return None
    return sorted(touchpoints, key=lambda item: (_normalize_utc(item.occurred_at), _normalize_utc(item.created_at)))[0]


def _last_touchpoint(touchpoints: list[AttributionTouchpointModel]) -> AttributionTouchpointModel | None:
    if not touchpoints:
        return None
    return sorted(touchpoints, key=lambda item: (_normalize_utc(item.occurred_at), _normalize_utc(item.created_at)))[-1]


def _owner_source_for_touchpoint(touchpoint: AttributionTouchpointModel) -> str:
    if touchpoint.touchpoint_type == AttributionTouchpointType.EXPLICIT_CODE.value:
        return CommercialOwnerSource.EXPLICIT_CODE.value
    return CommercialOwnerSource.PASSIVE_CLICK.value


def _candidate_from_binding(
    binding: CustomerCommercialBindingModel,
    *,
    owner_source: str,
    rule_path: list[str],
) -> _ResolvedCandidate:
    commercial_policy_snapshot = dict((binding.evidence_payload or {}).get("policy_snapshot") or {})
    return _ResolvedCandidate(
        owner_type=binding.owner_type,
        owner_source=owner_source,
        partner_account_id=binding.partner_account_id,
        partner_code_id=binding.partner_code_id,
        attribution_session_id=binding.attribution_session_id,
        policy_version_id=binding.policy_version_id,
        commission_contract_id=binding.commission_contract_id,
        winning_touchpoint_id=None,
        winning_binding_id=binding.id,
        attribution_model=str(commercial_policy_snapshot.get("attribution_model") or ""),
        commercial_policy_snapshot=commercial_policy_snapshot,
        rule_path=rule_path,
    )


def _infer_owner_type_from_code(code_model: PartnerCodeModel) -> str:
    owner_type = (code_model.owner_type or "").strip()
    if owner_type in {
        CommercialOwnerType.AFFILIATE.value,
        CommercialOwnerType.PERFORMANCE.value,
        CommercialOwnerType.RESELLER.value,
    }:
        return owner_type
    raise ValueError("Partner code owner_type is invalid")


def _owner_type_from_snapshot(policy_snapshot: dict) -> str | None:
    owner_type = str(policy_snapshot.get("owner_type") or "").strip()
    if not owner_type:
        return None
    if owner_type in {
        CommercialOwnerType.AFFILIATE.value,
        CommercialOwnerType.PERFORMANCE.value,
        CommercialOwnerType.RESELLER.value,
    }:
        return owner_type
    raise ValueError("Partner snapshot owner_type is invalid")


def _uuid_from_snapshot(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _policy_snapshot_from_touchpoint(touchpoint: AttributionTouchpointModel) -> dict:
    payload = dict(touchpoint.evidence_payload or {})
    snapshot = payload.get("policy_snapshot")
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def _policy_reason_codes_from_touchpoint(touchpoint: AttributionTouchpointModel) -> list[str]:
    return _policy_reason_codes_from_snapshot(_policy_snapshot_from_touchpoint(touchpoint))


def _policy_reason_codes_from_snapshot(snapshot: dict) -> list[str]:
    raw_reason_codes = snapshot.get("reason_codes")
    if not isinstance(raw_reason_codes, list):
        return []
    return [str(reason_code) for reason_code in raw_reason_codes if str(reason_code).strip()]


def _touchpoint_policy_allows_resolution(touchpoint: AttributionTouchpointModel) -> bool:
    snapshot = _policy_snapshot_from_touchpoint(touchpoint)
    if not snapshot:
        return True
    if snapshot.get("allowed") is False:
        return False
    return not bool(snapshot.get("reason_codes") or [])


def _touchpoint_attribution_model(touchpoint: AttributionTouchpointModel | None) -> str:
    if touchpoint is None:
        return "last_eligible_touch"
    snapshot = _policy_snapshot_from_touchpoint(touchpoint)
    attribution_model = str(snapshot.get("attribution_model") or "last_eligible_touch")
    if attribution_model in _SUPPORTED_TOUCHPOINT_STRATEGIES:
        return attribution_model
    return "last_eligible_touch"


def _touchpoint_expires_at(touchpoint: AttributionTouchpointModel) -> datetime | None:
    payload = dict(touchpoint.evidence_payload or {})
    snapshot = _policy_snapshot_from_touchpoint(touchpoint)
    for key in ("attribution_expires_at", "expires_at"):
        value = snapshot.get(key) or payload.get(key)
        parsed = _parse_snapshot_datetime(value)
        if parsed is not None:
            return parsed
    return None


def _parse_snapshot_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_utc(value)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return _normalize_utc(datetime.fromisoformat(normalized))
    except ValueError:
        return None


def _resolution_time(order: OrderModel) -> datetime:
    created_at = getattr(order, "created_at", None)
    if isinstance(created_at, datetime):
        return _normalize_utc(created_at)
    return datetime.now(UTC)


def _dedupe_reason_codes(reason_codes: list[str]) -> list[str]:
    deduped: list[str] = []
    for reason_code in reason_codes:
        normalized = str(reason_code).strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return deduped


def _serialize_touchpoint_evaluation(
    *,
    evaluation: _TouchpointEvaluation,
    candidate: _ResolvedCandidate | None,
    selected_strategy: str | None,
) -> dict:
    touchpoint = evaluation.touchpoint
    result = _touchpoint_evaluation_result(evaluation=evaluation, candidate=candidate)
    snapshot = _policy_snapshot_from_touchpoint(touchpoint)
    return {
        "candidate_kind": "touchpoint",
        "id": str(touchpoint.id),
        "result": result,
        "eligible": evaluation.eligible,
        "reason_codes": _touchpoint_result_reason_codes(
            evaluation=evaluation,
            candidate=candidate,
            result=result,
            selected_strategy=selected_strategy,
        ),
        "policy_reason_codes": list(evaluation.policy_reason_codes),
        "touchpoint_type": touchpoint.touchpoint_type,
        "attribution_model": evaluation.attribution_model,
        "selected_strategy": selected_strategy,
        "partner_code_id": str(touchpoint.partner_code_id) if touchpoint.partner_code_id else None,
        "attribution_session_id": (
            str(touchpoint.partner_attribution_session_id) if touchpoint.partner_attribution_session_id else None
        ),
        "policy_version_id": str(touchpoint.policy_version_id) if touchpoint.policy_version_id else None,
        "commission_contract_id": str(snapshot.get("commission_contract_id"))
        if snapshot.get("commission_contract_id")
        else None,
        "partner_account_id": str(snapshot.get("partner_account_id")) if snapshot.get("partner_account_id") else None,
        "storefront_id": str(touchpoint.storefront_id) if touchpoint.storefront_id else None,
        "occurred_at": _normalize_utc(touchpoint.occurred_at).isoformat(),
    }


def _touchpoint_evaluation_result(
    *,
    evaluation: _TouchpointEvaluation,
    candidate: _ResolvedCandidate | None,
) -> str:
    if candidate is not None and candidate.winning_touchpoint_id == evaluation.touchpoint.id:
        return "winner"
    if not evaluation.eligible:
        return "excluded"
    return "loser"


def _touchpoint_result_reason_codes(
    *,
    evaluation: _TouchpointEvaluation,
    candidate: _ResolvedCandidate | None,
    result: str,
    selected_strategy: str | None,
) -> list[str]:
    if result == "winner":
        return []
    if result == "excluded":
        return list(evaluation.reason_codes)
    if candidate is None:
        return ["no_owner_resolved"]
    if candidate.winning_binding_id is not None:
        return [f"lower_precedence_{candidate.owner_source or 'binding'}"]

    strategy = selected_strategy or "no_touchpoint_strategy"
    if strategy == "first_eligible_touch":
        return ["not_first_eligible_touch"]
    if strategy == "last_eligible_touch":
        return ["not_last_eligible_touch"]
    if strategy == "last_eligible_click":
        if evaluation.touchpoint.touchpoint_type not in _CLICK_TOUCHPOINT_TYPES:
            return ["not_click_touchpoint"]
        return ["not_last_eligible_click"]
    if strategy == "explicit_code_priority":
        if evaluation.touchpoint.touchpoint_type == AttributionTouchpointType.EXPLICIT_CODE.value:
            return ["older_explicit_code"]
        return ["explicit_code_priority_loser"]
    if strategy == "persistent_storefront_binding":
        return ["persistent_storefront_binding_strategy_loser"]
    return [f"not_selected_by_{strategy}"]


def _serialize_binding_evaluation(
    *,
    evaluation: _BindingEvaluation,
    candidate: _ResolvedCandidate | None,
) -> dict:
    binding = evaluation.binding
    result = _binding_evaluation_result(evaluation=evaluation, candidate=candidate)
    commercial_policy_snapshot = dict((binding.evidence_payload or {}).get("policy_snapshot") or {})
    return {
        "candidate_kind": "binding",
        "id": str(binding.id),
        "result": result,
        "eligible": evaluation.eligible,
        "reason_codes": _binding_result_reason_codes(
            evaluation=evaluation,
            candidate=candidate,
            result=result,
        ),
        "binding_type": binding.binding_type,
        "precedence_rank": _BINDING_PRECEDENCE_RANK.get(binding.binding_type, 90),
        "owner_type": binding.owner_type,
        "partner_account_id": str(binding.partner_account_id) if binding.partner_account_id else None,
        "partner_code_id": str(binding.partner_code_id) if binding.partner_code_id else None,
        "attribution_session_id": str(binding.attribution_session_id) if binding.attribution_session_id else None,
        "policy_version_id": str(binding.policy_version_id) if binding.policy_version_id else None,
        "commission_contract_id": str(binding.commission_contract_id) if binding.commission_contract_id else None,
        "snapshot_attribution_model": str(commercial_policy_snapshot.get("attribution_model") or ""),
        "storefront_id": str(binding.storefront_id) if binding.storefront_id else None,
        "effective_from": _normalize_utc(binding.effective_from).isoformat(),
        "effective_to": _normalize_utc(binding.effective_to).isoformat() if binding.effective_to else None,
    }


_SAFE_CAMPAIGN_PARAM_KEYS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "gclid",
        "fbclid",
        "yclid",
        "sub_id",
        "sub_source",
        "creator",
    }
)
_SAFE_EVIDENCE_PAYLOAD_KEYS = frozenset(
    {
        "policy_snapshot",
        "public_token_source",
        "partner_code_link_id",
        "source",
    }
)
_SAFE_POLICY_SNAPSHOT_KEYS = frozenset(
    {
        "allowed",
        "reason_codes",
        "owner_type",
        "partner_account_id",
        "partner_code_id",
        "partner_code_link_id",
        "policy_version_id",
        "commission_contract_id",
        "commission_contract_snapshot",
        "attribution_model",
        "snapshot_complete",
        "evaluated_sale_channel",
        "evaluated_storefront_id",
        "lane_key",
        "lane_application_id",
        "lane_application_status",
        "risk_review_ids",
        "risk_review_decisions",
        "attribution_expires_at",
        "expires_at",
    }
)
_SENSITIVE_KEY_PARTS = (
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "cookie",
    "authorization",
    "password",
    "secret",
    "jwt",
    "session",
    "telegram_initdata",
    "initdata",
    "email",
    "phone",
    "pat",
)
_SENSITIVE_KEY_EXCEPTIONS = frozenset({"public_token_source"})
_EMAIL_RE = re.compile(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")
_JWT_RE = re.compile(r"^[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}$")


def _safe_campaign_params(payload: dict | None) -> dict:
    return _safe_metadata_map(payload, allowed_keys=_SAFE_CAMPAIGN_PARAM_KEYS)


def _safe_evidence_payload(payload: dict | None) -> dict:
    raw_payload = dict(payload or {})
    safe = _safe_metadata_map(raw_payload, allowed_keys=_SAFE_EVIDENCE_PAYLOAD_KEYS)
    if isinstance(raw_payload.get("policy_snapshot"), dict):
        safe["policy_snapshot"] = _safe_policy_snapshot(raw_payload["policy_snapshot"])
    return safe


def _safe_policy_snapshot(payload: dict | None) -> dict:
    return _safe_metadata_map(payload, allowed_keys=_SAFE_POLICY_SNAPSHOT_KEYS, include_nested=True)


def _safe_metadata_map(
    payload: dict | None,
    *,
    allowed_keys: frozenset[str],
    include_nested: bool = False,
) -> dict:
    safe: dict[str, object] = {}
    redacted_keys: list[str] = []
    for raw_key, raw_value in dict(payload or {}).items():
        key = str(raw_key)
        if key in allowed_keys:
            safe[key] = _safe_metadata_value(key, raw_value, include_nested=include_nested)
        else:
            redacted_keys.append(key)
    if redacted_keys:
        safe["redacted_keys"] = sorted(redacted_keys)
    return safe


def _safe_metadata_value(key: str, value: object, *, include_nested: bool) -> object:
    if _is_sensitive_metadata(key, value):
        return _redacted_value(value)
    if isinstance(value, dict):
        if include_nested:
            return {
                str(nested_key): _safe_metadata_value(str(nested_key), nested_value, include_nested=True)
                for nested_key, nested_value in value.items()
            }
        return {"redacted": True, "sha256": _metadata_sha256(value)}
    if isinstance(value, list):
        return [_safe_metadata_value(key, item, include_nested=include_nested) for item in value[:50]]
    if isinstance(value, str):
        return value if len(value) <= 256 else f"{value[:256]}..."
    if isinstance(value, int | float | bool) or value is None:
        return value
    return str(value)


def _is_sensitive_metadata(key: str, value: object) -> bool:
    normalized_key = key.lower().replace("-", "_")
    if normalized_key in _SENSITIVE_KEY_EXCEPTIONS:
        return False
    if any(part == normalized_key or part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return True
    if not isinstance(value, str):
        return False
    normalized_value = value.strip()
    if not normalized_value:
        return False
    lowered = normalized_value.lower()
    if _EMAIL_RE.search(normalized_value):
        return True
    if _JWT_RE.match(normalized_value):
        return True
    if lowered.startswith("bearer ") or lowered.startswith("glpat-") or lowered.startswith("ghp_"):
        return True
    if "access_token=" in lowered or "refresh_token=" in lowered or "telegram_initdata=" in lowered:
        return True
    if "pat=" in lowered or "cookie=" in lowered:
        return True
    return len(normalized_value) > 64 and " " not in normalized_value


def _redacted_value(value: object) -> dict:
    return {"redacted": True, "sha256": _metadata_sha256(value)}


def _metadata_sha256(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _binding_evaluation_result(
    *,
    evaluation: _BindingEvaluation,
    candidate: _ResolvedCandidate | None,
) -> str:
    if candidate is not None and candidate.winning_binding_id == evaluation.binding.id:
        return "winner"
    if not evaluation.eligible:
        return "excluded"
    return "loser"


def _binding_result_reason_codes(
    *,
    evaluation: _BindingEvaluation,
    candidate: _ResolvedCandidate | None,
    result: str,
) -> list[str]:
    if result == "winner":
        return []
    if result == "excluded":
        return list(evaluation.reason_codes)
    if candidate is None:
        return ["no_owner_resolved"]
    return [f"lower_precedence_{candidate.owner_source or 'candidate'}"]


def _select_touchpoint_by_model(
    touchpoints: list[AttributionTouchpointModel | None],
) -> AttributionTouchpointModel | None:
    candidates = [touchpoint for touchpoint in touchpoints if touchpoint is not None]
    if not candidates:
        return None
    if any(_touchpoint_attribution_model(touchpoint) == "first_eligible_touch" for touchpoint in candidates):
        return sorted(
            candidates,
            key=lambda item: (_normalize_utc(item.occurred_at), _normalize_utc(item.created_at)),
        )[0]
    return sorted(
        candidates,
        key=lambda item: (_normalize_utc(item.occurred_at), _normalize_utc(item.created_at)),
    )[-1]


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
    touchpoint_evaluations = _evaluate_touchpoints(order=order, touchpoints=touchpoints)
    binding_evaluations = _evaluate_bindings(order=order, bindings=bindings)
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
        "eligible_touchpoint_ids": [
            str(evaluation.touchpoint.id) for evaluation in touchpoint_evaluations if evaluation.eligible
        ],
        "eligible_binding_ids": [
            str(evaluation.binding.id) for evaluation in binding_evaluations if evaluation.eligible
        ],
        "excluded_touchpoints": [
            {
                "id": str(evaluation.touchpoint.id),
                "reason_codes": list(evaluation.reason_codes),
            }
            for evaluation in touchpoint_evaluations
            if not evaluation.eligible
        ],
        "excluded_bindings": [
            {
                "id": str(evaluation.binding.id),
                "reason_codes": list(evaluation.reason_codes),
            }
            for evaluation in binding_evaluations
            if not evaluation.eligible
        ],
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
    touchpoint_evaluations = _evaluate_touchpoints(order=order, touchpoints=touchpoints)
    eligible_touchpoints = [evaluation.touchpoint for evaluation in touchpoint_evaluations if evaluation.eligible]
    touchpoint_strategy = _resolve_touchpoint_strategy(eligible_touchpoints) if eligible_touchpoints else None
    binding_evaluations = _evaluate_bindings(order=order, bindings=bindings)
    candidate_evaluations = [
        *[
            _serialize_touchpoint_evaluation(
                evaluation=evaluation,
                candidate=candidate,
                selected_strategy=touchpoint_strategy,
            )
            for evaluation in touchpoint_evaluations
        ],
        *[
            _serialize_binding_evaluation(
                evaluation=evaluation,
                candidate=candidate,
            )
            for evaluation in binding_evaluations
        ],
    ]
    return {
        "resolver_version": "phase3_t3_3_v2",
        "policy_strategy": touchpoint_strategy,
        "resolution_precedence": [
            "manual_override",
            "contract_assignment",
            "claimed_commercial_binding",
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
                "attribution_session_id": (
                    str(candidate.attribution_session_id) if candidate.attribution_session_id else None
                ),
                "policy_version_id": str(candidate.policy_version_id) if candidate.policy_version_id else None,
                "commission_contract_id": (
                    str(candidate.commission_contract_id) if candidate.commission_contract_id else None
                ),
                "winning_touchpoint_id": (
                    str(candidate.winning_touchpoint_id) if candidate.winning_touchpoint_id else None
                ),
                "winning_binding_id": str(candidate.winning_binding_id) if candidate.winning_binding_id else None,
                "rule_path": list(candidate.rule_path),
            }
            if candidate is not None
            else None
        ),
        "candidate_evaluations": candidate_evaluations,
        "losing_candidates": [
            evaluation for evaluation in candidate_evaluations if evaluation["result"] in {"loser", "excluded"}
        ],
        "evaluated_touchpoints": [
            {
                "id": str(touchpoint.id),
                "touchpoint_type": touchpoint.touchpoint_type,
                "partner_code_id": str(touchpoint.partner_code_id) if touchpoint.partner_code_id else None,
                "storefront_id": str(touchpoint.storefront_id) if touchpoint.storefront_id else None,
                "occurred_at": _normalize_utc(touchpoint.occurred_at).isoformat(),
                "campaign_params": _safe_campaign_params(touchpoint.campaign_params),
                "evidence_payload": _safe_evidence_payload(touchpoint.evidence_payload),
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
                "effective_to": _normalize_utc(binding.effective_to).isoformat() if binding.effective_to else None,
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
