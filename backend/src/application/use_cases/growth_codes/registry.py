from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.events import EventOutboxService, OutboxActorContext
from src.application.use_cases.growth_codes.hashing import build_growth_code_prefix, hash_growth_code
from src.domain.enums import GrowthCodeType, InviteSource
from src.infrastructure.database.models.growth_code_model import (
    GrowthCodeIssuanceModel,
    GrowthCodeModel,
    GrowthCodeResolutionEventModel,
    InviteCodePolicyModel,
    PromoCodePolicyModel,
    ReferralProgramPolicyModel,
)
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.growth_code_repo import GrowthCodeRepository
from src.infrastructure.monitoring.instrumentation.growth_codes import (
    ADMIN_GROWTH_SURFACE,
    CUSTOMER_COMMERCE_SURFACE,
    log_growth_code_event,
    observe_growth_code_issue,
    observe_growth_code_resolution,
)


class GrowthCodeRegistryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._codes = GrowthCodeRepository(session)
        self._outbox = EventOutboxService(session)

    async def ensure_shadow_invite(self, invite) -> GrowthCodeModel:
        owner = await self._session.get(MobileUserModel, invite.owner_user_id)
        now = datetime.now(UTC)
        code = await self._codes.get_code_by_hash(hash_growth_code(invite.code), code_type=GrowthCodeType.INVITE.value)
        if code is None:
            code = await self._codes.create_code(
                GrowthCodeModel(
                    code_hash=hash_growth_code(invite.code),
                    code_prefix=build_growth_code_prefix(invite.code),
                    code_type=GrowthCodeType.INVITE.value,
                    status=_invite_status(invite=invite, now=now),
                    issuer_type="purchase" if invite.source == InviteSource.PURCHASE.value else "admin",
                    owner_user_id=invite.owner_user_id,
                    auth_realm_id=owner.auth_realm_id if owner is not None else None,
                    starts_at=_coerce_utc(invite.created_at),
                    expires_at=_coerce_utc(invite.expires_at),
                    max_uses=1,
                    uses_count=1 if invite.is_used else 0,
                )
            )
        else:
            code.status = _invite_status(invite=invite, now=now)
            code.issuer_type = "purchase" if invite.source == InviteSource.PURCHASE.value else "admin"
            code.owner_user_id = invite.owner_user_id
            code.auth_realm_id = owner.auth_realm_id if owner is not None else None
            code.starts_at = _coerce_utc(invite.created_at)
            code.expires_at = _coerce_utc(invite.expires_at)
            code.max_uses = 1
            code.uses_count = 1 if invite.is_used else 0
            await self._session.flush()

        invite_policy = await self._codes.get_invite_policy(code.id)
        if invite_policy is None:
            await self._codes.create_invite_policy(
                InviteCodePolicyModel(
                    growth_code_id=code.id,
                    friend_days=invite.free_days,
                    entitlement_profile_key="invite_limited_access_v1",
                    self_redemption_block=True,
                    policy_snapshot={
                        "legacy_plan_id": str(invite.plan_id) if invite.plan_id else None,
                        "source": invite.source,
                    },
                )
            )
        else:
            invite_policy.friend_days = invite.free_days
            invite_policy.policy_snapshot = {
                "legacy_plan_id": str(invite.plan_id) if invite.plan_id else None,
                "source": invite.source,
            }
            await self._session.flush()

        issuances = await self._codes.list_issuances(code.id)
        if not issuances:
            await self._codes.create_issuance(
                GrowthCodeIssuanceModel(
                    growth_code_id=code.id,
                    issuance_type=(
                        "plan_invite_bundle" if invite.source == InviteSource.PURCHASE.value else "admin_manual_grant"
                    ),
                    issued_to_user_id=invite.owner_user_id,
                    source_payment_id=invite.source_payment_id,
                    source_bundle_snapshot={
                        "friend_days": invite.free_days,
                        "legacy_plan_id": str(invite.plan_id) if invite.plan_id else None,
                    },
                    reason_code=invite.source,
                )
            )
            await self._outbox.append_event(
                event_name=(
                    "invite.generated_from_order"
                    if invite.source == InviteSource.PURCHASE.value
                    else "growth_code.issued"
                ),
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(code.owner_user_id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "code_type": code.code_type,
                    "source_type": invite.source,
                    "owner_user_id": str(code.owner_user_id) if code.owner_user_id else None,
                    "friend_days": invite.free_days,
                },
                actor_context=OutboxActorContext(
                    principal_type="customer" if code.owner_user_id else "system",
                    principal_id=str(code.owner_user_id) if code.owner_user_id else None,
                    auth_realm_id=str(code.auth_realm_id) if code.auth_realm_id else None,
                ),
                source_context={"source_use_case": "GrowthCodeRegistryService.ensure_shadow_invite"},
            )
            observe_growth_code_issue(
                code_type=code.code_type,
                issuer_type=code.issuer_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                result="success",
                source_type=invite.source,
            )
            log_growth_code_event(
                "growth_code.issued",
                surface=CUSTOMER_COMMERCE_SURFACE,
                code_type=code.code_type,
                result="success",
                source_type=invite.source,
                growth_code_id=str(code.id),
                owner_user_id=str(code.owner_user_id) if code.owner_user_id else None,
            )

        return code

    async def ensure_shadow_promo(self, promo) -> GrowthCodeModel:
        now = datetime.now(UTC)
        code = await self._codes.get_code_by_hash(hash_growth_code(promo.code), code_type=GrowthCodeType.PROMO.value)
        if code is None:
            code = await self._codes.create_code(
                GrowthCodeModel(
                    code_hash=hash_growth_code(promo.code),
                    code_prefix=build_growth_code_prefix(promo.code),
                    code_type=GrowthCodeType.PROMO.value,
                    status=_promo_status(promo=promo, now=now),
                    issuer_type="admin",
                    issuer_admin_id=promo.created_by,
                    starts_at=_coerce_utc(promo.created_at),
                    expires_at=_coerce_utc(promo.expires_at),
                    max_uses=promo.max_uses,
                    uses_count=promo.current_uses,
                )
            )
        else:
            code.status = _promo_status(promo=promo, now=now)
            code.issuer_type = "admin"
            code.issuer_admin_id = promo.created_by
            code.starts_at = _coerce_utc(promo.created_at)
            code.expires_at = _coerce_utc(promo.expires_at)
            code.max_uses = promo.max_uses
            code.uses_count = promo.current_uses
            await self._session.flush()

        promo_policy = await self._codes.get_promo_policy(code.id)
        policy_snapshot = {
            "currency": promo.currency,
            "legacy_description": promo.description,
            "is_single_use": promo.is_single_use,
        }
        eligible_plan_ids = [str(plan_id) for plan_id in (promo.plan_ids or [])]
        if promo_policy is None:
            await self._codes.create_promo_policy(
                PromoCodePolicyModel(
                    growth_code_id=code.id,
                    discount_type=promo.discount_type,
                    discount_value=promo.discount_value,
                    eligible_plan_ids=eligible_plan_ids,
                    min_net_paid_amount=promo.min_amount,
                    global_usage_cap=promo.max_uses,
                    usage_cap_per_user=1 if promo.is_single_use else None,
                    policy_snapshot=policy_snapshot,
                )
            )
        else:
            promo_policy.discount_type = promo.discount_type
            promo_policy.discount_value = promo.discount_value
            promo_policy.eligible_plan_ids = eligible_plan_ids
            promo_policy.min_net_paid_amount = promo.min_amount
            promo_policy.global_usage_cap = promo.max_uses
            promo_policy.usage_cap_per_user = 1 if promo.is_single_use else None
            promo_policy.policy_snapshot = policy_snapshot
            await self._session.flush()

        issuances = await self._codes.list_issuances(code.id)
        if not issuances:
            await self._codes.create_issuance(
                GrowthCodeIssuanceModel(
                    growth_code_id=code.id,
                    issuance_type="marketing_campaign",
                    issued_by_admin_id=promo.created_by,
                    reason_code="promo_campaign",
                    admin_note=promo.description,
                )
            )
            await self._outbox.append_event(
                event_name="growth_code.issued",
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(code.id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "code_type": code.code_type,
                    "issuer_type": code.issuer_type,
                    "issuer_admin_id": str(code.issuer_admin_id) if code.issuer_admin_id else None,
                },
                actor_context=OutboxActorContext(
                    principal_type="admin" if code.issuer_admin_id else "system",
                    principal_id=str(code.issuer_admin_id) if code.issuer_admin_id else None,
                ),
                source_context={"source_use_case": "GrowthCodeRegistryService.ensure_shadow_promo"},
            )
            observe_growth_code_issue(
                code_type=code.code_type,
                issuer_type=code.issuer_type,
                surface=ADMIN_GROWTH_SURFACE,
                result="success",
                source_type="marketing_campaign",
            )
            log_growth_code_event(
                "growth_code.issued",
                surface=ADMIN_GROWTH_SURFACE,
                code_type=code.code_type,
                result="success",
                admin_action_type="promo_shadow_sync",
                growth_code_id=str(code.id),
            )

        return code

    async def ensure_shadow_referral(self, referral_owner: MobileUserModel) -> GrowthCodeModel:
        if not referral_owner.referral_code:
            raise ValueError("Referral owner does not have a referral code")

        code = await self._codes.get_code_by_hash(
            hash_growth_code(referral_owner.referral_code),
            code_type=GrowthCodeType.REFERRAL.value,
        )
        if code is None:
            code = await self._codes.create_code(
                GrowthCodeModel(
                    code_hash=hash_growth_code(referral_owner.referral_code),
                    code_prefix=build_growth_code_prefix(referral_owner.referral_code),
                    code_type=GrowthCodeType.REFERRAL.value,
                    status="active" if referral_owner.is_active else "inactive",
                    issuer_type="user",
                    owner_user_id=referral_owner.id,
                    auth_realm_id=referral_owner.auth_realm_id,
                    starts_at=_coerce_utc(referral_owner.created_at),
                )
            )
        else:
            code.status = "active" if referral_owner.is_active else "inactive"
            code.issuer_type = "user"
            code.owner_user_id = referral_owner.id
            code.auth_realm_id = referral_owner.auth_realm_id
            code.starts_at = _coerce_utc(referral_owner.created_at)
            await self._session.flush()

        referral_policy = await self._codes.get_referral_policy(code.id)
        policy_snapshot = {
            "friend_discount_schedule": {"type": "percent", "value": 10},
            "duration_reward_schedule": {"90": 4, "180": 6, "365": 10},
            "plan_families": ["basic", "plus", "pro", "max"],
            "hold_days": 14,
            "monthly_cap_usd": 300,
            "lifetime_cap_usd": 1000,
        }
        if referral_policy is None:
            await self._codes.create_referral_policy(
                ReferralProgramPolicyModel(
                    growth_code_id=code.id,
                    program_key=f"customer_referral_default_v1:{referral_owner.id}",
                    friend_discount_type="percent",
                    friend_discount_value=10,
                    eligible_durations=[90, 180, 365],
                    eligible_plan_families=["basic", "plus", "pro", "max"],
                    reward_type="nonwithdrawable_credit",
                    hold_days=14,
                    monthly_cap=300,
                    lifetime_cap=1000,
                    policy_snapshot=policy_snapshot,
                )
            )
        else:
            referral_policy.friend_discount_type = "percent"
            referral_policy.friend_discount_value = 10
            referral_policy.eligible_durations = [90, 180, 365]
            referral_policy.eligible_plan_families = ["basic", "plus", "pro", "max"]
            referral_policy.reward_type = "nonwithdrawable_credit"
            referral_policy.hold_days = 14
            referral_policy.monthly_cap = 300
            referral_policy.lifetime_cap = 1000
            referral_policy.policy_snapshot = policy_snapshot
            await self._session.flush()

        issuances = await self._codes.list_issuances(code.id)
        if not issuances:
            await self._codes.create_issuance(
                GrowthCodeIssuanceModel(
                    growth_code_id=code.id,
                    issuance_type="user_owned_referral",
                    issued_to_user_id=referral_owner.id,
                    reason_code="customer_referral_program",
                )
            )
            await self._outbox.append_event(
                event_name="growth_code.issued",
                aggregate_type="growth_code",
                aggregate_id=str(code.id),
                partition_key=str(referral_owner.id),
                event_payload={
                    "growth_code_id": str(code.id),
                    "code_type": code.code_type,
                    "owner_user_id": str(referral_owner.id),
                    "issuer_type": code.issuer_type,
                },
                actor_context=OutboxActorContext(
                    principal_type="customer",
                    principal_id=str(referral_owner.id),
                    auth_realm_id=str(code.auth_realm_id) if code.auth_realm_id else None,
                ),
                source_context={"source_use_case": "GrowthCodeRegistryService.ensure_shadow_referral"},
            )
            observe_growth_code_issue(
                code_type=code.code_type,
                issuer_type=code.issuer_type,
                surface=CUSTOMER_COMMERCE_SURFACE,
                result="success",
                source_type="customer_referral_program",
            )
            log_growth_code_event(
                "growth_code.issued",
                surface=CUSTOMER_COMMERCE_SURFACE,
                code_type=code.code_type,
                result="success",
                growth_code_id=str(code.id),
                owner_user_id=str(referral_owner.id),
            )

        return code

    async def record_resolution_event(
        self,
        *,
        growth_code_id,
        raw_code: str,
        code_type: str | None,
        user_id,
        surface: str,
        action_context: str,
        result: str,
        reject_reason: str | None,
        conflict_code: str | None,
        policy_version_id,
    ):
        raw_code_hash = hash_growth_code(raw_code)
        model = await self._codes.create_resolution_event(
            GrowthCodeResolutionEventModel(
                growth_code_id=growth_code_id,
                raw_code_hash=raw_code_hash,
                code_type=code_type,
                user_id=user_id,
                surface=surface,
                action_context=action_context,
                result=result,
                reject_reason=reject_reason,
                conflict_code=conflict_code,
                policy_version_id=policy_version_id,
            )
        )
        observe_growth_code_resolution(
            code_type=code_type,
            action_context=action_context,
            surface=surface,
            result=result,
            reject_reason=reject_reason,
        )
        event_name = "growth_code.resolved" if result == "accepted" else "growth_code.rejected"
        await self._outbox.append_event(
            event_name=event_name,
            aggregate_type="growth_code_resolution",
            aggregate_id=str(growth_code_id or raw_code_hash),
            partition_key=str(growth_code_id or raw_code_hash),
            event_payload={
                "growth_code_id": str(growth_code_id) if growth_code_id else None,
                "raw_code_hash": raw_code_hash,
                "code_type": code_type,
                "user_id": str(user_id) if user_id else None,
                "surface": surface,
                "action_context": action_context,
                "result": result,
                "reject_reason": reject_reason,
                "conflict_code": conflict_code,
                "policy_version_id": str(policy_version_id) if policy_version_id else None,
                "resolution_event_id": str(model.id),
            },
            actor_context=OutboxActorContext(
                principal_type="customer" if user_id else "anonymous",
                principal_id=str(user_id) if user_id else None,
            ),
            source_context={"source_use_case": "GrowthCodeRegistryService.record_resolution_event"},
        )
        log_growth_code_event(
            event_name,
            surface=surface,
            code_type=code_type,
            action_context=action_context,
            result=result,
            reject_reason=reject_reason,
            growth_code_id=str(growth_code_id) if growth_code_id else None,
            resolution_event_id=str(model.id),
        )
        return model


def _invite_status(*, invite, now: datetime) -> str:
    if invite.is_used:
        return "redeemed"
    expires_at = _coerce_utc(invite.expires_at)
    if expires_at is not None and expires_at <= now:
        return "expired"
    return "active"


def _promo_status(*, promo, now: datetime) -> str:
    if not promo.is_active:
        return "inactive"
    expires_at = _coerce_utc(promo.expires_at)
    if expires_at is not None and expires_at <= now:
        return "expired"
    if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
        return "exhausted"
    return "active"


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
