from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.application.use_cases.payments.checkout import CheckoutAddonLine, CheckoutResult


def build_checkout_result_from_order(order) -> CheckoutResult:
    pricing_snapshot = order.pricing_snapshot or {}
    quote_snapshot = pricing_snapshot.get("quote") or {}
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
        entitlements_snapshot=dict(order.entitlements_snapshot or quote_snapshot.get("entitlements_snapshot") or {}),
        commission_base_amount=Decimal(str(quote_snapshot.get("commission_base_amount", 0))),
    )
