from __future__ import annotations

from typing import Any

from src.application.use_cases.commerce_sessions.context_resolution import ResolvedQuoteContext
from src.application.use_cases.growth_code_sets.snapshots import attach_growth_checkout_integrity
from src.application.use_cases.growth_codes.hashing import hash_growth_code
from src.application.use_cases.payments.checkout import CheckoutResult
from src.shared.security.encryption import EncryptionError, get_oauth_token_encryption_service

PROTECTED_CODE_VALUE_PREFIX = "enc:growth-code-snapshot:v1:"


def _normalize_optional_code(value: str | None) -> str | None:
    normalized = value.strip() if value else None
    return normalized or None


def _safe_code_ref(value: str | None, *, include_encrypted_value: bool = False) -> dict[str, Any] | None:
    normalized = _normalize_optional_code(value)
    if normalized is None:
        return None
    code_ref: dict[str, Any] = {
        "redacted": True,
        "code_hash": hash_growth_code(normalized),
        "code_prefix": _safe_code_prefix(normalized),
        "code_length": len(normalized),
    }
    if include_encrypted_value:
        service = get_oauth_token_encryption_service()
        if service is not None:
            code_ref["encrypted_value"] = f"{PROTECTED_CODE_VALUE_PREFIX}{service.encrypt(normalized)}"
        else:
            code_ref["encrypted_value"] = None
            code_ref["encryption_unavailable"] = True
    return code_ref


def _safe_code_prefix(value: str) -> str:
    return value[:3].upper() if len(value) > 4 else "***"


def _safe_code_label(value: str | None) -> str | None:
    code_ref = _safe_code_ref(value)
    if code_ref is None:
        return None
    return f"{code_ref['code_prefix']}...{code_ref['code_hash'][:12]}"


def restore_protected_request_code(request_snapshot: dict[str, Any], field_name: str) -> str | None:
    """Recover encrypted request code for short-lived quote drift checks.

    Legacy snapshots may still contain the raw field; new snapshots store raw
    codes only as encrypted values under ``<field>_ref``.
    """
    raw_value = _normalize_optional_code(request_snapshot.get(field_name))
    if raw_value is not None:
        return raw_value
    code_ref = request_snapshot.get(f"{field_name}_ref")
    return _restore_protected_code_ref(code_ref)


def restore_protected_request_codes(request_snapshot: dict[str, Any]) -> list[dict[str, str | None]]:
    """Recover encrypted multi-code basket entries for quote drift checks."""
    raw_codes = request_snapshot.get("codes")
    if isinstance(raw_codes, list):
        restored = []
        for item in raw_codes:
            if not isinstance(item, dict):
                continue
            raw_code = _normalize_optional_code(item.get("code"))
            if raw_code is not None:
                restored.append({"code": raw_code, "client_slot_id": item.get("client_slot_id")})
        if restored:
            return restored

    restored_refs = []
    for item in request_snapshot.get("codes_ref") or []:
        if not isinstance(item, dict):
            continue
        code = _restore_protected_code_ref(item.get("code_ref"))
        if code is not None:
            restored_refs.append({"code": code, "client_slot_id": item.get("client_slot_id")})
    return restored_refs


def _restore_protected_code_ref(code_ref: object) -> str | None:
    if not isinstance(code_ref, dict):
        return None
    encrypted_value = code_ref.get("encrypted_value")
    if not isinstance(encrypted_value, str) or not encrypted_value.startswith(PROTECTED_CODE_VALUE_PREFIX):
        return None
    service = get_oauth_token_encryption_service()
    if service is None:
        raise ValueError("Encrypted checkout code cannot be restored without an encryption key")
    try:
        return service.decrypt(encrypted_value.removeprefix(PROTECTED_CODE_VALUE_PREFIX))
    except EncryptionError as exc:
        raise ValueError("Encrypted checkout code could not be restored") from exc


def serialize_checkout_result(
    result: CheckoutResult,
    *,
    subscription_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entitlements_snapshot = dict(result.entitlements_snapshot or {})
    if subscription_snapshot is not None:
        entitlements_snapshot["subscription_snapshot"] = subscription_snapshot

    snapshot = {
        "base_price": float(result.base_price),
        "addon_amount": float(result.addon_amount),
        "displayed_price": float(result.displayed_price),
        "discount_amount": float(result.discount_amount),
        "wallet_amount": float(result.wallet_amount),
        "gateway_amount": float(result.gateway_amount),
        "partner_markup": float(result.partner_markup),
        "is_zero_gateway": result.is_zero_gateway,
        "requires_external_payment": not result.is_zero_gateway,
        "settlement_mode": "internal_zero" if result.is_zero_gateway else "external_gateway",
        "next_action": "commit_and_activate" if result.is_zero_gateway else "create_payment_attempt",
        "plan_id": str(result.plan_id) if result.plan_id else None,
        "plan_name": result.plan_name,
        "duration_days": result.duration_days,
        "promo_code_id": str(result.promo_code_id) if result.promo_code_id else None,
        "partner_code_id": str(result.partner_code_id) if result.partner_code_id else None,
        "partner_commission_contract_snapshot": (
            dict(result.partner_commission_contract_snapshot) if result.partner_commission_contract_snapshot else None
        ),
        "private_catalog": dict(result.private_catalog_snapshot or {}),
        "private_catalog_grant_id": (
            str(result.private_catalog_grant_id) if result.private_catalog_grant_id is not None else None
        ),
        "code_input": _safe_code_label(result.code_input),
        "code_input_ref": _safe_code_ref(result.code_input),
        "code_resolution": _serialize_code_resolution(result),
        "discounts": [
            {
                "type": discount.discount_type,
                "code": _safe_code_label(discount.code),
                "code_ref": _safe_code_ref(discount.code),
                "amount": float(discount.amount),
                "policy_version_id": str(discount.policy_version_id) if discount.policy_version_id else None,
            }
            for discount in result.discounts
        ],
        "growth_effects": {
            "discount": {
                "amount": float(result.discount_amount),
                "currency": result.currency_code,
                "discount_count": len(result.discounts),
            },
            "benefits_preview": [
                benefit
                for application in result.code_set_applications
                for benefit in list(application.get("benefits") or [])
            ],
        },
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
        "entitlements_snapshot": entitlements_snapshot,
    }
    return attach_growth_checkout_integrity(snapshot, producer="cybervpn-backend.quote_serialization")


def build_subscription_snapshot(
    *,
    result: CheckoutResult,
    context: ResolvedQuoteContext,
) -> dict[str, Any]:
    entitlements = dict((result.entitlements_snapshot or {}).get("effective_entitlements") or {})
    return {
        "snapshot_version": "commercial_subscription_snapshot.v1",
        "plan": {
            "plan_id": str(result.plan_id) if result.plan_id else None,
            "plan_name": result.plan_name,
            "duration_days": result.duration_days,
            "offer_id": str(context.offer.id),
            "offer_key": context.offer.offer_key,
            "offer_version_status": context.offer.version_status,
            "offer_effective_from": context.offer.effective_from.isoformat(),
        },
        "price": {
            "base_price": str(result.base_price),
            "addon_amount": str(result.addon_amount),
            "displayed_price": str(result.displayed_price),
            "discount_amount": str(result.discount_amount),
            "wallet_amount": str(result.wallet_amount),
            "gateway_amount": str(result.gateway_amount),
            "partner_markup": str(result.partner_markup),
            "commission_base_amount": str(result.commission_base_amount),
            "currency": context.pricebook.currency_code.upper(),
            "pricebook_id": str(context.pricebook.id),
            "pricebook_key": context.pricebook.pricebook_key,
            "pricebook_entry_id": str(context.pricebook_entry.id),
            "pricebook_region_code": context.pricebook.region_code,
        },
        "country": {
            "pricing_country": context.pricebook.region_code,
            "payment_country": context.pricebook.region_code,
        },
        "addons": [
            {
                "addon_id": str(line.addon_id),
                "code": line.code,
                "qty": line.qty,
                "unit_price": str(line.unit_price),
                "total_price": str(line.total_price),
                "location_code": line.location_code,
                "delta_entitlements": dict(line.delta_entitlements or {}),
            }
            for line in result.addons
        ],
        "entitlements": entitlements,
        "provisioning_profile": {
            "source": "entitlements_snapshot",
            "device_limit": entitlements.get("device_limit"),
            "traffic_limit_bytes": entitlements.get("traffic_limit_bytes"),
            "traffic_policy": entitlements.get("traffic_policy"),
            "connection_modes": list(entitlements.get("connection_modes") or []),
            "server_pool": list(entitlements.get("server_pool") or []),
            "support_sla": entitlements.get("support_sla"),
            "dedicated_ip_count": entitlements.get("dedicated_ip_count"),
        },
    }


def _serialize_code_resolution(result: CheckoutResult) -> dict[str, Any] | None:
    if result.code_resolution is None:
        return None
    resolution = result.code_resolution
    return {
        "accepted": resolution.accepted,
        "code_type": resolution.code_type.value if resolution.code_type else None,
        "action_context": resolution.action_context.value,
        "result": resolution.result.value,
        "reject_reason": resolution.reject_reason.value if resolution.reject_reason else None,
        "conflict_code": resolution.conflict_code,
        "wrong_context_target": resolution.wrong_context_target.value if resolution.wrong_context_target else None,
        "issuer_type": resolution.issuer_type,
        "owner_type": resolution.owner_type,
        "resolved_code_id": str(resolution.resolved_code_id) if resolution.resolved_code_id else None,
        "growth_code_id": str(resolution.growth_code_id) if resolution.growth_code_id else None,
        "promo_code_id": str(resolution.promo_code_id) if resolution.promo_code_id else None,
        "partner_code_id": str(resolution.partner_code_id) if resolution.partner_code_id else None,
        "user_message_key": resolution.user_message_key,
        "policy_snapshot": dict(resolution.policy_snapshot or {}),
        "reservation_id": str(result.reservation_id) if result.reservation_id else None,
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
    code_input: str | None,
    promo_code: str | None,
    partner_code: str | None,
    use_wallet: float,
    addons: list[dict[str, Any]],
    private_catalog_grant_id: str | None = None,
    codes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "storefront_key": storefront_key,
        "pricebook_key": pricebook_key,
        "offer_key": offer_key,
        "plan_id": plan_id,
        "currency": currency,
        "channel": channel,
        "code_input": None,
        "promo_code": None,
        "partner_code": None,
        "code_input_ref": _safe_code_ref(code_input, include_encrypted_value=True),
        "promo_code_ref": _safe_code_ref(promo_code, include_encrypted_value=True),
        "partner_code_ref": _safe_code_ref(partner_code, include_encrypted_value=True),
        "codes": None,
        "codes_ref": [
            {
                "client_slot_id": item.get("client_slot_id"),
                "code_ref": _safe_code_ref(str(item.get("code") or ""), include_encrypted_value=True),
            }
            for item in codes or []
        ],
        "private_catalog_grant_id": private_catalog_grant_id,
        "use_wallet": use_wallet,
        "addons": addons,
    }
