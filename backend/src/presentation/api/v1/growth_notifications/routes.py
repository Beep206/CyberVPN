"""Customer growth notification feed routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.gifts import ListGiftCodesUseCase
from src.application.use_cases.growth_notifications.automation import (
    AutomateCustomerGrowthNotificationRepairUseCase,
)
from src.application.use_cases.growth_notifications.catalog import (
    admin_manual_notification_key,
    category_for_growth_notification_kind,
    gift_expired_notification_key,
    gift_expiring_notification_key,
    gift_issued_notification_key,
    gift_redeemed_notification_key,
    invite_expired_notification_key,
    invite_expiring_notification_key,
    invite_issued_notification_key,
    invite_redeemed_notification_key,
    normalize_growth_notification_key,
    referral_available_notification_key,
    referral_pending_notification_key,
    referral_reversed_notification_key,
)
from src.application.use_cases.growth_notifications.customer_surface import (
    EscalateCustomerGrowthNotificationSupportUseCase,
    GetCustomerGrowthNotificationSurfaceDetailUseCase,
    RequestCustomerGrowthNotificationRecoveryUseCase,
)
from src.application.use_cases.growth_notifications.preferences import (
    build_customer_growth_notification_preferences,
    growth_notification_pref_enabled,
)
from src.infrastructure.database.repositories.customer_growth_notification_delivery_repository import (
    CustomerGrowthNotificationDeliveryRepository,
)
from src.infrastructure.database.repositories.customer_growth_notification_read_state_repository import (
    CustomerGrowthNotificationReadStateRepository,
)
from src.infrastructure.database.repositories.growth_reward_allocation_repo import (
    GrowthRewardAllocationRepository,
)
from src.infrastructure.database.repositories.invite_code_repo import InviteCodeRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.presentation.dependencies.auth import get_current_mobile_user_id
from src.presentation.dependencies.database import get_db

from .schemas import (
    GrowthNotificationCountersResponse,
    GrowthNotificationDeliveryDetailResponse,
    GrowthNotificationDetailResponse,
    GrowthNotificationFeedItemResponse,
    GrowthNotificationPreferencesResponse,
    GrowthNotificationPreferencesUpdateRequest,
    GrowthNotificationReadStateResponse,
    GrowthNotificationRecoveryRequest,
    GrowthNotificationRepairTargetResponse,
    GrowthNotificationSupportEscalationRequest,
    GrowthNotificationSupportHandoffResponse,
)

router = APIRouter(prefix="/growth-notifications", tags=["growth_notifications"])


def _normalize_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _notification_state_by_key(read_states: list[object]) -> dict[str, object]:
    return {
        normalize_growth_notification_key(getattr(item, "notification_key", "")): item
        for item in read_states
        if getattr(item, "notification_key", None)
    }


def _append_growth_notification(
    *,
    items: list[GrowthNotificationFeedItemResponse],
    read_state_by_key: dict[str, object],
    notification_key: str,
    kind: str,
    tone: str,
    title: str,
    message: str,
    created_at: datetime | None,
    route_slug: str = "/referral",
    notes: list[str] | None = None,
    action_required: bool = False,
    unread_by_default: bool = True,
    include_archived: bool = False,
    source_kind: str | None = None,
    source_id: str | None = None,
    prefs: dict[str, bool] | None = None,
) -> None:
    if prefs is not None and not growth_notification_pref_enabled(
        prefs,
        category=category_for_growth_notification_kind(kind),
        channel="in_app",
    ):
        return

    normalized_key = normalize_growth_notification_key(notification_key)
    state = read_state_by_key.get(normalized_key)
    archived_at = getattr(state, "archived_at", None)
    if archived_at is not None and not include_archived:
        return

    read_at = getattr(state, "read_at", None)
    unread = unread_by_default and read_at is None and archived_at is None
    items.append(
        GrowthNotificationFeedItemResponse(
            id=normalized_key,
            kind=kind,
            tone=tone,
            route_slug=route_slug,
            title=title.strip(),
            message=message.strip(),
            notes=list(notes or []),
            action_required=action_required,
            unread=unread,
            created_at=_normalize_utc(created_at),
            archived_at=_normalize_utc(archived_at) if archived_at is not None else None,
            source_kind=source_kind,
            source_id=source_id,
        )
    )


def _format_usd(amount: Decimal | float | int) -> str:
    normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    return f"${normalized}"


async def _build_growth_notification_feed(
    *,
    mobile_user_id: UUID,
    db: AsyncSession,
    include_archived: bool = False,
) -> list[GrowthNotificationFeedItemResponse]:
    mobile_user = await MobileUserRepository(db).get_by_id(mobile_user_id)
    if mobile_user is None:
        return []
    prefs = build_customer_growth_notification_preferences(mobile_user.notification_prefs)
    read_state_by_key = _notification_state_by_key(
        await CustomerGrowthNotificationReadStateRepository(db).list_for_user(mobile_user_id=mobile_user_id)
    )
    items: list[GrowthNotificationFeedItemResponse] = []
    now = datetime.now(UTC)

    invites = await InviteCodeRepository(db).get_by_owner(owner_user_id=mobile_user_id, offset=0, limit=100)
    for invite in invites:
        expires_at = _normalize_utc(invite.expires_at) if invite.expires_at is not None else None
        source_label = str(invite.source).replace("_", " ")
        _append_growth_notification(
            items=items,
            read_state_by_key=read_state_by_key,
            notification_key=invite_issued_notification_key(invite.id),
            kind="invite_issued",
            tone="info",
            title="Invite ready to share",
            message=f"Your account received an invite code for {invite.free_days} free days.",
            notes=[
                *[f"Source: {source_label}."],
                *([f"Expires {expires_at.date().isoformat()}."] if expires_at else []),
            ],
            action_required=not invite.is_used,
            created_at=invite.created_at,
            include_archived=include_archived,
            source_kind="invite_code",
            source_id=str(invite.id),
            prefs=prefs,
        )

        if invite.is_used and invite.used_at is not None:
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=invite_redeemed_notification_key(invite.id),
                kind="invite_redeemed",
                tone="success",
                title="Invite redeemed",
                message=f"One of your invite codes was redeemed for {invite.free_days} free days of access.",
                notes=[],
                action_required=False,
                created_at=invite.used_at,
                include_archived=include_archived,
                source_kind="invite_code",
                source_id=str(invite.id),
                prefs=prefs,
            )
        elif expires_at is not None and expires_at <= now:
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=invite_expired_notification_key(invite.id),
                kind="invite_expired",
                tone="warning",
                title="Invite expired",
                message=f"An unused invite code for {invite.free_days} free days expired.",
                notes=[],
                action_required=False,
                created_at=invite.expires_at,
                include_archived=include_archived,
                source_kind="invite_code",
                source_id=str(invite.id),
                prefs=prefs,
            )
        elif expires_at is not None and expires_at <= now + timedelta(days=3):
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=invite_expiring_notification_key(invite.id),
                kind="invite_expiring_soon",
                tone="warning",
                title="Invite expiring soon",
                message=f"An unused invite code for {invite.free_days} free days expires soon.",
                notes=[f"Expires {expires_at.date().isoformat()}."],
                action_required=True,
                created_at=invite.expires_at,
                include_archived=include_archived,
                source_kind="invite_code",
                source_id=str(invite.id),
                prefs=prefs,
            )

    rewards = await GrowthRewardAllocationRepository(db).list(
        beneficiary_user_id=mobile_user_id,
        reward_type="referral_credit",
        limit=100,
    )
    for reward in rewards:
        reward_amount = _format_usd(reward.quantity)
        base_notes = []
        if reward.hold_until is not None:
            base_notes.append(f"Hold until {_normalize_utc(reward.hold_until).date().isoformat()}.")
        if reward.reversal_reason:
            base_notes.append(f"Reason: {reward.reversal_reason}.")
        if reward.allocation_status == "pending":
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=referral_pending_notification_key(reward.id),
                kind="referral_reward_pending",
                tone="info",
                title="Referral reward pending",
                message=f"A referral reward of {reward_amount} is pending review.",
                notes=base_notes,
                action_required=False,
                created_at=reward.allocated_at,
                include_archived=include_archived,
                source_kind="growth_reward",
                source_id=str(reward.id),
                prefs=prefs,
            )
        elif reward.allocation_status == "available":
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=referral_available_notification_key(reward.id),
                kind="referral_reward_available",
                tone="success",
                title="Referral reward available",
                message=f"A referral reward of {reward_amount} is now available on your account.",
                notes=base_notes,
                action_required=False,
                created_at=reward.available_at or reward.updated_at,
                include_archived=include_archived,
                source_kind="growth_reward",
                source_id=str(reward.id),
                prefs=prefs,
            )
        elif reward.allocation_status == "reversed":
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=referral_reversed_notification_key(reward.id),
                kind="referral_reward_reversed",
                tone="critical",
                title="Referral reward reversed",
                message=f"A referral reward of {reward_amount} was reversed.",
                notes=base_notes,
                action_required=False,
                created_at=reward.reversed_at or reward.updated_at,
                include_archived=include_archived,
                source_kind="growth_reward",
                source_id=str(reward.id),
                prefs=prefs,
            )

    gifts = await ListGiftCodesUseCase(db).execute(owner_user_id=mobile_user_id, limit=100)
    for code, policy, issuance, redemption in gifts:
        plan_label = policy.plan_family if policy is not None and policy.plan_family else "gift plan"
        duration_days = policy.duration_days if policy is not None and policy.duration_days is not None else 0
        expires_at = _normalize_utc(code.expires_at) if code.expires_at is not None else None
        issuance_type = issuance.issuance_type if issuance is not None else None
        if issuance_type == "gift_purchase":
            title = "Gift purchase completed"
            message = f"Your {plan_label} gift for {duration_days} days is ready to share."
            tone = "info"
            action_required = redemption is None
            kind = "gift_purchased"
        else:
            title = "Gift code available"
            message = f"A {plan_label} gift for {duration_days} days was issued to your account."
            tone = "success"
            action_required = redemption is None
            kind = "gift_available"

        recipient_hint = None
        if policy is not None and isinstance(policy.policy_snapshot, dict):
            recipient_hint = policy.policy_snapshot.get("recipient_hint")

        _append_growth_notification(
            items=items,
            read_state_by_key=read_state_by_key,
            notification_key=gift_issued_notification_key(code.id),
            kind=kind,
            tone=tone,
            title=title,
            message=message,
            notes=[
                *([f"Recipient: {recipient_hint}."] if recipient_hint else []),
                *([f"Expires {expires_at.date().isoformat()}."] if expires_at else []),
            ],
            action_required=action_required,
            created_at=code.created_at,
            include_archived=include_archived,
            source_kind="gift_code",
            source_id=str(code.id),
            prefs=prefs,
        )

        if redemption is not None:
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=gift_redeemed_notification_key(code.id),
                kind="gift_redeemed",
                tone="success",
                title="Gift redeemed",
                message=f"Your {plan_label} gift for {duration_days} days was redeemed.",
                notes=[],
                action_required=False,
                created_at=redemption.redeemed_at,
                include_archived=include_archived,
                source_kind="gift_code",
                source_id=str(code.id),
                prefs=prefs,
            )
        elif expires_at is not None and expires_at <= now:
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=gift_expired_notification_key(code.id),
                kind="gift_expired",
                tone="warning",
                title="Gift expired",
                message=f"An unused {plan_label} gift for {duration_days} days expired.",
                notes=[],
                action_required=False,
                created_at=code.expires_at,
                include_archived=include_archived,
                source_kind="gift_code",
                source_id=str(code.id),
                prefs=prefs,
            )
        elif expires_at is not None and expires_at <= now + timedelta(days=7):
            _append_growth_notification(
                items=items,
                read_state_by_key=read_state_by_key,
                notification_key=gift_expiring_notification_key(code.id),
                kind="gift_expiring_soon",
                tone="warning",
                title="Gift expiring soon",
                message=f"Your unused {plan_label} gift for {duration_days} days expires soon.",
                notes=[f"Expires {expires_at.date().isoformat()}."],
                action_required=True,
                created_at=code.expires_at,
                include_archived=include_archived,
                source_kind="gift_code",
                source_id=str(code.id),
                prefs=prefs,
            )

    admin_manual_deliveries = await CustomerGrowthNotificationDeliveryRepository(db).list_deliveries(
        mobile_user_id=mobile_user_id,
        delivery_channel="in_app",
        limit=100,
        offset=0,
    )
    for delivery in admin_manual_deliveries:
        if delivery.delivery_status != "delivered" or delivery.notification_kind != "admin_manual_update":
            continue
        route_slug = str((delivery.delivery_payload or {}).get("route_slug") or "/referral")
        notes = [str(item) for item in list((delivery.delivery_payload or {}).get("notes") or []) if str(item).strip()]
        _append_growth_notification(
            items=items,
            read_state_by_key=read_state_by_key,
            notification_key=delivery.notification_key or admin_manual_notification_key(delivery.id),
            kind="admin_manual_update",
            tone="info",
            title=delivery.title,
            message=delivery.message,
            notes=notes,
            action_required=False,
            created_at=delivery.delivered_at or delivery.created_at,
            route_slug=route_slug,
            include_archived=include_archived,
            source_kind=delivery.source_kind,
            source_id=delivery.source_id,
            prefs=prefs,
        )

    items.sort(key=lambda item: (item.created_at, item.id), reverse=True)
    return items


async def _get_growth_notification_item(
    *,
    mobile_user_id: UUID,
    db: AsyncSession,
    notification_id: str,
) -> GrowthNotificationFeedItemResponse:
    normalized_id = normalize_growth_notification_key(notification_id)
    items = await _build_growth_notification_feed(
        mobile_user_id=mobile_user_id,
        db=db,
        include_archived=True,
    )
    for item in items:
        if item.id == normalized_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Growth notification not found")


async def _build_growth_notification_detail_response(
    *,
    mobile_user_id: UUID,
    db: AsyncSession,
    notification_id: str,
) -> GrowthNotificationDetailResponse:
    item = await _get_growth_notification_item(
        mobile_user_id=mobile_user_id,
        db=db,
        notification_id=notification_id,
    )
    detail = await GetCustomerGrowthNotificationSurfaceDetailUseCase(db).execute(
        mobile_user_id=mobile_user_id,
        notification_key=item.id,
        title=item.title,
        route_slug=item.route_slug,
    )
    return GrowthNotificationDetailResponse(
        notification=item,
        deliveries=[
            GrowthNotificationDeliveryDetailResponse(
                delivery_id=str(delivery_view.delivery.id),
                delivery_channel=delivery_view.delivery.delivery_channel,
                delivery_status=delivery_view.delivery.delivery_status,
                troubleshooting_state=delivery_view.troubleshooting_state,
                customer_message_key=delivery_view.customer_message_key,
                customer_summary=delivery_view.customer_summary,
                recovery_allowed=delivery_view.recovery_allowed,
                support_required=delivery_view.support_required,
                repair_target=(
                    GrowthNotificationRepairTargetResponse(
                        kind=delivery_view.repair_target.kind,
                        summary=delivery_view.repair_target.summary,
                    )
                    if delivery_view.repair_target is not None
                    else None
                ),
                planned_at=delivery_view.delivery.planned_at,
                delivered_at=delivery_view.delivery.delivered_at,
                events=[
                    {
                        "event_type": event.event_type,
                        "occurred_at": event.occurred_at,
                        "summary": event.summary,
                    }
                    for event in delivery_view.events
                ],
            )
            for delivery_view in detail.deliveries
        ],
        support_handoff=GrowthNotificationSupportHandoffResponse(
            reference_code=detail.support_handoff.reference_code,
            troubleshooting_summary=detail.support_handoff.troubleshooting_summary,
            copy_text=detail.support_handoff.copy_text,
            suggested_escalation_channel=detail.support_handoff.suggested_escalation_channel,
            contact_subject=detail.support_handoff.contact_subject,
            contact_body=detail.support_handoff.contact_body,
        ),
    )


@router.get(
    "",
    response_model=list[GrowthNotificationFeedItemResponse],
    summary="List growth notifications for the current customer",
)
async def list_growth_notifications(
    include_archived: bool = Query(False, description="Include archived notification records"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> list[GrowthNotificationFeedItemResponse]:
    return await _build_growth_notification_feed(
        mobile_user_id=user_id,
        db=db,
        include_archived=include_archived,
    )


@router.get(
    "/counters",
    response_model=GrowthNotificationCountersResponse,
    summary="Get growth notification counters for the current customer",
)
async def get_growth_notification_counters(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationCountersResponse:
    items = await _build_growth_notification_feed(mobile_user_id=user_id, db=db, include_archived=False)
    return GrowthNotificationCountersResponse(
        total_notifications=len(items),
        unread_notifications=sum(1 for item in items if item.unread),
        action_required_notifications=sum(1 for item in items if item.action_required),
    )


def _serialize_growth_notification_preferences(raw_prefs: dict | None) -> GrowthNotificationPreferencesResponse:
    prefs = build_customer_growth_notification_preferences(raw_prefs)
    return GrowthNotificationPreferencesResponse(**prefs)


@router.get(
    "/preferences",
    response_model=GrowthNotificationPreferencesResponse,
    summary="Get growth notification preferences for the current customer",
)
async def get_growth_notification_preferences(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationPreferencesResponse:
    user = await MobileUserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer account not found")
    return _serialize_growth_notification_preferences(user.notification_prefs)


@router.patch(
    "/preferences",
    response_model=GrowthNotificationPreferencesResponse,
    summary="Update growth notification preferences for the current customer",
)
async def update_growth_notification_preferences(
    body: GrowthNotificationPreferencesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationPreferencesResponse:
    user_repo = MobileUserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer account not found")

    previous_prefs = build_customer_growth_notification_preferences(user.notification_prefs)
    prefs = dict(previous_prefs)
    prefs.update({key: value for key, value in body.model_dump(exclude_unset=True).items() if value is not None})
    user.notification_prefs = prefs
    updated_user = await user_repo.update(user)
    if any(previous_prefs.get(key) is False and prefs.get(key) is True for key in prefs):
        await AutomateCustomerGrowthNotificationRepairUseCase(db).execute(
            mobile_user_id=user_id,
            repair_trigger="preferences_reenabled",
        )
    await db.commit()
    await db.refresh(updated_user)
    return _serialize_growth_notification_preferences(updated_user.notification_prefs)


@router.post(
    "/{notification_id}/read",
    response_model=GrowthNotificationReadStateResponse,
    summary="Mark a growth notification as read",
)
async def mark_growth_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationReadStateResponse:
    items = await _build_growth_notification_feed(mobile_user_id=user_id, db=db, include_archived=True)
    if not any(item.id == normalize_growth_notification_key(notification_id) for item in items):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Growth notification not found")

    state = await CustomerGrowthNotificationReadStateRepository(db).upsert_read_state(
        mobile_user_id=user_id,
        notification_key=normalize_growth_notification_key(notification_id),
        read_at=datetime.now(UTC),
    )
    await db.commit()
    return GrowthNotificationReadStateResponse(
        notification_id=normalize_growth_notification_key(notification_id),
        read_at=state.read_at,
        archived_at=state.archived_at,
    )


@router.post(
    "/{notification_id}/archive",
    response_model=GrowthNotificationReadStateResponse,
    summary="Archive a growth notification",
)
async def archive_growth_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationReadStateResponse:
    items = await _build_growth_notification_feed(mobile_user_id=user_id, db=db, include_archived=True)
    if not any(item.id == normalize_growth_notification_key(notification_id) for item in items):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Growth notification not found")

    state = await CustomerGrowthNotificationReadStateRepository(db).upsert_read_state(
        mobile_user_id=user_id,
        notification_key=normalize_growth_notification_key(notification_id),
        read_at=datetime.now(UTC),
        archived_at=datetime.now(UTC),
    )
    await db.commit()
    return GrowthNotificationReadStateResponse(
        notification_id=normalize_growth_notification_key(notification_id),
        read_at=state.read_at,
        archived_at=state.archived_at,
    )


@router.get(
    "/{notification_id}",
    response_model=GrowthNotificationDetailResponse,
    summary="Get customer troubleshooting detail for a growth notification",
)
async def get_growth_notification_detail(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationDetailResponse:
    return await _build_growth_notification_detail_response(
        mobile_user_id=user_id,
        db=db,
        notification_id=notification_id,
    )


@router.post(
    "/{notification_id}/recovery",
    response_model=GrowthNotificationDetailResponse,
    summary="Request a supported recovery action for a growth notification delivery",
)
async def request_growth_notification_recovery(
    notification_id: str,
    body: GrowthNotificationRecoveryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationDetailResponse:
    await _get_growth_notification_item(
        mobile_user_id=user_id,
        db=db,
        notification_id=notification_id,
    )
    try:
        await RequestCustomerGrowthNotificationRecoveryUseCase(db).execute(
            mobile_user_id=user_id,
            notification_key=notification_id,
            delivery_channel=body.delivery_channel,
        )
    except ValueError as exc:
        message = str(exc)
        if message in {"delivery_not_found", "customer_not_found"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        if message == "already_in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This delivery is already in progress.",
            ) from exc
        if message == "already_delivered":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This delivery is already completed.",
            ) from exc
        if message == "preference_disabled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Enable this delivery channel in preferences before requesting another send.",
            ) from exc
        if message == "telegram_unlinked":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Link Telegram to your account before requesting another Telegram send.",
            ) from exc
        if message == "email_unavailable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email delivery is not available for this account.",
            ) from exc
        if message in {"revoked_by_admin", "paused_by_admin"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This delivery is under support review and cannot be retried from the customer surface.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This delivery cannot be retried from the customer surface.",
        ) from exc

    await db.commit()
    return await _build_growth_notification_detail_response(
        mobile_user_id=user_id,
        db=db,
        notification_id=notification_id,
    )


@router.post(
    "/{notification_id}/support-escalation",
    response_model=GrowthNotificationDetailResponse,
    summary="Log a guided support escalation for a growth notification delivery",
)
async def request_growth_notification_support_escalation(
    notification_id: str,
    body: GrowthNotificationSupportEscalationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_mobile_user_id),
) -> GrowthNotificationDetailResponse:
    await _get_growth_notification_item(
        mobile_user_id=user_id,
        db=db,
        notification_id=notification_id,
    )
    try:
        await EscalateCustomerGrowthNotificationSupportUseCase(db).execute(
            mobile_user_id=user_id,
            notification_key=notification_id,
            delivery_channel=body.delivery_channel,
            escalation_channel=body.escalation_channel,
        )
    except ValueError as exc:
        message = str(exc)
        if message in {"delivery_not_found", "customer_not_found"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Growth notification delivery not found",
            ) from exc
        if message == "support_escalation_not_required":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This notification does not currently require support escalation.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This notification cannot be escalated from the customer surface.",
        ) from exc

    await db.commit()
    return await _build_growth_notification_detail_response(
        mobile_user_id=user_id,
        db=db,
        notification_id=notification_id,
    )
