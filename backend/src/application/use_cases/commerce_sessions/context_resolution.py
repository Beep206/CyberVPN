from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.legal_documents import ResolveLegalDocumentSetUseCase
from src.application.use_cases.merchant_billing import ResolveBillingDescriptorUseCase
from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.models.legal_document_set_model import LegalDocumentSetModel
from src.infrastructure.database.models.merchant_profile_model import MerchantProfileModel
from src.infrastructure.database.models.offer_model import OfferModel
from src.infrastructure.database.models.pricebook_model import PricebookEntryModel, PricebookModel
from src.infrastructure.database.models.program_eligibility_policy_model import ProgramEligibilityPolicyModel
from src.infrastructure.database.models.storefront_model import StorefrontModel
from src.infrastructure.database.repositories.offer_repo import OfferRepository
from src.infrastructure.database.repositories.pricebook_repo import PricebookRepository
from src.infrastructure.database.repositories.program_eligibility_policy_repo import (
    ProgramEligibilityPolicyRepository,
)
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository
from src.presentation.dependencies.auth_realms import RealmResolution


@dataclass(frozen=True)
class ResolvedQuoteContext:
    storefront: StorefrontModel
    merchant_profile: MerchantProfileModel
    invoice_profile: InvoiceProfileModel
    billing_descriptor: BillingDescriptorModel
    pricebook: PricebookModel
    pricebook_entry: PricebookEntryModel
    offer: OfferModel
    legal_document_set: LegalDocumentSetModel
    program_eligibility_policy: ProgramEligibilityPolicyModel | None


class ResolveQuoteContextUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._storefront_repo = StorefrontRepository(session)
        self._offer_repo = OfferRepository(session)
        self._pricebook_repo = PricebookRepository(session)
        self._program_repo = ProgramEligibilityPolicyRepository(session)
        self._legal_sets = ResolveLegalDocumentSetUseCase(session)
        self._billing_descriptor = ResolveBillingDescriptorUseCase(session)

    async def execute(
        self,
        *,
        current_realm: RealmResolution,
        storefront_key: str | None,
        host: str | None,
        subscription_plan_id: UUID,
        pricebook_key: str | None,
        offer_key: str | None,
        currency_code: str,
        sale_channel: str,
    ) -> ResolvedQuoteContext:
        storefront = await self._resolve_storefront(storefront_key=storefront_key, host=host)
        if storefront.status != "active":
            raise ValueError("Storefront is inactive")
        if storefront.auth_realm_id is not None and str(storefront.auth_realm_id) != current_realm.realm_id:
            raise ValueError("Storefront does not belong to the current auth realm")
        if storefront.merchant_profile_id is None:
            raise ValueError("Storefront does not have a merchant profile")

        merchant_profile = await self._storefront_repo.get_merchant_profile_by_id(storefront.merchant_profile_id)
        if merchant_profile is None or merchant_profile.status != "active":
            raise ValueError("Merchant profile not found")
        if merchant_profile.invoice_profile_id is None:
            raise ValueError("Merchant profile does not have an invoice profile")

        invoice_profile = await self._storefront_repo.get_invoice_profile_by_id(merchant_profile.invoice_profile_id)
        if invoice_profile is None or invoice_profile.status != "active":
            raise ValueError("Invoice profile not found")

        billing_descriptor = await self._billing_descriptor.execute(
            merchant_profile_id=merchant_profile.id,
            invoice_profile_id=invoice_profile.id,
        )
        if billing_descriptor is None:
            raise ValueError("Billing descriptor not found")

        pricebook = await self._resolve_pricebook(
            storefront=storefront,
            pricebook_key=pricebook_key,
            currency_code=currency_code,
        )
        if pricebook.merchant_profile_id is not None and pricebook.merchant_profile_id != merchant_profile.id:
            raise ValueError("Pricebook does not belong to the storefront merchant profile")

        offer, pricebook_entry = await self._resolve_offer(
            subscription_plan_id=subscription_plan_id,
            pricebook=pricebook,
            offer_key=offer_key,
            sale_channel=sale_channel,
        )

        legal_document_set = await self._legal_sets.execute(
            storefront_key=storefront.storefront_key,
            realm_key=current_realm.realm_key,
        )
        if legal_document_set is None:
            legal_document_set = await self._legal_sets.execute(storefront_key=storefront.storefront_key)
        if legal_document_set is None:
            raise ValueError("Legal document set not found")

        program_eligibility_policy = await self._resolve_program_eligibility(
            subscription_plan_id=subscription_plan_id,
            offer_id=offer.id,
        )

        return ResolvedQuoteContext(
            storefront=storefront,
            merchant_profile=merchant_profile,
            invoice_profile=invoice_profile,
            billing_descriptor=billing_descriptor,
            pricebook=pricebook,
            pricebook_entry=pricebook_entry,
            offer=offer,
            legal_document_set=legal_document_set,
            program_eligibility_policy=program_eligibility_policy,
        )

    async def _resolve_storefront(
        self,
        *,
        storefront_key: str | None,
        host: str | None,
    ) -> StorefrontModel:
        storefront = None
        if storefront_key:
            storefront = await self._storefront_repo.get_storefront_by_key(storefront_key)
        elif host:
            storefront = await self._storefront_repo.get_storefront_by_host(host)
        else:
            raise ValueError("storefront_key or request host is required")

        if storefront is None:
            raise ValueError("Storefront not found")
        return storefront

    async def _resolve_pricebook(
        self,
        *,
        storefront: StorefrontModel,
        pricebook_key: str | None,
        currency_code: str,
    ) -> PricebookModel:
        normalized_currency = currency_code.upper()
        if pricebook_key:
            pricebook = await self._pricebook_repo.get_current_by_key(pricebook_key)
            if pricebook is None:
                raise ValueError("Pricebook not found")
            if pricebook.storefront_id != storefront.id:
                raise ValueError("Pricebook does not belong to the requested storefront")
            if pricebook.currency_code.upper() != normalized_currency:
                raise ValueError("Pricebook currency does not match the requested currency")
            return pricebook

        candidates = await self._pricebook_repo.list_active(
            storefront_id=storefront.id,
            currency_code=normalized_currency,
        )
        if not candidates:
            raise ValueError("Pricebook not found")
        return candidates[0]

    async def _resolve_offer(
        self,
        *,
        subscription_plan_id: UUID,
        pricebook: PricebookModel,
        offer_key: str | None,
        sale_channel: str,
    ) -> tuple[OfferModel, PricebookEntryModel]:
        entries = list(pricebook.entries)
        if not entries:
            raise ValueError("Pricebook does not contain any entries")

        matching_entries = [
            entry
            for entry in entries
            if entry.offer.subscription_plan_id == subscription_plan_id
            and (
                not entry.offer.sale_channels
                or sale_channel in entry.offer.sale_channels
            )
        ]
        if offer_key is not None:
            matching_entries = [entry for entry in matching_entries if entry.offer.offer_key == offer_key]
            if not matching_entries:
                offer = await self._offer_repo.get_current_by_key(offer_key)
                if offer is None:
                    raise ValueError("Offer not found")
                raise ValueError("Offer is not available in the selected pricebook")

        if not matching_entries:
            raise ValueError("Offer not found for the selected plan")

        pricebook_entry = sorted(matching_entries, key=lambda entry: (entry.display_order, str(entry.id)))[0]
        return pricebook_entry.offer, pricebook_entry

    async def _resolve_program_eligibility(
        self,
        *,
        subscription_plan_id: UUID,
        offer_id: UUID,
    ) -> ProgramEligibilityPolicyModel | None:
        offer_policies = await self._program_repo.list_active(
            subject_type="offer",
            offer_id=offer_id,
        )
        if offer_policies:
            return offer_policies[0]

        plan_policies = await self._program_repo.list_active(
            subject_type="subscription_plan",
            subscription_plan_id=subscription_plan_id,
        )
        if plan_policies:
            return plan_policies[0]
        return None
