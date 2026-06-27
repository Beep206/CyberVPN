from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from src.application.use_cases.growth_code_sets.ledger import code_set_applications
from src.application.use_cases.growth_code_sets.snapshots import read_growth_checkout_v3_snapshot
from src.application.use_cases.payments.checkout import CheckoutAddonLine, CheckoutAppliedDiscount, CheckoutResult


def build_checkout_result_from_order(order) -> CheckoutResult:
    pricing_snapshot = order.pricing_snapshot or {}
    quote_snapshot = pricing_snapshot.get("quote") or {}
    growth_checkout_snapshot = read_growth_checkout_v3_snapshot(pricing_snapshot)
    code_set_snapshot = _code_set_snapshot_from_growth_checkout_snapshot(growth_checkout_snapshot)
    order_code_set_id = getattr(order, "code_set_id", None)
    if code_set_snapshot is not None and not code_set_snapshot.get("id") and order_code_set_id is not None:
        code_set_snapshot["id"] = str(order_code_set_id)
    code_set_acceptance_mode = None
    code_set_hash = None
    if code_set_snapshot is not None:
        raw_acceptance_mode = code_set_snapshot.get("acceptance_mode")
        code_set_acceptance_mode = str(raw_acceptance_mode) if raw_acceptance_mode else None
        raw_code_set_hash = code_set_snapshot.get("hash")
        code_set_hash = str(raw_code_set_hash) if raw_code_set_hash else None
    applications = code_set_applications(growth_checkout_snapshot)
    addon_lines = [
        CheckoutAddonLine(
            addon_id=UUID(str(addon["addon_id"])),
            code=str(addon["code"]),
            display_name=str(addon.get("display_name") or addon["code"]),
            qty=int(addon.get("qty", 1) or 1),
            unit_price=Decimal(str(addon.get("unit_price", 0))),
            total_price=Decimal(str(addon.get("total_price", 0))),
            location_code=addon.get("location_code"),
            delta_entitlements=dict(addon.get("delta_entitlements", {})),
        )
        for addon in quote_snapshot.get("addons", [])
        if addon.get("addon_id")
    ]
    entitlements_snapshot = dict(order.entitlements_snapshot or quote_snapshot.get("entitlements_snapshot") or {})
    if growth_checkout_snapshot is not None:
        entitlements_snapshot["growth_checkout_snapshot"] = growth_checkout_snapshot
        entitlements_snapshot["growth_effects_snapshot"] = dict(growth_checkout_snapshot.get("growth_effects") or {})

    return CheckoutResult(
        base_price=Decimal(str(quote_snapshot.get("base_price", 0))),
        addon_amount=Decimal(str(quote_snapshot.get("addon_amount", 0))),
        displayed_price=Decimal(str(quote_snapshot.get("displayed_price", 0))),
        discount_amount=Decimal(str(quote_snapshot.get("discount_amount", 0))),
        wallet_amount=Decimal(str(quote_snapshot.get("wallet_amount", 0))),
        gateway_amount=Decimal(str(quote_snapshot.get("gateway_amount", 0))),
        partner_markup=Decimal(str(quote_snapshot.get("partner_markup", 0))),
        is_zero_gateway=bool(quote_snapshot.get("is_zero_gateway", False)),
        plan_id=UUID(str(quote_snapshot["plan_id"])) if quote_snapshot.get("plan_id") else None,
        promo_code_id=UUID(str(quote_snapshot["promo_code_id"])) if quote_snapshot.get("promo_code_id") else None,
        partner_code_id=(
            UUID(str(quote_snapshot["partner_code_id"])) if quote_snapshot.get("partner_code_id") else None
        ),
        plan_name=quote_snapshot.get("plan_name"),
        duration_days=quote_snapshot.get("duration_days"),
        addons=addon_lines,
        entitlements_snapshot=entitlements_snapshot,
        commission_base_amount=_commission_base_amount(
            quote_snapshot=quote_snapshot,
            growth_checkout_snapshot=growth_checkout_snapshot,
        ),
        discounts=_discounts_from_growth_checkout_snapshot(growth_checkout_snapshot),
        code_input=_code_input_from_growth_checkout_snapshot(growth_checkout_snapshot),
        reservation_id=_reservation_id_from_growth_checkout_snapshot(growth_checkout_snapshot),
        private_catalog_grant_id=_private_catalog_grant_id_from_snapshots(
            quote_snapshot=quote_snapshot,
            growth_checkout_snapshot=growth_checkout_snapshot,
        ),
        private_catalog_snapshot=_private_catalog_snapshot_from_growth_checkout_snapshot(growth_checkout_snapshot),
        code_set_applications=applications,
        code_set_acceptance_mode=code_set_acceptance_mode,
        code_set_id=_uuid_or_none(code_set_snapshot.get("id") if code_set_snapshot else order_code_set_id),
        code_set_hash=code_set_hash,
        reservation_group_id=_uuid_or_none(
            growth_checkout_snapshot.get("reservation_group_id") if growth_checkout_snapshot else None
        ),
        code_set_snapshot=code_set_snapshot,
        growth_checkout_snapshot=growth_checkout_snapshot,
    )


def _discounts_from_growth_checkout_snapshot(
    growth_checkout_snapshot: dict | None,
) -> list[CheckoutAppliedDiscount]:
    if growth_checkout_snapshot is None:
        return []
    code_set = growth_checkout_snapshot.get("code_set")
    applications = code_set.get("applications") if isinstance(code_set, dict) else None
    if not applications:
        return []
    if not isinstance(applications, list):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    discounts: list[CheckoutAppliedDiscount] = []
    for application in applications:
        if not isinstance(application, dict):
            raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
        discount = application.get("discount")
        if not isinstance(discount, dict):
            raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
        applied_amount = discount.get("applied_amount")
        if applied_amount is None:
            raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
        policy_version_id = application.get("policy_version_id")
        roles = application.get("roles") if isinstance(application.get("roles"), list) else []
        discounts.append(
            CheckoutAppliedDiscount(
                discount_type=str(roles[0] if roles else "growth_code"),
                code=str(application.get("masked_code") or ""),
                amount=Decimal(str(applied_amount)),
                policy_version_id=UUID(str(policy_version_id)) if policy_version_id else None,
            )
        )
    return discounts


def _code_set_snapshot_from_growth_checkout_snapshot(growth_checkout_snapshot: dict | None) -> dict | None:
    if growth_checkout_snapshot is None:
        return None
    code_set = growth_checkout_snapshot.get("code_set")
    if not isinstance(code_set, dict):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    applications = code_set.get("applications")
    if applications is not None and not isinstance(applications, list):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    return deepcopy(code_set)


def _private_catalog_snapshot_from_growth_checkout_snapshot(growth_checkout_snapshot: dict | None) -> dict | None:
    if growth_checkout_snapshot is None:
        return None
    private_catalog = growth_checkout_snapshot.get("private_catalog")
    if private_catalog in (None, {}):
        return None
    if not isinstance(private_catalog, dict):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    return deepcopy(private_catalog)


def _private_catalog_grant_id_from_snapshots(
    *,
    quote_snapshot: dict,
    growth_checkout_snapshot: dict | None,
) -> UUID | None:
    candidates = [
        quote_snapshot.get("private_catalog_grant_id"),
    ]
    private_catalog = growth_checkout_snapshot.get("private_catalog") if growth_checkout_snapshot else None
    if isinstance(private_catalog, dict):
        candidates.extend(
            [
                private_catalog.get("grant_id"),
                private_catalog.get("private_catalog_grant_id"),
            ]
        )
    for candidate in candidates:
        parsed = _uuid_or_none(candidate)
        if parsed is not None:
            return parsed
    return None


def _code_input_from_growth_checkout_snapshot(growth_checkout_snapshot: dict | None) -> str | None:
    if growth_checkout_snapshot is None:
        return None
    applications = (growth_checkout_snapshot.get("code_set") or {}).get("applications") or []
    if not applications:
        return None
    first = applications[0]
    if not isinstance(first, dict):
        raise ValueError("SNAPSHOT_INTEGRITY_ERROR")
    masked_code = first.get("masked_code")
    return str(masked_code) if masked_code else None


def _reservation_id_from_growth_checkout_snapshot(growth_checkout_snapshot: dict | None) -> UUID | None:
    if growth_checkout_snapshot is None:
        return None
    applications = (growth_checkout_snapshot.get("code_set") or {}).get("applications") or []
    reservation_id = None
    if applications and isinstance(applications[0], dict):
        reservation_id = applications[0].get("reservation_id")
    return UUID(str(reservation_id)) if reservation_id else None


def _commission_base_amount(*, quote_snapshot: dict, growth_checkout_snapshot: dict | None) -> Decimal:
    if growth_checkout_snapshot is not None:
        growth_effects = growth_checkout_snapshot.get("growth_effects")
        settlement = growth_effects.get("settlement") if isinstance(growth_effects, dict) else None
        if isinstance(settlement, dict) and settlement.get("commissionable_amount") is not None:
            return Decimal(str(settlement["commissionable_amount"]))
    return Decimal(str(quote_snapshot.get("commission_base_amount", 0)))


def _uuid_or_none(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    return UUID(str(value))
