from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.invoice_profile_model import InvoiceProfileModel
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class ListInvoiceProfilesUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, include_inactive: bool = False) -> list[InvoiceProfileModel]:
        stmt = select(InvoiceProfileModel).order_by(InvoiceProfileModel.profile_key)
        if not include_inactive:
            stmt = stmt.where(InvoiceProfileModel.status == "active")
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class CreateInvoiceProfileUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StorefrontRepository(session)

    async def execute(
        self,
        *,
        profile_key: str,
        display_name: str,
        issuer_legal_name: str,
        tax_identifier: str | None,
        issuer_email: str | None,
        tax_behavior: dict,
        invoice_footer: str | None,
        receipt_footer: str | None,
        status: str,
    ) -> InvoiceProfileModel:
        model = InvoiceProfileModel(
            profile_key=profile_key.strip(),
            display_name=display_name.strip(),
            issuer_legal_name=issuer_legal_name.strip(),
            tax_identifier=tax_identifier.strip() if tax_identifier else None,
            issuer_email=issuer_email.strip().lower() if issuer_email else None,
            tax_behavior=tax_behavior,
            invoice_footer=invoice_footer.strip() if invoice_footer else None,
            receipt_footer=receipt_footer.strip() if receipt_footer else None,
            status=status,
        )
        created = await self._repo.create_invoice_profile(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created
