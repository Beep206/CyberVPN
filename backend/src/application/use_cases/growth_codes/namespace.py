from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.application.use_cases.growth_codes.hashing import (
    build_growth_code_prefix,
    hash_growth_code,
    normalize_growth_code_value,
)
from src.domain.enums import GrowthCodeType

CUSTOMER_INPUT_CODE_NAMESPACE = "customer_input"
CODE_NAMESPACE_AMBIGUOUS = "CODE_NAMESPACE_AMBIGUOUS"


class CanonicalGrowthCodeLookup(Protocol):
    async def get_code_by_hash(self, code_hash: str, *, code_type: str | None = None) -> Any | None: ...


class LegacyCodeLookup(Protocol):
    async def get_by_code(self, code: str) -> Any | None: ...


class ReferralCodeLookup(Protocol):
    async def get_by_referral_code(self, referral_code: str) -> Any | None: ...


class PartnerCodeLookup(Protocol):
    async def get_code_by_code(self, code: str) -> Any | None: ...


@dataclass(frozen=True, slots=True)
class NormalizedCustomerCode:
    namespace: str
    normalized_code: str
    code_hash: str
    code_prefix: str
    masked_code: str
    lookup_values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GrowthCodeNamespaceMatch:
    code_type: GrowthCodeType
    source: str
    entity_id: object | None
    growth_code_id: object | None = None


@dataclass(frozen=True, slots=True)
class GrowthCodeNamespaceLookup:
    normalized: NormalizedCustomerCode
    matches: tuple[GrowthCodeNamespaceMatch, ...]

    @property
    def matched_code_types(self) -> tuple[GrowthCodeType, ...]:
        return tuple(sorted({match.code_type for match in self.matches}, key=lambda item: item.value))

    @property
    def is_ambiguous(self) -> bool:
        return len(self.matched_code_types) > 1

    @property
    def primary_match(self) -> GrowthCodeNamespaceMatch | None:
        if self.is_ambiguous or not self.matches:
            return None
        return self.matches[0]

    @property
    def public_error_code(self) -> str | None:
        return CODE_NAMESPACE_AMBIGUOUS if self.is_ambiguous else None


def normalize_customer_input_code(raw_code: str) -> NormalizedCustomerCode:
    normalized_code = normalize_growth_code_value(raw_code)
    stripped_raw = raw_code.strip()
    lookup_values = (normalized_code,) if stripped_raw == normalized_code else (normalized_code, stripped_raw)
    return NormalizedCustomerCode(
        namespace=CUSTOMER_INPUT_CODE_NAMESPACE,
        normalized_code=normalized_code,
        code_hash=hash_growth_code(normalized_code),
        code_prefix=build_growth_code_prefix(normalized_code),
        masked_code=mask_customer_input_code(normalized_code),
        lookup_values=lookup_values,
    )


def mask_customer_input_code(raw_code: str) -> str:
    normalized_code = normalize_growth_code_value(raw_code)
    if len(normalized_code) <= 4:
        return f"{normalized_code[0:1]}***"
    return f"{normalized_code[:4]}...{normalized_code[-2:]}"


class GrowthCodeNamespaceService:
    """Classify customer-entered codes before legacy resolver fallbacks.

    The v6 schema will replace legacy tables with a global namespace table. Until
    that migration lands, this service gives application code one normalization,
    hashing and ambiguity gate while reading existing repositories only.
    """

    def __init__(
        self,
        *,
        canonical_codes: CanonicalGrowthCodeLookup,
        invite_codes: LegacyCodeLookup | None = None,
        promo_codes: LegacyCodeLookup | None = None,
        referral_codes: ReferralCodeLookup | None = None,
        partner_codes: PartnerCodeLookup | None = None,
    ) -> None:
        self._canonical_codes = canonical_codes
        self._invite_codes = invite_codes
        self._promo_codes = promo_codes
        self._referral_codes = referral_codes
        self._partner_codes = partner_codes

    async def lookup_customer_input(self, raw_code: str) -> GrowthCodeNamespaceLookup:
        normalized = normalize_customer_input_code(raw_code)
        matches: list[GrowthCodeNamespaceMatch] = []
        seen: set[tuple[GrowthCodeType, str, str | None]] = set()

        canonical = await self._canonical_codes.get_code_by_hash(normalized.code_hash)
        if canonical is not None:
            self._append_match(
                matches,
                seen,
                GrowthCodeNamespaceMatch(
                    code_type=GrowthCodeType(str(canonical.code_type)),
                    source="canonical_growth_codes",
                    entity_id=getattr(canonical, "id", None),
                    growth_code_id=getattr(canonical, "id", None),
                ),
            )

        for lookup_value in normalized.lookup_values:
            await self._append_legacy_match(
                matches,
                seen,
                repository=self._invite_codes,
                code_type=GrowthCodeType.INVITE,
                source="legacy_invite_codes",
                lookup_value=lookup_value,
            )
            await self._append_legacy_match(
                matches,
                seen,
                repository=self._promo_codes,
                code_type=GrowthCodeType.PROMO,
                source="legacy_promo_codes",
                lookup_value=lookup_value,
            )
            await self._append_referral_match(
                matches,
                seen,
                lookup_value=lookup_value,
            )
            await self._append_partner_match(
                matches,
                seen,
                lookup_value=lookup_value,
            )

        return GrowthCodeNamespaceLookup(normalized=normalized, matches=tuple(matches))

    async def _append_legacy_match(
        self,
        matches: list[GrowthCodeNamespaceMatch],
        seen: set[tuple[GrowthCodeType, str, str | None]],
        *,
        repository: LegacyCodeLookup | None,
        code_type: GrowthCodeType,
        source: str,
        lookup_value: str,
    ) -> None:
        if repository is None:
            return
        model = await repository.get_by_code(lookup_value)
        if model is None:
            return
        self._append_match(
            matches,
            seen,
            GrowthCodeNamespaceMatch(
                code_type=code_type,
                source=source,
                entity_id=getattr(model, "id", None),
            ),
        )

    async def _append_referral_match(
        self,
        matches: list[GrowthCodeNamespaceMatch],
        seen: set[tuple[GrowthCodeType, str, str | None]],
        *,
        lookup_value: str,
    ) -> None:
        if self._referral_codes is None:
            return
        model = await self._referral_codes.get_by_referral_code(lookup_value)
        if model is None:
            return
        self._append_match(
            matches,
            seen,
            GrowthCodeNamespaceMatch(
                code_type=GrowthCodeType.REFERRAL,
                source="mobile_user_referral_codes",
                entity_id=getattr(model, "id", None),
            ),
        )

    async def _append_partner_match(
        self,
        matches: list[GrowthCodeNamespaceMatch],
        seen: set[tuple[GrowthCodeType, str, str | None]],
        *,
        lookup_value: str,
    ) -> None:
        if self._partner_codes is None:
            return
        model = await self._partner_codes.get_code_by_code(lookup_value)
        if model is None:
            return
        self._append_match(
            matches,
            seen,
            GrowthCodeNamespaceMatch(
                code_type=GrowthCodeType.PARTNER,
                source="partner_codes",
                entity_id=getattr(model, "id", None),
            ),
        )

    @staticmethod
    def _append_match(
        matches: list[GrowthCodeNamespaceMatch],
        seen: set[tuple[GrowthCodeType, str, str | None]],
        match: GrowthCodeNamespaceMatch,
    ) -> None:
        key = (match.code_type, match.source, str(match.entity_id) if match.entity_id is not None else None)
        if key in seen:
            return
        seen.add(key)
        matches.append(match)
