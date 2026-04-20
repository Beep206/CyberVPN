from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_order_item_payloads(
    *,
    currency_code: str,
    quote_snapshot: dict[str, Any],
    context_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    plan_item = {
        "item_type": "plan",
        "subject_id": quote_snapshot.get("plan_id"),
        "subject_code": context_snapshot.get("offer", {}).get("offer_key"),
        "display_name": quote_snapshot.get("plan_name")
        or context_snapshot.get("offer", {}).get("display_name")
        or "Subscription Plan",
        "quantity": 1,
        "unit_price": float(quote_snapshot.get("base_price", 0)),
        "total_price": float(quote_snapshot.get("base_price", 0)),
        "currency_code": currency_code,
        "item_snapshot": {
            "duration_days": quote_snapshot.get("duration_days"),
            "commission_base_amount": quote_snapshot.get("commission_base_amount"),
            "offer": deepcopy(context_snapshot.get("offer", {})),
            "subscription_plan_id": quote_snapshot.get("plan_id"),
        },
    }
    addon_items = [
        {
            "item_type": "addon",
            "subject_id": addon.get("addon_id"),
            "subject_code": addon.get("code"),
            "display_name": addon.get("display_name") or addon.get("code") or "Addon",
            "quantity": int(addon.get("qty", 1) or 1),
            "unit_price": float(addon.get("unit_price", 0)),
            "total_price": float(addon.get("total_price", 0)),
            "currency_code": currency_code,
            "item_snapshot": {
                "location_code": addon.get("location_code"),
                "source": deepcopy(addon),
            },
        }
        for addon in quote_snapshot.get("addons", [])
    ]
    return [plan_item, *addon_items]


def build_order_snapshots(
    *,
    quote_snapshot: dict[str, Any],
    context_snapshot: dict[str, Any],
    request_snapshot: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    merchant_snapshot = {
        "storefront": deepcopy(context_snapshot.get("storefront", {})),
        "merchant_profile": deepcopy(context_snapshot.get("merchant_profile", {})),
        "invoice_profile": deepcopy(context_snapshot.get("invoice_profile", {})),
        "billing_descriptor": deepcopy(context_snapshot.get("billing_descriptor", {})),
    }
    pricing_snapshot = {
        "quote": deepcopy(quote_snapshot),
        "request": deepcopy(request_snapshot),
        "pricebook": deepcopy(context_snapshot.get("pricebook", {})),
        "pricebook_entry": deepcopy(context_snapshot.get("pricebook_entry", {})),
    }
    policy_snapshot = {
        "offer": deepcopy(context_snapshot.get("offer", {})),
        "legal_document_set": deepcopy(context_snapshot.get("legal_document_set", {})),
        "program_eligibility_policy": deepcopy(context_snapshot.get("program_eligibility_policy")),
        "applied_codes": {
            "promo_code_id": quote_snapshot.get("promo_code_id"),
            "partner_code_id": quote_snapshot.get("partner_code_id"),
        },
    }
    return merchant_snapshot, pricing_snapshot, policy_snapshot
