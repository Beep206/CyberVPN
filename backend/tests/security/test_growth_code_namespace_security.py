from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.growth_codes.namespace import (
    GrowthCodeNamespaceLookup,
    GrowthCodeNamespaceMatch,
    normalize_customer_input_code,
)
from src.application.use_cases.growth_codes.resolve_code import ResolveGrowthCodeUseCase
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
)


class RaisingLegacyLookup:
    async def get_by_code(self, _code: str):
        raise AssertionError("ambiguous namespace must stop before legacy lookup side effects")


class RecordingRegistry:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def record_resolution_event(self, **kwargs):
        self.events.append(kwargs)
        return SimpleNamespace(id=uuid4())


class NullLegacyLookup:
    async def get_by_code(self, _code: str):
        return None


class NullCanonicalLookup:
    async def get_code_by_hash(self, _code_hash: str, *, code_type: str | None = None):
        return None


class NullReferralLookup:
    async def get_by_referral_code(self, _code: str):
        return None


class AmbiguousNamespace:
    async def lookup_customer_input(self, raw_code: str) -> GrowthCodeNamespaceLookup:
        normalized = normalize_customer_input_code(raw_code)
        return GrowthCodeNamespaceLookup(
            normalized=normalized,
            matches=(
                GrowthCodeNamespaceMatch(
                    code_type=GrowthCodeType.PROMO,
                    source="legacy_promo_codes",
                    entity_id=uuid4(),
                ),
                GrowthCodeNamespaceMatch(
                    code_type=GrowthCodeType.INVITE,
                    source="legacy_invite_codes",
                    entity_id=uuid4(),
                ),
            ),
        )


class PassthroughNamespace:
    async def lookup_customer_input(self, raw_code: str) -> GrowthCodeNamespaceLookup:
        return GrowthCodeNamespaceLookup(normalized=normalize_customer_input_code(raw_code), matches=())


class SinglePartnerLookup:
    def __init__(self, *, stored_code: str, partner_code: SimpleNamespace) -> None:
        self.stored_code = stored_code
        self.partner_code = partner_code
        self.calls: list[str] = []

    async def get_code_by_code(self, code: str):
        self.calls.append(code)
        if code == self.stored_code:
            return self.partner_code
        return None


@pytest.mark.asyncio
async def test_resolver_fails_closed_on_namespace_collision_before_legacy_lookup() -> None:
    use_case = ResolveGrowthCodeUseCase(SimpleNamespace())
    registry = RecordingRegistry()
    use_case._namespace = AmbiguousNamespace()
    use_case._registry = registry
    use_case._invites = RaisingLegacyLookup()
    use_case._promos = RaisingLegacyLookup()

    outcome = await use_case.execute(
        code="SAMECODE",
        action_context=GrowthCodeActionContext.CHECKOUT,
        user_id=uuid4(),
    )

    assert outcome.accepted is False
    assert outcome.result == GrowthCodeResolutionStatus.CONFLICTED
    assert outcome.reject_reason == GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS
    assert outcome.conflict_code == "CODE_NAMESPACE_AMBIGUOUS"
    assert outcome.user_message_key == "growth_codes.code.namespace_ambiguous"
    assert registry.events[0]["conflict_code"] == "CODE_NAMESPACE_AMBIGUOUS"
    assert registry.events[0]["raw_code"] == "SAMECODE"


@pytest.mark.asyncio
async def test_resolver_preserves_legacy_partner_code_lookup_after_namespace_normalization() -> None:
    use_case = ResolveGrowthCodeUseCase(SimpleNamespace())
    partner_code = SimpleNamespace(id=uuid4())
    partners = SinglePartnerLookup(stored_code="legacyPartner", partner_code=partner_code)
    registry = RecordingRegistry()
    use_case._invites = NullLegacyLookup()
    use_case._promos = NullLegacyLookup()
    use_case._growth_codes = NullCanonicalLookup()
    use_case._users = NullReferralLookup()
    use_case._partners = partners
    use_case._registry = registry
    use_case._namespace = PassthroughNamespace()

    async def _resolve_referral_owner(_code: str):
        return None

    use_case._resolve_referral_owner = _resolve_referral_owner

    async def _resolve_partner_code(**kwargs):
        return SimpleNamespace(
            accepted=True,
            code_type=GrowthCodeType.PARTNER,
            action_context=kwargs["action_context"],
            result=GrowthCodeResolutionStatus.ACCEPTED,
            user_message_key="growth_codes.partner.accepted",
            reject_reason=None,
            conflict_code=None,
            partner_code_id=kwargs["partner_code"].id,
            policy_snapshot=None,
        )

    use_case._resolve_partner_code = _resolve_partner_code

    outcome = await use_case.execute(
        code=" legacyPartner ",
        action_context=GrowthCodeActionContext.CHECKOUT,
        user_id=uuid4(),
    )

    assert outcome.accepted is True
    assert outcome.code_type == GrowthCodeType.PARTNER
    assert outcome.partner_code_id == partner_code.id
    assert partners.calls == ["LEGACYPARTNER", "legacyPartner"]
    assert registry.events[0]["raw_code"] == "LEGACYPARTNER"
