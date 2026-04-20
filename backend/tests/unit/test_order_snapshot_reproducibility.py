from src.application.use_cases.orders.snapshot_builder import build_order_item_payloads, build_order_snapshots


def test_order_snapshot_builder_produces_stable_copies() -> None:
    quote_snapshot = {
        "plan_id": "00000000-0000-0000-0000-000000000101",
        "plan_name": "Partner 365 Offer",
        "duration_days": 365,
        "base_price": 90.0,
        "addon_amount": 12.0,
        "displayed_price": 102.0,
        "discount_amount": 6.0,
        "wallet_amount": 0.0,
        "gateway_amount": 96.0,
        "partner_markup": 0.0,
        "commission_base_amount": 90.0,
        "promo_code_id": None,
        "partner_code_id": None,
        "entitlements_snapshot": {"status": "preview"},
        "addons": [
            {
                "addon_id": "00000000-0000-0000-0000-000000000202",
                "code": "extra_device",
                "display_name": "Extra Device",
                "qty": 2,
                "unit_price": 6.0,
                "total_price": 12.0,
                "location_code": None,
            }
        ],
    }
    context_snapshot = {
        "offer": {"id": "offer-1", "offer_key": "partner-365", "display_name": "Partner 365 Offer"},
        "merchant_profile": {"id": "merchant-1", "legal_entity_name": "Partner Merchant Ltd"},
        "pricebook": {"id": "pricebook-1", "currency_code": "USD"},
        "pricebook_entry": {"id": "entry-1", "visible_price": 75.0},
        "legal_document_set": {"id": "legal-set-1", "set_key": "partner-web-terms"},
        "program_eligibility_policy": {"id": "eligibility-1", "reseller_allowed": True},
        "storefront": {"id": "storefront-1", "storefront_key": "partner-web"},
        "invoice_profile": {"id": "invoice-1", "issuer_legal_name": "Partner Billing Ltd"},
        "billing_descriptor": {"id": "descriptor-1", "statement_descriptor": "PARTNER VPN"},
    }
    request_snapshot = {"storefront_key": "partner-web", "currency": "USD", "channel": "web"}

    merchant_snapshot, pricing_snapshot, policy_snapshot = build_order_snapshots(
        quote_snapshot=quote_snapshot,
        context_snapshot=context_snapshot,
        request_snapshot=request_snapshot,
    )
    item_payloads = build_order_item_payloads(
        currency_code="USD",
        quote_snapshot=quote_snapshot,
        context_snapshot=context_snapshot,
    )

    quote_snapshot["plan_name"] = "Mutated Plan"
    quote_snapshot["addons"][0]["display_name"] = "Mutated Addon"
    context_snapshot["merchant_profile"]["legal_entity_name"] = "Mutated Merchant"
    context_snapshot["offer"]["display_name"] = "Mutated Offer"

    assert merchant_snapshot["merchant_profile"]["legal_entity_name"] == "Partner Merchant Ltd"
    assert pricing_snapshot["quote"]["plan_name"] == "Partner 365 Offer"
    assert policy_snapshot["offer"]["display_name"] == "Partner 365 Offer"
    assert item_payloads[0]["display_name"] == "Partner 365 Offer"
    assert item_payloads[1]["display_name"] == "Extra Device"
