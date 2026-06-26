from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.application.use_cases.growth_codes.namespace import (
    CODE_NAMESPACE_AMBIGUOUS,
    GrowthCodeNamespaceService,
    normalize_customer_input_code,
)
from src.domain.enums import GrowthCodeType


class StaticCanonicalCodes:
    def __init__(self, model=None) -> None:
        self._model = model

    async def get_code_by_hash(self, _code_hash: str, *, code_type: str | None = None):
        if code_type is not None:
            return None
        return self._model


class StaticLegacyCodes:
    def __init__(self, expected_code: str, model=None) -> None:
        self._expected_code = expected_code
        self._model = model

    async def get_by_code(self, code: str):
        return self._model if code == self._expected_code else None


class StaticReferralCodes:
    def __init__(self, expected_code: str, model=None) -> None:
        self._expected_code = expected_code
        self._model = model

    async def get_by_referral_code(self, code: str):
        return self._model if code == self._expected_code else None


def test_normalize_customer_input_code_uses_one_unicode_uppercase_hash() -> None:
    normalized = normalize_customer_input_code("  ｓａｖｅ_10  ")

    assert normalized.namespace == "customer_input"
    assert normalized.normalized_code == "SAVE_10"
    assert normalized.code_hash == hash_growth_code("SAVE_10")
    assert normalized.masked_code == "SAVE...10"
    assert normalized.lookup_values == ("SAVE_10", "ｓａｖｅ_10")


@pytest.mark.asyncio
async def test_namespace_lookup_reports_cross_type_legacy_collision_without_raw_code() -> None:
    promo = SimpleNamespace(id=uuid4())
    invite = SimpleNamespace(id=uuid4())
    service = GrowthCodeNamespaceService(
        canonical_codes=StaticCanonicalCodes(),
        promo_codes=StaticLegacyCodes("SAMECODE", promo),
        invite_codes=StaticLegacyCodes("SAMECODE", invite),
    )

    lookup = await service.lookup_customer_input(" samecode ")

    assert lookup.is_ambiguous is True
    assert lookup.public_error_code == CODE_NAMESPACE_AMBIGUOUS
    assert lookup.matched_code_types == (GrowthCodeType.INVITE, GrowthCodeType.PROMO)
    assert lookup.normalized.masked_code == "SAME...DE"
    assert "samecode" not in lookup.normalized.masked_code


@pytest.mark.asyncio
async def test_namespace_lookup_keeps_canonical_and_legacy_same_type_unambiguous() -> None:
    canonical = SimpleNamespace(id=uuid4(), code_type="promo")
    legacy = SimpleNamespace(id=uuid4())
    service = GrowthCodeNamespaceService(
        canonical_codes=StaticCanonicalCodes(canonical),
        promo_codes=StaticLegacyCodes("SAVE20", legacy),
    )

    lookup = await service.lookup_customer_input("save20")

    assert lookup.is_ambiguous is False
    assert lookup.matched_code_types == (GrowthCodeType.PROMO,)
    assert lookup.primary_match is not None
