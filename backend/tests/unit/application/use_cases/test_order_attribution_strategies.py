from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.application.use_cases.attribution.order_resolution.resolve_order_attribution import (
    ResolveOrderAttributionUseCase,
)
from src.domain.enums import AttributionTouchpointType, CustomerCommercialBindingType
from src.infrastructure.database.models.attribution_touchpoint_model import AttributionTouchpointModel
from src.infrastructure.database.models.customer_commercial_binding_model import CustomerCommercialBindingModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel, PartnerCodeModel


class _PartnerLookup:
    def __init__(self, codes: list[PartnerCodeModel]) -> None:
        self._codes = {code.id: code for code in codes}

    async def get_code_by_id(self, code_id: uuid.UUID) -> PartnerCodeModel | None:
        return self._codes.get(code_id)


def _resolver(*codes: PartnerCodeModel) -> ResolveOrderAttributionUseCase:
    resolver = ResolveOrderAttributionUseCase.__new__(ResolveOrderAttributionUseCase)
    resolver._partners = _PartnerLookup(list(codes))
    return resolver


def _code(label: str, *, owner_type: str = "affiliate", attribution_model: str = "last_eligible_touch"):
    account_id = uuid.uuid4()
    return PartnerCodeModel(
        id=uuid.uuid4(),
        code=label,
        code_normalized=label,
        public_slug=f"px_{label.lower()}",
        public_token_hash=f"hash-{label.lower()}",
        partner_account_id=account_id,
        partner_user_id=uuid.uuid4(),
        owner_type=owner_type,
        attribution_model=attribution_model,
        markup_pct=5,
        is_active=True,
    )


def _account() -> PartnerAccountModel:
    return PartnerAccountModel(
        id=uuid.uuid4(),
        account_key=f"acct-{uuid.uuid4().hex[:12]}",
        display_name="Strategy Account",
        status="active",
    )


def _touchpoint(
    *,
    code: PartnerCodeModel,
    touchpoint_type: str,
    occurred_at: datetime,
    attribution_model: str,
    allowed: bool = True,
    reason_codes: list[str] | None = None,
) -> AttributionTouchpointModel:
    return AttributionTouchpointModel(
        id=uuid.uuid4(),
        touchpoint_type=touchpoint_type,
        partner_code_id=code.id,
        policy_version_id=None,
        sale_channel="content",
        source_host="partner.example.test",
        source_path="/campaign",
        campaign_params={},
        evidence_payload={
            "policy_snapshot": {
                "owner_type": code.owner_type,
                "partner_account_id": str(code.partner_account_id),
                "attribution_model": attribution_model,
                "snapshot_complete": True,
                "allowed": allowed,
                "reason_codes": list(reason_codes or []),
            }
        },
        occurred_at=occurred_at,
        created_at=occurred_at,
    )


def _binding(*, code: PartnerCodeModel, binding_type: str, owner_type: str) -> CustomerCommercialBindingModel:
    return CustomerCommercialBindingModel(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        binding_type=binding_type,
        binding_status="active",
        owner_type=owner_type,
        partner_account_id=code.partner_account_id,
        partner_code_id=code.id,
        storefront_id=None,
        reason_code="strategy-test",
        evidence_payload={"policy_snapshot": {"owner_type": owner_type, "attribution_model": "persistent"}},
        effective_from=datetime.now(UTC),
    )


def _order():
    return SimpleNamespace(storefront_id=None)


@pytest.mark.asyncio
async def test_first_eligible_touch_strategy_uses_all_touchpoints_and_selects_a() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    code_a = _code("STRATA")
    code_b = _code("STRATB")
    code_c = _code("STRATC")

    candidate = await _resolver(code_a, code_b, code_c)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=code_a,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started,
                attribution_model="first_eligible_touch",
            ),
            _touchpoint(
                code=code_b,
                touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                occurred_at=started + timedelta(minutes=1),
                attribution_model="first_eligible_touch",
            ),
            _touchpoint(
                code=code_c,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=2),
                attribution_model="first_eligible_touch",
            ),
        ],
        bindings=[],
    )

    assert candidate is not None
    assert candidate.partner_code_id == code_a.id
    assert candidate.owner_source == "passive_click"
    assert "first_eligible_touch_strategy_selected" in candidate.rule_path


@pytest.mark.asyncio
async def test_last_eligible_touch_strategy_selects_c() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    code_a = _code("LASTA")
    code_b = _code("LASTB")
    code_c = _code("LASTC")

    candidate = await _resolver(code_a, code_b, code_c)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=code_a,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started,
                attribution_model="last_eligible_touch",
            ),
            _touchpoint(
                code=code_b,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=1),
                attribution_model="last_eligible_touch",
            ),
            _touchpoint(
                code=code_c,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=2),
                attribution_model="last_eligible_touch",
            ),
        ],
        bindings=[],
    )

    assert candidate is not None
    assert candidate.partner_code_id == code_c.id
    assert "last_eligible_touch_strategy_selected" in candidate.rule_path


@pytest.mark.asyncio
async def test_last_eligible_click_strategy_ignores_later_non_click_touchpoint() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    click_code = _code("CLICKA")
    explicit_code = _code("CLICKB")

    candidate = await _resolver(click_code, explicit_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=click_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started,
                attribution_model="last_eligible_click",
            ),
            _touchpoint(
                code=explicit_code,
                touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="last_eligible_click",
            ),
        ],
        bindings=[],
    )

    assert candidate is not None
    assert candidate.partner_code_id == click_code.id
    assert candidate.owner_source == "passive_click"
    assert "last_eligible_click_strategy_selected" in candidate.rule_path


@pytest.mark.asyncio
async def test_ineligible_touchpoint_policy_snapshot_is_not_selected() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    blocked_code = _code("BLOCKEDA")
    eligible_code = _code("BLOCKEDB")

    candidate = await _resolver(blocked_code, eligible_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=blocked_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="last_eligible_touch",
                allowed=False,
                reason_codes=["risk_review_block"],
            ),
            _touchpoint(
                code=eligible_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started,
                attribution_model="last_eligible_touch",
            ),
        ],
        bindings=[],
    )

    assert candidate is not None
    assert candidate.partner_code_id == eligible_code.id
    assert "last_eligible_touch_strategy_selected" in candidate.rule_path


@pytest.mark.asyncio
async def test_explicit_code_priority_touchpoint_beats_older_first_eligible_touch_policy() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    first_touch_code = _code("MIXEDA")
    explicit_code = _code("MIXEDB")

    candidate = await _resolver(first_touch_code, explicit_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=first_touch_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started,
                attribution_model="first_eligible_touch",
            ),
            _touchpoint(
                code=explicit_code,
                touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="explicit_code_priority",
            ),
        ],
        bindings=[],
    )

    assert candidate is not None
    assert candidate.partner_code_id == explicit_code.id
    assert candidate.owner_source == "explicit_code"
    assert "explicit_code_priority_strategy_selected" in candidate.rule_path


@pytest.mark.asyncio
async def test_explicit_priority_and_immutable_binding_precedence_are_preserved() -> None:
    started = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    passive_code = _code("PRECA")
    explicit_code = _code("PRECB")
    reseller_code = _code("PRECR", owner_type="reseller")
    manual_code = _code("PRECM", owner_type="performance")

    explicit_candidate = await _resolver(passive_code, explicit_code, reseller_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=passive_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="explicit_code_priority",
            ),
            _touchpoint(
                code=explicit_code,
                touchpoint_type=AttributionTouchpointType.EXPLICIT_CODE.value,
                occurred_at=started,
                attribution_model="explicit_code_priority",
            ),
        ],
        bindings=[
            _binding(
                code=reseller_code,
                binding_type=CustomerCommercialBindingType.RESELLER_BINDING.value,
                owner_type="reseller",
            )
        ],
    )
    assert explicit_candidate is not None
    assert explicit_candidate.partner_code_id == explicit_code.id
    assert explicit_candidate.owner_source == "explicit_code"

    reseller_candidate = await _resolver(passive_code, reseller_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=passive_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="explicit_code_priority",
            )
        ],
        bindings=[
            _binding(
                code=reseller_code,
                binding_type=CustomerCommercialBindingType.RESELLER_BINDING.value,
                owner_type="reseller",
            )
        ],
    )
    assert reseller_candidate is not None
    assert reseller_candidate.partner_code_id == reseller_code.id
    assert reseller_candidate.owner_source == "persistent_reseller_binding"

    manual_candidate = await _resolver(passive_code, manual_code)._resolve_candidate(
        order=_order(),
        touchpoints=[
            _touchpoint(
                code=passive_code,
                touchpoint_type=AttributionTouchpointType.PASSIVE_CLICK.value,
                occurred_at=started + timedelta(minutes=5),
                attribution_model="last_eligible_touch",
            )
        ],
        bindings=[
            _binding(
                code=manual_code,
                binding_type=CustomerCommercialBindingType.MANUAL_OVERRIDE.value,
                owner_type="performance",
            )
        ],
    )
    assert manual_candidate is not None
    assert manual_candidate.partner_code_id == manual_code.id
    assert manual_candidate.owner_source == "manual_override"
