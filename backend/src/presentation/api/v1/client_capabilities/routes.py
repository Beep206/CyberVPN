"""Runtime client capability contract.

This endpoint is intentionally public: clients use it to hide actions that the
backend policy/runtime would reject anyway. It must not expose secrets,
provider credentials, internal URLs, or user-specific authorization state.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import (
    ConfigService,
    CustomerOnboardingRuntimeConfig,
    CustomerSiteRuntimeConfig,
)
from src.config.settings import settings
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.database import get_db

from .schemas import (
    ClientCapabilityResponse,
    ClientGrowthCapabilities,
    ClientOnboardingCapabilities,
    ClientPartnerCapabilities,
    ClientPaymentCapabilities,
    ClientSiteCapabilities,
    ClientSubscriptionCapabilities,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])


def _build_client_capabilities(
    *,
    referral_runtime_enabled: bool,
    site_runtime: CustomerSiteRuntimeConfig | None = None,
    onboarding_runtime: CustomerOnboardingRuntimeConfig | None = None,
) -> ClientCapabilityResponse:
    """Build the public client capability snapshot from runtime settings."""

    site_runtime = site_runtime or CustomerSiteRuntimeConfig()
    onboarding_runtime = onboarding_runtime or CustomerOnboardingRuntimeConfig()
    invite_runtime_ready = settings.checkout_code_discounts_enabled or onboarding_runtime.available
    growth_hub = any(
        (
            invite_runtime_ready,
            referral_runtime_enabled,
            settings.promo_codes_enabled,
            settings.gift_codes_enabled,
            settings.checkout_code_discounts_enabled,
        )
    )

    return ClientCapabilityResponse(
        payments=ClientPaymentCapabilities(
            web_checkout=settings.payments_enabled,
            telegram_stars=settings.telegram_stars_enabled,
            cryptobot=settings.payments_enabled,
            manual_invoice=not settings.payments_enabled,
            autorenewal=settings.payment_autorenewal_enabled,
        ),
        growth=ClientGrowthCapabilities(
            invites=invite_runtime_ready,
            referral=referral_runtime_enabled,
            promo_codes=settings.promo_codes_enabled,
            gift_codes=settings.gift_codes_enabled,
            checkout_code_discounts=settings.checkout_code_discounts_enabled,
            growth_hub=growth_hub,
        ),
        subscriptions=ClientSubscriptionCapabilities(
            addons=settings.stage1_addons_enabled,
            trial=settings.stage1_trial_provisioning_enabled,
            paid_provisioning=settings.stage1_paid_provisioning_enabled,
        ),
        partner=ClientPartnerCapabilities(
            portal=settings.partner_portal_enabled,
            applications=settings.partner_applications_enabled,
            codes=settings.partner_codes_enabled,
            attribution=settings.partner_attribution_enabled,
            storefronts=settings.partner_storefronts_enabled,
            reporting=settings.partner_reporting_enabled,
            settlement_sandbox=settings.partner_settlement_sandbox_enabled,
            webhooks=settings.partner_webhooks_enabled,
            payouts=settings.partner_payouts_enabled,
            event_backbone=settings.partner_event_backbone_enabled,
        ),
        site=ClientSiteCapabilities(
            customer_site_mode=site_runtime.mode,
            cabinet_only=site_runtime.cabinet_only,
            version=site_runtime.version,
            public_hosts=list(site_runtime.public_hosts),
            cabinet_hosts=list(site_runtime.cabinet_hosts),
            cabinet_destination_path=site_runtime.cabinet_destination_path,
            allowed_path_prefixes=list(site_runtime.allowed_path_prefixes),
            cabinet_allowed_prefixes=list(site_runtime.cabinet_allowed_prefixes),
            cabinet_marketing_route_action=site_runtime.cabinet_marketing_route_action,
            public_marketing_destination_path=site_runtime.public_marketing_destination_path,
            legal_path_prefixes=list(site_runtime.legal_path_prefixes),
            operational_path_prefixes=list(site_runtime.operational_path_prefixes),
            preserve_query_keys=list(site_runtime.preserve_query_keys),
        ),
        onboarding=ClientOnboardingCapabilities(
            post_registration_code_prompt=onboarding_runtime.post_registration_code_prompt_enabled,
            web_otp=onboarding_runtime.web_otp_enabled,
            telegram_miniapp=onboarding_runtime.telegram_miniapp_enabled,
            state_store=onboarding_runtime.state_store_ready,
            flow_key=onboarding_runtime.flow_key,
            version=onboarding_runtime.version,
            allowed_code_types=list(onboarding_runtime.allowed_code_types),
            allow_referral_input=onboarding_runtime.allow_referral_input,
            allow_partner_input=onboarding_runtime.allow_partner_input,
            available=onboarding_runtime.available,
        ),
    )


@router.get("/capabilities", response_model=ClientCapabilityResponse)
async def get_client_capabilities(
    db: AsyncSession = Depends(get_db),
) -> ClientCapabilityResponse:
    """Return runtime feature capabilities for public clients."""

    referral_runtime_enabled = False
    site_runtime = CustomerSiteRuntimeConfig()
    onboarding_runtime = CustomerOnboardingRuntimeConfig()
    config_service = ConfigService(SystemConfigRepository(db))
    if settings.referral_enabled:
        try:
            referral_runtime_enabled = await config_service.is_referral_enabled()
        except Exception:
            logger.exception("client_capabilities_referral_config_failed")
            referral_runtime_enabled = False
    try:
        site_runtime = await config_service.get_customer_site_runtime_config()
        onboarding_runtime = await config_service.get_customer_onboarding_runtime_config()
    except Exception:
        logger.exception("client_capabilities_runtime_config_failed")

    return _build_client_capabilities(
        referral_runtime_enabled=referral_runtime_enabled,
        site_runtime=site_runtime,
        onboarding_runtime=onboarding_runtime,
    )
