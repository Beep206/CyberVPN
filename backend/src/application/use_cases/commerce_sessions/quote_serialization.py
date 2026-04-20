from __future__ import annotations

from typing import Any

from src.application.use_cases.commerce_sessions.context_resolution import ResolvedQuoteContext
from src.application.use_cases.payments.checkout import CheckoutResult


def serialize_checkout_result(result: CheckoutResult) -> dict[str, Any]:
    return {
        "base_price": float(result.base_price),
        "addon_amount": float(result.addon_amount),
        "displayed_price": float(result.displayed_price),
        "discount_amount": float(result.discount_amount),
        "wallet_amount": float(result.wallet_amount),
        "gateway_amount": float(result.gateway_amount),
        "partner_markup": float(result.partner_markup),
        "is_zero_gateway": result.is_zero_gateway,
        "plan_id": str(result.plan_id) if result.plan_id else None,
        "plan_name": result.plan_name,
        "duration_days": result.duration_days,
        "promo_code_id": str(result.promo_code_id) if result.promo_code_id else None,
        "partner_code_id": str(result.partner_code_id) if result.partner_code_id else None,
        "commission_base_amount": float(result.commission_base_amount),
        "addons": [
            {
                "addon_id": str(line.addon_id),
                "code": line.code,
                "display_name": line.display_name,
                "qty": line.qty,
                "unit_price": float(line.unit_price),
                "total_price": float(line.total_price),
                "location_code": line.location_code,
            }
            for line in result.addons
        ],
        "entitlements_snapshot": result.entitlements_snapshot,
    }


def build_context_snapshot(context: ResolvedQuoteContext) -> dict[str, Any]:
    return {
        "storefront_key": context.storefront.storefront_key,
        "pricebook_key": context.pricebook.pricebook_key,
        "offer_key": context.offer.offer_key,
        "legal_document_set_key": context.legal_document_set.set_key,
        "storefront": {
            "id": str(context.storefront.id),
            "storefront_key": context.storefront.storefront_key,
            "display_name": context.storefront.display_name,
            "host": context.storefront.host,
            "brand_id": str(context.storefront.brand_id),
            "auth_realm_id": str(context.storefront.auth_realm_id) if context.storefront.auth_realm_id else None,
            "support_profile_id": (
                str(context.storefront.support_profile_id) if context.storefront.support_profile_id else None
            ),
            "communication_profile_id": (
                str(context.storefront.communication_profile_id)
                if context.storefront.communication_profile_id
                else None
            ),
        },
        "merchant_profile": {
            "id": str(context.merchant_profile.id),
            "profile_key": context.merchant_profile.profile_key,
            "legal_entity_name": context.merchant_profile.legal_entity_name,
            "billing_descriptor": context.merchant_profile.billing_descriptor,
            "invoice_profile_id": (
                str(context.merchant_profile.invoice_profile_id)
                if context.merchant_profile.invoice_profile_id
                else None
            ),
            "supported_currencies": list(context.merchant_profile.supported_currencies),
            "tax_behavior": dict(context.merchant_profile.tax_behavior),
            "refund_responsibility_model": context.merchant_profile.refund_responsibility_model,
            "chargeback_liability_model": context.merchant_profile.chargeback_liability_model,
            "settlement_reference": context.merchant_profile.settlement_reference,
        },
        "invoice_profile": {
            "id": str(context.invoice_profile.id),
            "profile_key": context.invoice_profile.profile_key,
            "display_name": context.invoice_profile.display_name,
            "issuer_legal_name": context.invoice_profile.issuer_legal_name,
            "tax_identifier": context.invoice_profile.tax_identifier,
            "issuer_email": context.invoice_profile.issuer_email,
            "tax_behavior": dict(context.invoice_profile.tax_behavior),
            "invoice_footer": context.invoice_profile.invoice_footer,
            "receipt_footer": context.invoice_profile.receipt_footer,
        },
        "billing_descriptor": {
            "id": str(context.billing_descriptor.id),
            "descriptor_key": context.billing_descriptor.descriptor_key,
            "statement_descriptor": context.billing_descriptor.statement_descriptor,
            "soft_descriptor": context.billing_descriptor.soft_descriptor,
            "support_phone": context.billing_descriptor.support_phone,
            "support_url": context.billing_descriptor.support_url,
            "is_default": context.billing_descriptor.is_default,
        },
        "pricebook": {
            "id": str(context.pricebook.id),
            "pricebook_key": context.pricebook.pricebook_key,
            "currency_code": context.pricebook.currency_code,
            "region_code": context.pricebook.region_code,
            "discount_rules": dict(context.pricebook.discount_rules),
            "renewal_pricing_policy": dict(context.pricebook.renewal_pricing_policy),
        },
        "pricebook_entry": {
            "id": str(context.pricebook_entry.id),
            "visible_price": float(context.pricebook_entry.visible_price),
            "compare_at_price": (
                float(context.pricebook_entry.compare_at_price)
                if context.pricebook_entry.compare_at_price is not None
                else None
            ),
            "included_addon_codes": list(context.pricebook_entry.included_addon_codes),
            "display_order": context.pricebook_entry.display_order,
        },
        "offer": {
            "id": str(context.offer.id),
            "offer_key": context.offer.offer_key,
            "display_name": context.offer.display_name,
            "subscription_plan_id": str(context.offer.subscription_plan_id),
            "included_addon_codes": list(context.offer.included_addon_codes),
            "sale_channels": list(context.offer.sale_channels),
            "visibility_rules": dict(context.offer.visibility_rules),
            "invite_bundle": dict(context.offer.invite_bundle),
            "trial_eligible": context.offer.trial_eligible,
            "gift_eligible": context.offer.gift_eligible,
            "referral_eligible": context.offer.referral_eligible,
            "renewal_incentives": dict(context.offer.renewal_incentives),
        },
        "legal_document_set": {
            "id": str(context.legal_document_set.id),
            "set_key": context.legal_document_set.set_key,
            "display_name": context.legal_document_set.display_name,
            "policy_version_id": str(context.legal_document_set.policy_version_id),
            "documents": [
                {
                    "id": str(item.legal_document.id),
                    "document_key": item.legal_document.document_key,
                    "document_type": item.legal_document.document_type,
                    "locale": item.legal_document.locale,
                    "required": item.required,
                    "display_order": item.display_order,
                    "policy_version_id": str(item.legal_document.policy_version_id),
                }
                for item in context.legal_document_set.documents
            ],
        },
        "program_eligibility_policy": (
            {
                "id": str(context.program_eligibility_policy.id),
                "policy_key": context.program_eligibility_policy.policy_key,
                "subject_type": context.program_eligibility_policy.subject_type,
                "subscription_plan_id": (
                    str(context.program_eligibility_policy.subscription_plan_id)
                    if context.program_eligibility_policy.subscription_plan_id
                    else None
                ),
                "offer_id": (
                    str(context.program_eligibility_policy.offer_id)
                    if context.program_eligibility_policy.offer_id
                    else None
                ),
                "invite_allowed": context.program_eligibility_policy.invite_allowed,
                "referral_credit_allowed": context.program_eligibility_policy.referral_credit_allowed,
                "creator_affiliate_allowed": context.program_eligibility_policy.creator_affiliate_allowed,
                "performance_allowed": context.program_eligibility_policy.performance_allowed,
                "reseller_allowed": context.program_eligibility_policy.reseller_allowed,
                "renewal_commissionable": context.program_eligibility_policy.renewal_commissionable,
                "addon_commissionable": context.program_eligibility_policy.addon_commissionable,
            }
            if context.program_eligibility_policy
            else None
        ),
    }


def build_request_snapshot(
    *,
    storefront_key: str,
    pricebook_key: str | None,
    offer_key: str | None,
    plan_id: str,
    currency: str,
    channel: str,
    promo_code: str | None,
    partner_code: str | None,
    use_wallet: float,
    addons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "storefront_key": storefront_key,
        "pricebook_key": pricebook_key,
        "offer_key": offer_key,
        "plan_id": plan_id,
        "currency": currency,
        "channel": channel,
        "promo_code": promo_code,
        "partner_code": partner_code,
        "use_wallet": use_wallet,
        "addons": addons,
    }
