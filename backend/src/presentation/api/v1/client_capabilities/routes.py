"""Runtime client capability contract.

This endpoint is intentionally public: clients use it to hide actions that the
backend policy/runtime would reject anyway. It must not expose secrets,
provider credentials, internal URLs, or user-specific authorization state.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.config.settings import settings
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.database import get_db

from .schemas import (
    ClientCapabilityResponse,
    ClientGrowthCapabilities,
    ClientPartnerCapabilities,
    ClientPaymentCapabilities,
    ClientSubscriptionCapabilities,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])


def _build_client_capabilities(*, referral_runtime_enabled: bool) -> ClientCapabilityResponse:
    """Build the public client capability snapshot from runtime settings."""

    growth_hub = any(
        (
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
            invites=True,
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
    )


@router.get("/capabilities", response_model=ClientCapabilityResponse)
async def get_client_capabilities(
    db: AsyncSession = Depends(get_db),
) -> ClientCapabilityResponse:
    """Return runtime feature capabilities for public clients."""

    referral_runtime_enabled = False
    if settings.referral_enabled:
        try:
            config_service = ConfigService(SystemConfigRepository(db))
            referral_runtime_enabled = await config_service.is_referral_enabled()
        except Exception:
            logger.exception("client_capabilities_referral_config_failed")
            referral_runtime_enabled = False

    return _build_client_capabilities(referral_runtime_enabled=referral_runtime_enabled)

