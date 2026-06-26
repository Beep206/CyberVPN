from __future__ import annotations

import logging
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import ConfigService
from src.application.use_cases.customer_onboarding import (
    ApplyCustomerOnboardingGrowthCodeUseCase,
    CustomerOnboardingAppliedCode,
    CustomerOnboardingApplyResult,
    CustomerOnboardingCodeApplier,
    CustomerOnboardingCurrentState,
    CustomerOnboardingFlowTokenService,
    CustomerOnboardingSkipResult,
    CustomerOnboardingUnavailableError,
    GetCurrentCustomerOnboardingUseCase,
    SkipCustomerOnboardingUseCase,
)
from src.application.use_cases.gifts import RedeemGiftCodeUseCase
from src.application.use_cases.growth_codes import GrowthCodeResolutionOutcome, ResolveGrowthCodeUseCase
from src.application.use_cases.invites.redeem_invite import RedeemInviteUseCase
from src.domain.enums import (
    GrowthCodeActionContext,
    GrowthCodeRejectReason,
    GrowthCodeResolutionStatus,
    GrowthCodeType,
    GrowthCodeWrongContextTarget,
)
from src.domain.exceptions import (
    InviteCodeAlreadyUsedError,
    InviteCodeExpiredError,
    InviteCodeNotFoundError,
)
from src.infrastructure.database.repositories.customer_onboarding_repo import (
    CustomerOnboardingStateSqlAlchemyRepository,
)
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.auth_realms import RealmResolution, get_request_customer_realm
from src.presentation.dependencies.database import get_db

from .schemas import (
    CustomerOnboardingApplyRequest,
    CustomerOnboardingApplyResponse,
    CustomerOnboardingCurrentResponse,
    CustomerOnboardingSkipRequest,
    CustomerOnboardingSkipResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer/onboarding", tags=["customer-onboarding"])

_CUSTOMER_ONBOARDING_SURFACE = "customer_onboarding"


@router.get("/current", response_model=CustomerOnboardingCurrentResponse)
async def get_current_customer_onboarding(
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingCurrentResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    state = await GetCurrentCustomerOnboardingUseCase(
        runtime_config=runtime_config,
        state_repo=CustomerOnboardingStateSqlAlchemyRepository(db),
        flow_tokens=CustomerOnboardingFlowTokenService(),
    ).execute(user_id=user_id)
    return _current_response(state)


@router.post("/growth-code/apply", response_model=CustomerOnboardingApplyResponse)
async def apply_customer_onboarding_growth_code(
    payload: CustomerOnboardingApplyRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    current_realm: RealmResolution = Depends(get_request_customer_realm),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingApplyResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    try:
        result = await ApplyCustomerOnboardingGrowthCodeUseCase(
            runtime_config=runtime_config,
            state_repo=CustomerOnboardingStateSqlAlchemyRepository(db),
            flow_tokens=CustomerOnboardingFlowTokenService(),
        ).execute(
            user_id=user_id,
            code=payload.code,
            flow_token=payload.flow_token,
            idempotency_key=payload.idempotency_key,
            code_applier=CustomerOnboardingGrowthCodeApplier(db, current_realm=current_realm),
        )
    except CustomerOnboardingUnavailableError as exc:
        await db.rollback()
        raise _onboarding_http_error(exc) from exc
    if result.commit_required:
        await db.commit()
    return _apply_response(result)


@router.post("/growth-code/skip", response_model=CustomerOnboardingSkipResponse)
async def skip_customer_onboarding_growth_code(
    payload: CustomerOnboardingSkipRequest,
    user_id: UUID = Depends(get_current_mobile_user_id),
    db: AsyncSession = Depends(get_db),
) -> CustomerOnboardingSkipResponse:
    runtime_config = await ConfigService(SystemConfigRepository(db)).get_customer_onboarding_runtime_config()
    try:
        result = await SkipCustomerOnboardingUseCase(
            runtime_config=runtime_config,
            state_repo=CustomerOnboardingStateSqlAlchemyRepository(db),
            flow_tokens=CustomerOnboardingFlowTokenService(),
        ).execute(
            user_id=user_id,
            flow_token=payload.flow_token,
            idempotency_key=payload.idempotency_key,
        )
    except CustomerOnboardingUnavailableError as exc:
        raise _onboarding_http_error(exc) from exc
    if result.commit_required:
        await db.commit()
    return _skip_response(result)


def _current_response(state: CustomerOnboardingCurrentState) -> CustomerOnboardingCurrentResponse:
    return CustomerOnboardingCurrentResponse(
        required=state.required,
        status=state.status,
        flow_key=state.flow_key,
        version=state.version,
        allowed_code_types=cast(list[Literal["promo", "invite", "gift"]], list(state.allowed_code_types)),
        flow_token=state.flow_token,
        message_key=state.message_key,
        server_state_available=state.server_state_available,
        referral_already_attributed=state.referral_already_attributed,
    )


def _apply_response(result: CustomerOnboardingApplyResult) -> CustomerOnboardingApplyResponse:
    return CustomerOnboardingApplyResponse(
        status=cast(Literal["pending", "completed", "skipped"], result.status),
        message_key=result.message_key,
        masked_code=result.masked_code,
        next_destination=result.next_destination,
    )


def _skip_response(result: CustomerOnboardingSkipResult) -> CustomerOnboardingSkipResponse:
    return CustomerOnboardingSkipResponse(
        status=cast(Literal["skipped", "completed"], result.status),
        message_key=result.message_key,
        next_destination=result.next_destination,
    )


def _onboarding_http_error(exc: CustomerOnboardingUnavailableError) -> HTTPException:
    logger.info("customer_onboarding_unavailable", extra={"code": exc.code})
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "code": exc.code,
            "message_key": exc.message_key,
        },
    )


class CustomerOnboardingGrowthCodeApplier(CustomerOnboardingCodeApplier):
    def __init__(self, session: AsyncSession, *, current_realm: RealmResolution) -> None:
        self._session = session
        self._current_realm = current_realm
        self._resolver = ResolveGrowthCodeUseCase(session)
        self._invite_redeemer = RedeemInviteUseCase(session)
        self._gift_redeemer = RedeemGiftCodeUseCase(session)

    async def apply_code(
        self,
        *,
        code: str,
        user_id: UUID,
        idempotency_key: str,
        normalized_code_hash: str,
        masked_code: str,
    ) -> CustomerOnboardingAppliedCode:
        del idempotency_key, normalized_code_hash
        outcome = await self._resolver.execute(
            code=code,
            action_context=GrowthCodeActionContext.REDEEM,
            user_id=user_id,
            surface=_CUSTOMER_ONBOARDING_SURFACE,
        )
        if _is_checkout_staged_promo(outcome):
            return CustomerOnboardingAppliedCode(
                result="staged",
                code_type="promo",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                next_destination="/subscriptions",
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                safe_details={"wrong_context_target": GrowthCodeWrongContextTarget.CHECKOUT.value},
            )
        if not outcome.accepted or outcome.code_type is None:
            raise _onboarding_code_rejected(outcome)

        if outcome.code_type == GrowthCodeType.INVITE:
            try:
                redeemed = await self._invite_redeemer.execute(
                    code=code,
                    user_id=user_id,
                    current_realm=self._current_realm,
                )
            except InviteCodeNotFoundError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_NOT_FOUND",
                    message_key="growth_codes.code.not_found",
                    status_code=404,
                ) from exc
            except InviteCodeAlreadyUsedError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_ALREADY_REDEEMED",
                    message_key="growth_codes.invite.already_redeemed",
                    status_code=409,
                ) from exc
            except InviteCodeExpiredError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_EXPIRED",
                    message_key="growth_codes.invite.expired",
                    status_code=410,
                ) from exc
            except ValueError as exc:
                raise CustomerOnboardingUnavailableError(
                    code="CUSTOMER_ONBOARDING_CODE_NOT_ELIGIBLE",
                    message_key="growth_codes.invite.not_eligible",
                    status_code=422,
                ) from exc
            return CustomerOnboardingAppliedCode(
                result="accepted",
                code_type="invite",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                redemption_id=redeemed.redemption.id,
                entitlement_grant_id=redeemed.entitlement_grant_id,
                entitlement_snapshot=redeemed.entitlement_snapshot,
            )

        if outcome.code_type == GrowthCodeType.GIFT:
            try:
                redeemed_gift = await self._gift_redeemer.execute(
                    code=code,
                    user_id=user_id,
                    current_realm=self._current_realm,
                )
            except ValueError as exc:
                raise _gift_redemption_error(str(exc)) from exc
            return CustomerOnboardingAppliedCode(
                result="accepted",
                code_type="gift",
                message_key=outcome.user_message_key,
                masked_code=masked_code,
                resolved_code_id=outcome.resolved_code_id,
                growth_code_id=outcome.growth_code_id,
                redemption_id=redeemed_gift.redemption.id,
                entitlement_grant_id=redeemed_gift.entitlement_grant_id,
                entitlement_snapshot=redeemed_gift.entitlement_snapshot,
            )

        raise _onboarding_code_rejected(outcome)


def _is_checkout_staged_promo(outcome: GrowthCodeResolutionOutcome) -> bool:
    return (
        outcome.code_type == GrowthCodeType.PROMO
        and outcome.result == GrowthCodeResolutionStatus.REJECTED
        and outcome.reject_reason == GrowthCodeRejectReason.CODE_WRONG_CONTEXT
        and outcome.wrong_context_target == GrowthCodeWrongContextTarget.CHECKOUT
    )


def _onboarding_code_rejected(outcome: GrowthCodeResolutionOutcome) -> CustomerOnboardingUnavailableError:
    reject_reason = outcome.reject_reason
    status_code = 422
    error_code = "CUSTOMER_ONBOARDING_CODE_REJECTED"
    if reject_reason == GrowthCodeRejectReason.CODE_NOT_FOUND:
        status_code = 404
        error_code = "CUSTOMER_ONBOARDING_CODE_NOT_FOUND"
    elif reject_reason == GrowthCodeRejectReason.CODE_EXPIRED:
        status_code = 410
        error_code = "CUSTOMER_ONBOARDING_CODE_EXPIRED"
    elif reject_reason in {
        GrowthCodeRejectReason.CODE_ALREADY_REDEEMED,
        GrowthCodeRejectReason.GIFT_ALREADY_REDEEMED,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_BINDING,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PARTNER_CODE,
        GrowthCodeRejectReason.CODE_CONFLICTS_WITH_PROMO,
    }:
        status_code = 409
        error_code = "CUSTOMER_ONBOARDING_CODE_CONFLICT"
    elif reject_reason == GrowthCodeRejectReason.CODE_BLOCKED_BY_RISK:
        status_code = 403
        error_code = "CUSTOMER_ONBOARDING_CODE_BLOCKED"
    return CustomerOnboardingUnavailableError(
        code=error_code,
        message_key=outcome.user_message_key,
        status_code=status_code,
    )


def _gift_redemption_error(detail: str) -> CustomerOnboardingUnavailableError:
    normalized = detail.lower()
    if "not found" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_NOT_FOUND",
            message_key="growth_codes.code.not_found",
            status_code=404,
        )
    if "already redeemed" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_ALREADY_REDEEMED",
            message_key="growth_codes.gift.already_redeemed",
            status_code=409,
        )
    if "expired" in normalized:
        return CustomerOnboardingUnavailableError(
            code="CUSTOMER_ONBOARDING_CODE_EXPIRED",
            message_key="growth_codes.gift.expired",
            status_code=410,
        )
    return CustomerOnboardingUnavailableError(
        code="CUSTOMER_ONBOARDING_CODE_NOT_ELIGIBLE",
        message_key="growth_codes.gift.not_eligible",
        status_code=422,
    )
