from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.infrastructure.database.models.pricebook_model import PricebookModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.partner_repo import PartnerRepository
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository
from src.presentation.dependencies.database import get_db

from .schemas import (
    StorefrontAnalyticsContractResponse,
    StorefrontAttributionContractResponse,
    StorefrontBrandingBoundaryResponse,
    StorefrontPreviewResponse,
    StorefrontPricingBoundaryResponse,
    StorefrontPricingOfferResponse,
    StorefrontRouteContractResponse,
)

router = APIRouter(prefix="/storefronts", tags=["storefronts"])

_PUBLIC_LAUNCH_REQUIRED_STAGES = ["S3-STAGE-15", "S3-STAGE-16", "S3-STAGE-17"]
_ALLOWED_CUSTOMIZATIONS = [
    "approved_logo",
    "approved_display_name",
    "approved_support_contact",
    "approved_locale_copy",
]
_PROHIBITED_CLAIMS = [
    "custom_legal_promises",
    "no_logs_claim_without_approval",
    "unapproved_refund_terms",
    "unapproved_security_guarantees",
]


@router.get("/{storefront_key}/preview", response_model=StorefrontPreviewResponse)
async def preview_storefront_contract(
    storefront_key: str = Path(..., min_length=1, max_length=50),
    partner_code: str | None = Query(None, min_length=1, max_length=30),
    db: AsyncSession = Depends(get_db),
) -> StorefrontPreviewResponse:
    """Return a read-only reseller storefront contract preview.

    The endpoint is intentionally side-effect free: it does not create quotes,
    checkout sessions, attribution touchpoints, or commercial bindings.
    """

    storefront_repo = StorefrontRepository(db)
    storefront = await storefront_repo.get_storefront_by_key(storefront_key)
    if storefront is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storefront not found")

    brand = await storefront_repo.get_brand_by_id(storefront.brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storefront brand not found")

    pricebooks = await PricebookRepository(db).list_active(storefront_id=storefront.id)
    attribution_contract = await _build_attribution_contract(
        partner_code=partner_code,
        db=db,
    )

    return StorefrontPreviewResponse(
        storefront_id=storefront.id,
        storefront_key=storefront.storefront_key,
        display_name=storefront.display_name,
        status=storefront.status,
        route_contract=_build_route_contract(storefront),
        branding_boundary=StorefrontBrandingBoundaryResponse(
            brand_id=brand.id,
            brand_key=brand.brand_key,
            brand_display_name=brand.display_name,
            brand_status=brand.status,
            allowed_customizations=list(_ALLOWED_CUSTOMIZATIONS),
            prohibited_claims=list(_PROHIBITED_CLAIMS),
            legal_copy_source="CyberVPN approved legal pack",
        ),
        pricing_boundary=_build_pricing_boundary(pricebooks),
        attribution_contract=attribution_contract,
        analytics_contract=StorefrontAnalyticsContractResponse(
            preview_records_touchpoint=False,
            checkout_records_storefront_origin=bool(settings.partner_attribution_enabled),
            checkout_records_explicit_code=bool(settings.partner_attribution_enabled),
            expected_dimensions=[
                "storefront_id",
                "storefront_key",
                "partner_account_id",
                "partner_code_id",
                "owner_type",
                "owner_source",
                "sale_channel",
            ],
        ),
        generated_at=datetime.now(UTC),
    )


def _build_route_contract(storefront: StorefrontModel) -> StorefrontRouteContractResponse:
    route_status = "preview" if storefront.status == "active" else "inactive"
    return StorefrontRouteContractResponse(
        storefront_key=storefront.storefront_key,
        host=storefront.host,
        preview_api_path=f"/api/v1/storefronts/{storefront.storefront_key}/preview",
        customer_entry_path=f"/s/{storefront.storefront_key}",
        route_status=route_status,
        public_launch_requires_stages=list(_PUBLIC_LAUNCH_REQUIRED_STAGES),
        checkout_side_effects=False,
    )


def _build_pricing_boundary(pricebooks: list[PricebookModel]) -> StorefrontPricingBoundaryResponse:
    offers: list[StorefrontPricingOfferResponse] = []
    for pricebook in pricebooks:
        for entry in sorted(pricebook.entries, key=lambda item: (item.display_order, str(item.id))):
            offer = entry.offer
            offers.append(
                StorefrontPricingOfferResponse(
                    pricebook_id=pricebook.id,
                    pricebook_key=pricebook.pricebook_key,
                    pricebook_display_name=pricebook.display_name,
                    currency_code=pricebook.currency_code,
                    region_code=pricebook.region_code,
                    offer_id=offer.id,
                    offer_key=offer.offer_key,
                    offer_display_name=offer.display_name,
                    plan_id=offer.subscription_plan_id,
                    visible_price=float(entry.visible_price),
                    compare_at_price=float(entry.compare_at_price) if entry.compare_at_price is not None else None,
                    sale_channels=list(offer.sale_channels or []),
                )
            )

    return StorefrontPricingBoundaryResponse(
        display_policy="show native storefront price only; never show base price plus reseller markup",
        finance_policy="pricebook entries must be approved by finance policy before public launch",
        offers=offers,
    )


async def _build_attribution_contract(
    *,
    partner_code: str | None,
    db: AsyncSession,
) -> StorefrontAttributionContractResponse:
    if not partner_code:
        return StorefrontAttributionContractResponse(
            owner_type="direct_store",
            owner_source="none",
            partner_code_required_for_reseller=True,
            touchpoint_policy="preview does not record touchpoints; checkout records storefront origin when enabled",
        )

    code_model = await PartnerRepository(db).get_active_code_by_code(partner_code)
    if code_model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Partner code not found or inactive")

    partner_account = None
    if code_model.partner_account_id is not None:
        partner_account = await PartnerAccountRepository(db).get_account_by_id(code_model.partner_account_id)

    owner_type = "reseller" if code_model.partner_account_id is not None else "affiliate"
    return StorefrontAttributionContractResponse(
        owner_type=owner_type,
        owner_source="explicit_code",
        partner_account_id=code_model.partner_account_id,
        partner_account_key=partner_account.account_key if partner_account is not None else None,
        partner_account_status=partner_account.status if partner_account is not None else None,
        partner_code_id=code_model.id,
        partner_code=code_model.code,
        partner_code_required_for_reseller=True,
        touchpoint_policy="preview does not record touchpoints; checkout records explicit_code when enabled",
    )
