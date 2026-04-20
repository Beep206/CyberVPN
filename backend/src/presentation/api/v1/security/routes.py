"""Security management endpoints for anti-phishing, risk, and eligibility."""

import logging
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.auth.anti_phishing import AntiPhishingUseCase
from src.application.use_cases.risk import (
    AttachRiskIdentifierUseCase,
    AttachRiskReviewAttachmentUseCase,
    CreateGovernanceActionUseCase,
    CreateRiskReviewUseCase,
    CreateRiskSubjectUseCase,
    EvaluateEligibilityUseCase,
    GetRiskReviewUseCase,
    ListGovernanceActionsUseCase,
    ListRiskLinksUseCase,
    ListRiskReviewQueueUseCase,
    ListRiskReviewsUseCase,
    ResolveRiskReviewUseCase,
)
from src.domain.enums import AdminRole
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

from .schemas import (
    AntiPhishingCodeResponse,
    AttachRiskIdentifierRequest,
    AttachRiskIdentifierResponse,
    AttachRiskReviewAttachmentRequest,
    CreateGovernanceActionRequest,
    CreateRiskReviewRequest,
    CreateRiskSubjectRequest,
    DeleteAntiPhishingCodeResponse,
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    GovernanceActionResponse,
    ResolveRiskReviewRequest,
    RiskLinkResponse,
    RiskReviewAttachmentResponse,
    RiskReviewDetailResponse,
    RiskReviewQueueItemResponse,
    RiskReviewResponse,
    RiskSubjectResponse,
    SetAntiPhishingCodeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security", tags=["security"])


def _build_risk_review_queue_item_response(item) -> RiskReviewQueueItemResponse:
    return RiskReviewQueueItemResponse(
        review=RiskReviewResponse.model_validate(item.review),
        subject=RiskSubjectResponse.model_validate(item.subject),
        attachment_count=item.attachment_count,
        governance_action_count=item.governance_action_count,
    )


def _build_risk_review_detail_response(detail) -> RiskReviewDetailResponse:
    return RiskReviewDetailResponse(
        review=RiskReviewResponse.model_validate(detail.review),
        subject=RiskSubjectResponse.model_validate(detail.subject),
        attachments=[RiskReviewAttachmentResponse.model_validate(item) for item in detail.attachments],
        governance_actions=[GovernanceActionResponse.model_validate(item) for item in detail.governance_actions],
    )


@router.post(
    "/antiphishing",
    response_model=AntiPhishingCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update anti-phishing code",
    description="Set or update the authenticated user's anti-phishing code for email security.",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded (10 requests per hour)"},
    },
)
async def set_antiphishing_code(
    request: SetAntiPhishingCodeRequest,
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> AntiPhishingCodeResponse:
    """Set or update the user's anti-phishing code.

    The code will be displayed in emails from the platform to help users
    verify email authenticity and prevent phishing attacks.

    Rate limited to 10 requests per hour per user.
    """
    # Rate limiting: 10 requests per hour per user
    rate_limit_key = f"antiphishing_set:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 10

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    try:
        await use_case.set_code(user_id=current_user.id, code=request.code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    await pipe.incr(rate_limit_key)
    await pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    logger.info(
        "Anti-phishing code set",
        extra={"user_id": str(current_user.id)},
    )

    route_operations_total.labels(route="security", action="set_antiphishing", status="success").inc()
    return AntiPhishingCodeResponse(code=request.code)


@router.get(
    "/antiphishing",
    response_model=AntiPhishingCodeResponse,
    summary="Get current anti-phishing code",
    description="Retrieve the authenticated user's current anti-phishing code.",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def get_antiphishing_code(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> AntiPhishingCodeResponse:
    """Get the user's current anti-phishing code.

    Returns null if no code has been set.
    """
    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    code = await use_case.get_code(user_id=current_user.id)

    logger.info(
        "Anti-phishing code retrieved",
        extra={"user_id": str(current_user.id), "code_set": code is not None},
    )

    route_operations_total.labels(route="security", action="get_antiphishing", status="success").inc()
    return AntiPhishingCodeResponse(code=code)


@router.delete(
    "/antiphishing",
    response_model=DeleteAntiPhishingCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete anti-phishing code",
    description="Remove the authenticated user's anti-phishing code.",
    responses={
        401: {"description": "Not authenticated"},
        429: {"description": "Rate limit exceeded (5 requests per hour)"},
    },
)
async def delete_antiphishing_code(
    current_user: AdminUserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> DeleteAntiPhishingCodeResponse:
    """Delete the user's anti-phishing code.

    After deletion, emails will no longer include the anti-phishing code.

    Rate limited to 5 requests per hour per user.
    """
    # Rate limiting: 5 requests per hour per user
    rate_limit_key = f"antiphishing_delete:{current_user.id}"
    rate_limit_window = 3600  # 1 hour in seconds
    rate_limit_max = 5

    # Check current request count
    current_count = await redis_client.get(rate_limit_key)
    if current_count and int(current_count) >= rate_limit_max:
        ttl = await redis_client.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
        )

    user_repo = AdminUserRepository(db)
    use_case = AntiPhishingUseCase(repo=user_repo)

    await use_case.remove_code(user_id=current_user.id)

    # Increment rate limit counter
    pipe = redis_client.pipeline()
    await pipe.incr(rate_limit_key)
    await pipe.expire(rate_limit_key, rate_limit_window)
    await pipe.execute()

    logger.info(
        "Anti-phishing code deleted",
        extra={"user_id": str(current_user.id)},
    )

    route_operations_total.labels(route="security", action="delete_antiphishing", status="success").inc()
    return DeleteAntiPhishingCodeResponse()


@router.post(
    "/risk-subjects",
    response_model=RiskSubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_subject(
    payload: CreateRiskSubjectRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RiskSubjectResponse:
    use_case = CreateRiskSubjectUseCase(db)
    try:
        created = await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "Risk subject created",
        extra={"admin_user_id": str(current_user.id), "risk_subject_id": str(created.id)},
    )
    route_operations_total.labels(route="security", action="create_risk_subject", status="success").inc()
    return created


@router.post(
    "/risk-subjects/{risk_subject_id}/identifiers",
    response_model=AttachRiskIdentifierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_risk_identifier(
    risk_subject_id: UUID,
    payload: AttachRiskIdentifierRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AttachRiskIdentifierResponse:
    use_case = AttachRiskIdentifierUseCase(db)
    try:
        identifier, links_created = await use_case.execute(
            risk_subject_id=risk_subject_id,
            **payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "Risk identifier attached",
        extra={
            "admin_user_id": str(current_user.id),
            "risk_subject_id": str(risk_subject_id),
            "links_created": len(links_created),
        },
    )
    route_operations_total.labels(route="security", action="attach_risk_identifier", status="success").inc()
    return AttachRiskIdentifierResponse(
        identifier=identifier,
        links_created=[RiskLinkResponse.model_validate(link) for link in links_created],
    )


@router.get(
    "/risk-subjects/{risk_subject_id}/links",
    response_model=list[RiskLinkResponse],
)
async def list_risk_links(
    risk_subject_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[RiskLinkResponse]:
    use_case = ListRiskLinksUseCase(db)
    try:
        return await use_case.execute(risk_subject_id=risk_subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/risk-reviews",
    response_model=RiskReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_review(
    payload: CreateRiskReviewRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RiskReviewResponse:
    use_case = CreateRiskReviewUseCase(db)
    try:
        review = await use_case.execute(
            **payload.model_dump(),
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="security", action="create_risk_review", status="success").inc()
    return review


@router.get(
    "/risk-reviews/queue",
    response_model=list[RiskReviewQueueItemResponse],
)
async def list_risk_review_queue(
    status: str | None = None,
    review_type: str | None = None,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[RiskReviewQueueItemResponse]:
    use_case = ListRiskReviewQueueUseCase(db)
    queue = await use_case.execute(status=status, review_type=review_type)
    logger.info(
        "Risk review queue listed",
        extra={
            "admin_user_id": str(current_user.id),
            "queue_size": len(queue),
            "status": status,
            "review_type": review_type,
        },
    )
    route_operations_total.labels(route="security", action="list_risk_review_queue", status="success").inc()
    return [_build_risk_review_queue_item_response(item) for item in queue]


@router.get(
    "/risk-reviews/{risk_review_id}",
    response_model=RiskReviewDetailResponse,
)
async def get_risk_review(
    risk_review_id: UUID,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> RiskReviewDetailResponse:
    use_case = GetRiskReviewUseCase(db)
    try:
        detail = await use_case.execute(risk_review_id=risk_review_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    logger.info(
        "Risk review detail retrieved",
        extra={"admin_user_id": str(current_user.id), "risk_review_id": str(risk_review_id)},
    )
    route_operations_total.labels(route="security", action="get_risk_review", status="success").inc()
    return _build_risk_review_detail_response(detail)


@router.post(
    "/risk-reviews/{risk_review_id}/attachments",
    response_model=RiskReviewAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_risk_review_attachment(
    risk_review_id: UUID,
    payload: AttachRiskReviewAttachmentRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RiskReviewAttachmentResponse:
    use_case = AttachRiskReviewAttachmentUseCase(db)
    try:
        attachment = await use_case.execute(
            risk_review_id=risk_review_id,
            attachment_type=payload.attachment_type,
            storage_key=payload.storage_key,
            file_name=payload.file_name,
            attachment_metadata=payload.metadata,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "Risk review attachment created",
        extra={"admin_user_id": str(current_user.id), "risk_review_id": str(risk_review_id)},
    )
    route_operations_total.labels(route="security", action="attach_risk_review_attachment", status="success").inc()
    return RiskReviewAttachmentResponse.model_validate(attachment)


@router.post(
    "/risk-reviews/{risk_review_id}/resolve",
    response_model=RiskReviewResponse,
)
async def resolve_risk_review(
    risk_review_id: UUID,
    payload: ResolveRiskReviewRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RiskReviewResponse:
    use_case = ResolveRiskReviewUseCase(db)
    try:
        review = await use_case.execute(
            risk_review_id=risk_review_id,
            decision=payload.decision,
            resolution_status=payload.resolution_status,
            resolution_reason=payload.resolution_reason,
            resolution_evidence=payload.resolution_evidence,
            resolved_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "Risk review resolved",
        extra={
            "admin_user_id": str(current_user.id),
            "risk_review_id": str(risk_review_id),
            "decision": payload.decision.value,
        },
    )
    route_operations_total.labels(route="security", action="resolve_risk_review", status="success").inc()
    return review


@router.get(
    "/risk-subjects/{risk_subject_id}/reviews",
    response_model=list[RiskReviewResponse],
)
async def list_risk_reviews(
    risk_subject_id: UUID,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[RiskReviewResponse]:
    use_case = ListRiskReviewsUseCase(db)
    try:
        reviews = await use_case.execute(risk_subject_id=risk_subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    route_operations_total.labels(route="security", action="list_risk_reviews", status="success").inc()
    return reviews


@router.post(
    "/eligibility/checks",
    response_model=EligibilityCheckResponse,
)
async def evaluate_eligibility_check(
    payload: EligibilityCheckRequest,
    _current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> EligibilityCheckResponse:
    use_case = EvaluateEligibilityUseCase(db)
    try:
        result = await use_case.execute(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    route_operations_total.labels(route="security", action="evaluate_eligibility", status="success").inc()
    return EligibilityCheckResponse(
        check_type=result.check_type,
        risk_subject_id=result.risk_subject_id,
        allowed=result.allowed,
        reason_codes=result.reason_codes,
        linked_subject_ids=result.linked_subject_ids,
        checked_at=result.checked_at,
    )


@router.get(
    "/governance-actions",
    response_model=list[GovernanceActionResponse],
)
async def list_governance_actions(
    risk_subject_id: UUID | None = None,
    risk_review_id: UUID | None = None,
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
) -> list[GovernanceActionResponse]:
    use_case = ListGovernanceActionsUseCase(db)
    try:
        actions = await use_case.execute(risk_subject_id=risk_subject_id, risk_review_id=risk_review_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    logger.info(
        "Governance actions listed",
        extra={
            "admin_user_id": str(current_user.id),
            "risk_subject_id": str(risk_subject_id) if risk_subject_id else None,
            "risk_review_id": str(risk_review_id) if risk_review_id else None,
            "action_count": len(actions),
        },
    )
    route_operations_total.labels(route="security", action="list_governance_actions", status="success").inc()
    return [GovernanceActionResponse.model_validate(item) for item in actions]


@router.post(
    "/governance-actions",
    response_model=GovernanceActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_governance_action(
    payload: CreateGovernanceActionRequest,
    current_user: AdminUserModel = Depends(require_role(AdminRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> GovernanceActionResponse:
    use_case = CreateGovernanceActionUseCase(db)
    try:
        action = await use_case.execute(
            risk_subject_id=payload.risk_subject_id,
            risk_review_id=payload.risk_review_id,
            action_type=payload.action_type,
            reason=payload.reason,
            target_type=payload.target_type,
            target_ref=payload.target_ref,
            action_payload=payload.payload,
            apply_now=payload.apply_now,
            created_by_admin_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info(
        "Governance action created",
        extra={"admin_user_id": str(current_user.id), "governance_action_id": str(action.id)},
    )
    route_operations_total.labels(route="security", action="create_governance_action", status="success").inc()
    return GovernanceActionResponse.model_validate(action)
