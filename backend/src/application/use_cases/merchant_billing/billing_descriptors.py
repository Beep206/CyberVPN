from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.billing_descriptor_model import BillingDescriptorModel
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class ListBillingDescriptorsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        merchant_profile_id=None,
        include_inactive: bool = False,
    ) -> list[BillingDescriptorModel]:
        stmt = select(BillingDescriptorModel).order_by(
            BillingDescriptorModel.merchant_profile_id,
            BillingDescriptorModel.descriptor_key,
        )
        if merchant_profile_id is not None:
            stmt = stmt.where(BillingDescriptorModel.merchant_profile_id == merchant_profile_id)
        if not include_inactive:
            stmt = stmt.where(BillingDescriptorModel.status == "active")
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ResolveBillingDescriptorUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(
        self,
        *,
        merchant_profile_id,
        invoice_profile_id=None,
    ) -> BillingDescriptorModel | None:
        stmt = (
            select(BillingDescriptorModel)
            .where(
                BillingDescriptorModel.merchant_profile_id == merchant_profile_id,
                BillingDescriptorModel.status == "active",
            )
            .order_by(BillingDescriptorModel.is_default.desc(), BillingDescriptorModel.created_at.asc())
        )
        if invoice_profile_id is not None:
            stmt = stmt.where(BillingDescriptorModel.invoice_profile_id == invoice_profile_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()


class CreateBillingDescriptorUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = StorefrontRepository(session)

    async def execute(
        self,
        *,
        descriptor_key: str,
        merchant_profile_id,
        invoice_profile_id,
        statement_descriptor: str,
        soft_descriptor: str | None,
        support_phone: str | None,
        support_url: str | None,
        is_default: bool,
        status: str,
    ) -> BillingDescriptorModel:
        merchant_profile = await self._repo.get_merchant_profile_by_id(merchant_profile_id)
        if merchant_profile is None:
            raise ValueError("Merchant profile not found")
        if invoice_profile_id is not None:
            invoice_profile = await self._repo.get_invoice_profile_by_id(invoice_profile_id)
            if invoice_profile is None:
                raise ValueError("Invoice profile not found")
        if is_default:
            await self._session.execute(
                update(BillingDescriptorModel)
                .where(BillingDescriptorModel.merchant_profile_id == merchant_profile_id)
                .values(is_default=False)
            )

        model = BillingDescriptorModel(
            descriptor_key=descriptor_key.strip(),
            merchant_profile_id=merchant_profile_id,
            invoice_profile_id=invoice_profile_id,
            statement_descriptor=statement_descriptor.strip(),
            soft_descriptor=soft_descriptor.strip() if soft_descriptor else None,
            support_phone=support_phone.strip() if support_phone else None,
            support_url=support_url.strip() if support_url else None,
            is_default=is_default,
            status=status,
        )
        created = await self._repo.create_billing_descriptor(model)
        await self._session.commit()
        await self._session.refresh(created)
        return created
