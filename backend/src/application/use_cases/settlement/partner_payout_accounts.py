from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import (
    PartnerAccountStatus,
    PartnerPayoutAccountApprovalStatus,
    PartnerPayoutAccountStatus,
    PartnerPayoutAccountVerificationStatus,
    PrincipalClass,
    ReserveScope,
    ReserveStatus,
    RiskReviewDecision,
)
from src.infrastructure.database.models.partner_payout_account_model import PartnerPayoutAccountModel
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository
from src.infrastructure.database.repositories.settlement_repo import SettlementRepository


@dataclass(frozen=True)
class PartnerPayoutAccountEligibilityResult:
    partner_payout_account_id: UUID
    partner_account_id: UUID
    eligible: bool
    reason_codes: list[str]
    blocking_risk_review_ids: list[UUID]
    active_reserve_ids: list[UUID]
    checked_at: datetime


def _mask_destination_reference(value: str) -> str:
    normalized = value.strip()
    if len(normalized) <= 8:
        return "*" * len(normalized)
    return f"{normalized[:4]}...{normalized[-4:]}"


def _workspace_risk_subject_key(partner_account_id: UUID) -> str:
    return f"partner_account:{partner_account_id}"


class CreatePartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)
        self._partners = PartnerAccountRepository(session)
        self._risk = RiskSubjectGraphRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID,
        payout_rail: str,
        display_label: str,
        destination_reference: str,
        destination_metadata: dict | None = None,
        settlement_profile_id: UUID | None = None,
        make_default: bool = False,
        created_by_admin_user_id: UUID | None = None,
    ) -> PartnerPayoutAccountModel:
        workspace = await self._partners.get_account_by_id(partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")
        allowed_statuses = {
            PartnerAccountStatus.APPROVED_PROBATION.value,
            PartnerAccountStatus.ACTIVE.value,
            PartnerAccountStatus.RESTRICTED.value,
        }
        if workspace.status not in allowed_statuses:
            raise ValueError(
                "Partner workspace must be approved probation, active, or restricted before adding payout accounts",
            )

        normalized_rail = payout_rail.strip().lower()
        normalized_label = display_label.strip()
        normalized_reference = destination_reference.strip()
        if not normalized_rail:
            raise ValueError("payout_rail is required")
        if not normalized_label:
            raise ValueError("display_label is required")
        if not normalized_reference:
            raise ValueError("destination_reference is required")

        existing = await self._settlement.list_partner_payout_accounts(
            partner_account_id=partner_account_id,
            limit=500,
            offset=0,
        )
        should_be_default = make_default or not existing
        if should_be_default:
            await _clear_default_flags(existing)

        model = PartnerPayoutAccountModel(
            partner_account_id=partner_account_id,
            settlement_profile_id=settlement_profile_id,
            payout_rail=normalized_rail,
            display_label=normalized_label,
            destination_reference=normalized_reference,
            masked_destination=_mask_destination_reference(normalized_reference),
            destination_metadata=dict(destination_metadata or {}),
            verification_status=PartnerPayoutAccountVerificationStatus.PENDING.value,
            approval_status=PartnerPayoutAccountApprovalStatus.PENDING.value,
            account_status=PartnerPayoutAccountStatus.ACTIVE.value,
            is_default=should_be_default,
            created_by_admin_user_id=created_by_admin_user_id,
            default_selected_by_admin_user_id=created_by_admin_user_id if should_be_default else None,
            default_selected_at=datetime.now(UTC) if should_be_default else None,
        )
        created = await self._settlement.create_partner_payout_account(model)
        await self._get_or_create_workspace_risk_subject(partner_account_id)
        await self._session.commit()
        await self._session.refresh(created)
        return created

    async def _get_or_create_workspace_risk_subject(self, partner_account_id: UUID) -> RiskSubjectModel:
        existing = await self._risk.get_subject_by_principal(
            principal_class=PrincipalClass.PARTNER_OPERATOR.value,
            principal_subject=_workspace_risk_subject_key(partner_account_id),
            auth_realm_id=None,
        )
        if existing is not None:
            return existing

        model = RiskSubjectModel(
            principal_class=PrincipalClass.PARTNER_OPERATOR.value,
            principal_subject=_workspace_risk_subject_key(partner_account_id),
            auth_realm_id=None,
            storefront_id=None,
            status="active",
            risk_level="low",
            metadata_payload={
                "synthetic_subject": True,
                "subject_type": "partner_account",
                "partner_account_id": str(partner_account_id),
            },
        )
        return await self._risk.create_subject(model)


class ListPartnerPayoutAccountsUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        partner_account_id: UUID | None = None,
        payout_account_status: str | None = None,
        verification_status: str | None = None,
        approval_status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PartnerPayoutAccountModel]:
        return await self._settlement.list_partner_payout_accounts(
            partner_account_id=partner_account_id,
            payout_account_status=payout_account_status,
            verification_status=verification_status,
            approval_status=approval_status,
            limit=limit,
            offset=offset,
        )


class GetPartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)

    async def execute(self, *, payout_account_id: UUID) -> PartnerPayoutAccountModel | None:
        return await self._settlement.get_partner_payout_account_by_id(payout_account_id)


class VerifyPartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_account_id: UUID,
        verified_by_admin_user_id: UUID,
    ) -> PartnerPayoutAccountModel:
        payout_account = await self._settlement.get_partner_payout_account_by_id(payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")
        if payout_account.account_status == PartnerPayoutAccountStatus.ARCHIVED.value:
            raise ValueError("Archived payout accounts cannot be verified")

        now = datetime.now(UTC)
        payout_account.verification_status = PartnerPayoutAccountVerificationStatus.VERIFIED.value
        payout_account.approval_status = PartnerPayoutAccountApprovalStatus.APPROVED.value
        payout_account.verified_by_admin_user_id = verified_by_admin_user_id
        payout_account.verified_at = now
        payout_account.approved_by_admin_user_id = verified_by_admin_user_id
        payout_account.approved_at = now
        await self._session.commit()
        await self._session.refresh(payout_account)
        return payout_account


class SuspendPartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_account_id: UUID,
        suspended_by_admin_user_id: UUID,
        reason_code: str | None = None,
    ) -> PartnerPayoutAccountModel:
        payout_account = await self._settlement.get_partner_payout_account_by_id(payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")
        if payout_account.account_status == PartnerPayoutAccountStatus.ARCHIVED.value:
            raise ValueError("Archived payout accounts cannot be suspended")

        payout_account.account_status = PartnerPayoutAccountStatus.SUSPENDED.value
        payout_account.is_default = False
        payout_account.suspended_by_admin_user_id = suspended_by_admin_user_id
        payout_account.suspended_at = datetime.now(UTC)
        payout_account.suspension_reason_code = reason_code.strip() if reason_code else None
        await self._session.commit()
        await self._session.refresh(payout_account)
        return payout_account


class ArchivePartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_account_id: UUID,
        archived_by_admin_user_id: UUID,
        reason_code: str | None = None,
    ) -> PartnerPayoutAccountModel:
        payout_account = await self._settlement.get_partner_payout_account_by_id(payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")
        if payout_account.account_status == PartnerPayoutAccountStatus.ARCHIVED.value:
            return payout_account

        payout_account.account_status = PartnerPayoutAccountStatus.ARCHIVED.value
        payout_account.is_default = False
        payout_account.archived_by_admin_user_id = archived_by_admin_user_id
        payout_account.archived_at = datetime.now(UTC)
        payout_account.archive_reason_code = reason_code.strip() if reason_code else None
        await self._session.commit()
        await self._session.refresh(payout_account)
        return payout_account


class MakeDefaultPartnerPayoutAccountUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settlement = SettlementRepository(session)

    async def execute(
        self,
        *,
        payout_account_id: UUID,
        selected_by_admin_user_id: UUID | None = None,
    ) -> PartnerPayoutAccountModel:
        payout_account = await self._settlement.get_partner_payout_account_by_id(payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")
        if payout_account.account_status != PartnerPayoutAccountStatus.ACTIVE.value:
            raise ValueError("Only active payout accounts can be marked as default")

        siblings = await self._settlement.list_partner_payout_accounts(
            partner_account_id=payout_account.partner_account_id,
            limit=500,
            offset=0,
        )
        await _clear_default_flags(siblings)
        payout_account.is_default = True
        payout_account.default_selected_by_admin_user_id = selected_by_admin_user_id
        payout_account.default_selected_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(payout_account)
        return payout_account


class EvaluatePartnerPayoutAccountEligibilityUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._settlement = SettlementRepository(session)
        self._partners = PartnerAccountRepository(session)
        self._risk = RiskSubjectGraphRepository(session)

    async def execute(self, *, payout_account_id: UUID) -> PartnerPayoutAccountEligibilityResult:
        payout_account = await self._settlement.get_partner_payout_account_by_id(payout_account_id)
        if payout_account is None:
            raise ValueError("Partner payout account not found")

        workspace = await self._partners.get_account_by_id(payout_account.partner_account_id)
        if workspace is None:
            raise ValueError("Partner workspace not found")

        reason_codes: set[str] = set()
        blocking_risk_review_ids: list[UUID] = []
        active_reserve_ids: list[UUID] = []

        if workspace.status != PartnerAccountStatus.ACTIVE.value:
            reason_codes.add("workspace_inactive")

        if payout_account.account_status == PartnerPayoutAccountStatus.SUSPENDED.value:
            reason_codes.add("payout_account_suspended")
        if payout_account.account_status == PartnerPayoutAccountStatus.ARCHIVED.value:
            reason_codes.add("payout_account_archived")
        if payout_account.verification_status != PartnerPayoutAccountVerificationStatus.VERIFIED.value:
            reason_codes.add("payout_account_verification_pending")
        if payout_account.approval_status != PartnerPayoutAccountApprovalStatus.APPROVED.value:
            reason_codes.add("payout_account_approval_pending")

        risk_subject = await self._risk.get_subject_by_principal(
            principal_class=PrincipalClass.PARTNER_OPERATOR.value,
            principal_subject=_workspace_risk_subject_key(workspace.id),
            auth_realm_id=None,
        )
        if risk_subject is not None:
            for review in await self._risk.list_open_reviews_for_subject(risk_subject.id):
                if review.decision == RiskReviewDecision.BLOCK.value:
                    reason_codes.add("risk_review_block")
                    blocking_risk_review_ids.append(review.id)
                elif review.decision == RiskReviewDecision.HOLD.value:
                    reason_codes.add("risk_review_hold")
                    blocking_risk_review_ids.append(review.id)

        active_reserves = await self._settlement.list_reserves(
            partner_account_id=workspace.id,
            reserve_status=ReserveStatus.ACTIVE.value,
            limit=500,
            offset=0,
        )
        for reserve in active_reserves:
            if reserve.reserve_scope != ReserveScope.PARTNER_ACCOUNT.value:
                continue
            reason_codes.add("active_partner_reserve")
            active_reserve_ids.append(reserve.id)

        return PartnerPayoutAccountEligibilityResult(
            partner_payout_account_id=payout_account.id,
            partner_account_id=workspace.id,
            eligible=not reason_codes,
            reason_codes=sorted(reason_codes),
            blocking_risk_review_ids=blocking_risk_review_ids,
            active_reserve_ids=active_reserve_ids,
            checked_at=datetime.now(UTC),
        )


async def _clear_default_flags(accounts: list[PartnerPayoutAccountModel]) -> None:
    for account in accounts:
        account.is_default = False
