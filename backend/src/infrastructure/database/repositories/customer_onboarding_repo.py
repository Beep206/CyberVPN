from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import CustomerOnboardingRuntimeConfig
from src.application.use_cases.customer_onboarding import (
    ConnectionPlatform,
    ConnectionSurface,
    CustomerConnectionMarkResult,
    CustomerOnboardingAppliedCode,
    CustomerOnboardingApplyResult,
    CustomerOnboardingCodeApplier,
    CustomerOnboardingCurrentState,
    CustomerOnboardingSkipResult,
)
from src.infrastructure.database.models.customer_onboarding_model import (
    CustomerConnectionSessionModel,
    CustomerOnboardingCodeApplicationModel,
    CustomerOnboardingStateModel,
)

_OnboardingApplyCodeType = Literal["promo", "invite", "gift"]


class CustomerOnboardingStateSqlAlchemyRepository:
    """SQLAlchemy-backed post-registration onboarding state machine."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_pending(
        self,
        *,
        user_id: UUID,
        runtime_config: CustomerOnboardingRuntimeConfig,
        source_channel: str,
        auth_channel: str,
        referral_terminal_state: str | None = None,
    ) -> CustomerOnboardingCurrentState:
        state = await self._get_state(
            user_id=user_id,
            flow_key=runtime_config.flow_key,
            version=runtime_config.version,
            lock=True,
        )
        if state is None:
            now = datetime.now(UTC)
            state = CustomerOnboardingStateModel(
                mobile_user_id=user_id,
                flow_key=runtime_config.flow_key,
                flow_version=runtime_config.version,
                source_channel=_bounded(source_channel, 30),
                status="pending",
                skippable=True,
                first_eligible_at=now,
                auth_channel=_bounded(auth_channel, 40),
                referral_terminal_state=_bounded_or_none(referral_terminal_state, 30),
                result_payload={},
            )
            self._session.add(state)
            await self._session.flush()
        return self._state_to_current(state, runtime_config=runtime_config)

    async def get_current(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
    ) -> CustomerOnboardingCurrentState | None:
        state = await self._get_state(user_id=user_id, flow_key=flow_key, version=version, lock=False)
        if state is None:
            return None
        return self._state_to_current(
            state,
            runtime_config=CustomerOnboardingRuntimeConfig(
                post_registration_code_prompt_enabled=True,
                state_store_ready=True,
                web_otp_enabled=True,
                telegram_miniapp_enabled=True,
                flow_key=flow_key,
                version=version,
            ),
        )

    async def apply_growth_code(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
        normalized_code: str,
        normalized_code_hash: str,
        masked_code: str,
        idempotency_key: str | None,
        code_applier: CustomerOnboardingCodeApplier | None = None,
    ) -> CustomerOnboardingApplyResult:
        state = await self._get_state(user_id=user_id, flow_key=flow_key, version=version, lock=True)
        if state is None:
            return CustomerOnboardingApplyResult(
                status="pending",
                message_key="onboarding.state_unavailable",
                commit_required=False,
            )

        if state.status == "completed":
            return CustomerOnboardingApplyResult(
                status="completed",
                message_key=str(state.result_payload.get("message_key") or "onboarding.code.already_completed"),
                masked_code=str(state.result_payload.get("masked_code") or masked_code),
                next_destination=str(state.result_payload.get("next_destination") or "/dashboard"),
                code_type=_snapshot_code_type(state.result_payload),
                connection_required=bool(state.result_payload.get("connection_required")),
            )
        if state.status == "skipped":
            return CustomerOnboardingApplyResult(
                status="skipped",
                message_key="onboarding.already_skipped",
                commit_required=False,
            )

        stable_idempotency_key = idempotency_key or normalized_code_hash
        existing_application = await self._get_application(user_id=user_id, idempotency_key=stable_idempotency_key)
        if existing_application is not None:
            return CustomerOnboardingApplyResult(
                status="completed",
                message_key=str(
                    existing_application.safe_result_snapshot.get("message_key") or "onboarding.code.accepted"
                ),
                masked_code=str(existing_application.safe_result_snapshot.get("masked_code") or masked_code),
                next_destination=str(existing_application.safe_result_snapshot.get("next_destination") or "/dashboard"),
                code_type=_snapshot_code_type(existing_application.safe_result_snapshot),
                connection_required=bool(existing_application.safe_result_snapshot.get("connection_required")),
            )

        now = datetime.now(UTC)
        applied_code = (
            await code_applier.apply_code(
                code=normalized_code,
                user_id=user_id,
                idempotency_key=stable_idempotency_key,
                normalized_code_hash=normalized_code_hash,
                masked_code=masked_code,
            )
            if code_applier is not None
            else CustomerOnboardingAppliedCode(
                result="accepted",
                code_type="promo",
                message_key="onboarding.code.accepted",
                masked_code=masked_code,
            )
        )
        snapshot = _safe_application_snapshot(applied_code)
        application = CustomerOnboardingCodeApplicationModel(
            onboarding_state_id=state.id,
            mobile_user_id=user_id,
            action_context="post_registration",
            result=applied_code.result,
            idempotency_key=stable_idempotency_key,
            code_hash=normalized_code_hash,
            code_prefix=masked_code[:12],
            safe_result_snapshot=snapshot,
            referral_terminal_state=state.referral_terminal_state,
            auth_channel=state.auth_channel,
            return_route_key=state.return_route_key,
        )
        self._session.add(application)
        await self._session.flush()

        state.status = "completed"
        state.submitted_at = now
        state.completed_at = now
        state.result_code_application_id = application.id
        state.result_payload = snapshot
        await self._session.flush()
        return CustomerOnboardingApplyResult(
            status="completed",
            message_key=applied_code.message_key,
            masked_code=applied_code.masked_code,
            next_destination=applied_code.next_destination,
            code_type=applied_code.code_type,
            connection_required=_connection_required_for_applied_code(applied_code),
        )

    async def skip(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
        idempotency_key: str | None,
    ) -> CustomerOnboardingSkipResult:
        state = await self._get_state(user_id=user_id, flow_key=flow_key, version=version, lock=True)
        if state is None:
            return CustomerOnboardingSkipResult(
                status="skipped",
                message_key="onboarding.state_unavailable",
                commit_required=False,
            )
        if state.status == "completed":
            return CustomerOnboardingSkipResult(
                status="completed",
                message_key="onboarding.already_completed",
                commit_required=False,
            )
        if state.status == "skipped":
            return CustomerOnboardingSkipResult(
                status="skipped",
                message_key="onboarding.already_skipped",
                commit_required=False,
            )

        now = datetime.now(UTC)
        state.status = "skipped"
        state.skipped_at = now
        state.result_payload = {
            "message_key": "onboarding.skipped",
            "idempotency_key_present": idempotency_key is not None,
            "idempotency_key_hash": _hash_public_identifier(idempotency_key) if idempotency_key is not None else None,
        }
        await self._session.flush()
        return CustomerOnboardingSkipResult(status="skipped", message_key="onboarding.skipped")

    async def _get_state(
        self,
        *,
        user_id: UUID,
        flow_key: str,
        version: int,
        lock: bool,
    ) -> CustomerOnboardingStateModel | None:
        stmt = select(CustomerOnboardingStateModel).where(
            CustomerOnboardingStateModel.mobile_user_id == user_id,
            CustomerOnboardingStateModel.flow_key == flow_key,
            CustomerOnboardingStateModel.flow_version == version,
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_application(
        self,
        *,
        user_id: UUID,
        idempotency_key: str,
    ) -> CustomerOnboardingCodeApplicationModel | None:
        result = await self._session.execute(
            select(CustomerOnboardingCodeApplicationModel).where(
                CustomerOnboardingCodeApplicationModel.mobile_user_id == user_id,
                CustomerOnboardingCodeApplicationModel.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _state_to_current(
        state: CustomerOnboardingStateModel,
        *,
        runtime_config: CustomerOnboardingRuntimeConfig,
    ) -> CustomerOnboardingCurrentState:
        status = _public_status(state.status)
        return CustomerOnboardingCurrentState(
            required=status == "pending",
            status=status,
            flow_key=state.flow_key,
            version=state.flow_version,
            allowed_code_types=runtime_config.allowed_code_types,
            message_key=_message_key_for_status(status),
            server_state_available=True,
            referral_already_attributed=state.referral_terminal_state == "claimed",
            connection_required=bool(state.result_payload.get("connection_required")),
        )


class CustomerConnectionSessionSqlAlchemyRepository:
    """SQLAlchemy-backed connection bootstrap session ledger.

    Only the config hash and safe metadata are persisted; raw VPN subscription
    URLs stay in the authenticated response and are not stored in this ledger.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_available(
        self,
        *,
        user_id: UUID,
        source_surface: ConnectionSurface,
        subscription_config_hash: str,
        selected_platform: ConnectionPlatform,
        flow_key: str,
        version: int,
        expires_at: datetime,
        metadata: dict[str, object],
    ) -> UUID:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(CustomerConnectionSessionModel)
            .where(
                CustomerConnectionSessionModel.mobile_user_id == user_id,
                CustomerConnectionSessionModel.subscription_config_hash == subscription_config_hash,
            )
            .with_for_update()
        )
        session = result.scalar_one_or_none()
        if session is None:
            session = CustomerConnectionSessionModel(
                mobile_user_id=user_id,
                source_surface=source_surface,
                status="available",
                subscription_config_hash=subscription_config_hash,
                session_key_hash=_hash_public_identifier(f"{user_id}:{subscription_config_hash}"),
                selected_platform=selected_platform,
                expires_at=expires_at,
                metadata_=_connection_session_metadata(
                    metadata=metadata,
                    flow_key=flow_key,
                    version=version,
                ),
            )
            self._session.add(session)
        else:
            if session.status in {"pending", "expired", "unavailable", "cancelled"}:
                session.status = "available"
                session.acknowledged_at = None
                session.acknowledged_source_surface = None
            session.source_surface = source_surface
            session.selected_platform = selected_platform
            session.expires_at = max(session.expires_at, expires_at)
            session.metadata_ = _connection_session_metadata(
                metadata=metadata,
                flow_key=flow_key,
                version=version,
            )
            session.updated_at = now

        await self._session.flush()
        await self._cancel_other_available_sessions(user_id=user_id, active_session_id=session.id, now=now)
        await self._session.flush()
        return session.id

    async def mark_connected(
        self,
        *,
        user_id: UUID,
        connection_session_id: UUID,
        source_surface: ConnectionSurface,
        selected_platform: ConnectionPlatform,
        flow_key: str | None,
        version: int | None,
        connected_at: datetime,
    ) -> CustomerConnectionMarkResult:
        criteria = [
            CustomerConnectionSessionModel.mobile_user_id == user_id,
            CustomerConnectionSessionModel.id == connection_session_id,
            CustomerConnectionSessionModel.status.in_(("available", "acknowledged")),
            CustomerConnectionSessionModel.expires_at > connected_at,
        ]
        if flow_key is not None:
            criteria.append(CustomerConnectionSessionModel.metadata_["flow_key"].as_string() == flow_key)
        if version is not None:
            criteria.append(CustomerConnectionSessionModel.metadata_["version"].as_integer() == version)

        result = await self._session.execute(
            select(CustomerConnectionSessionModel)
            .where(*criteria)
            .order_by(desc(CustomerConnectionSessionModel.created_at))
            .limit(1)
            .with_for_update()
        )
        session = result.scalar_one_or_none()
        if session is None:
            return CustomerConnectionMarkResult(
                status="not_required",
                next_destination="/dashboard",
                flow_key=flow_key,
                version=version,
            )

        session_flow_key = _metadata_str(session.metadata_, "flow_key") or flow_key
        session_version = _metadata_int(session.metadata_, "version") or version
        if session.status == "acknowledged":
            return CustomerConnectionMarkResult(
                status="already_recorded",
                next_destination="/dashboard",
                connected_at=session.acknowledged_at,
                flow_key=session_flow_key,
                version=session_version,
            )

        session.status = "acknowledged"
        session.acknowledged_at = connected_at
        session.acknowledged_source_surface = source_surface
        session.selected_platform = selected_platform
        session.updated_at = connected_at
        await self._session.flush()
        return CustomerConnectionMarkResult(
            status="recorded",
            next_destination="/dashboard",
            connected_at=connected_at,
            flow_key=session_flow_key,
            version=session_version,
        )

    async def _cancel_other_available_sessions(
        self,
        *,
        user_id: UUID,
        active_session_id: UUID,
        now: datetime,
    ) -> None:
        result = await self._session.execute(
            select(CustomerConnectionSessionModel)
            .where(
                CustomerConnectionSessionModel.mobile_user_id == user_id,
                CustomerConnectionSessionModel.id != active_session_id,
                CustomerConnectionSessionModel.status.in_(("pending", "available")),
            )
            .with_for_update()
        )
        for stale_session in result.scalars():
            stale_session.status = "cancelled"
            stale_session.updated_at = now


def _public_status(status: str) -> Literal["unavailable", "pending", "completed", "skipped"]:
    if status in {"pending", "shown", "submitted", "failed_retryable"}:
        return "pending"
    if status == "completed":
        return "completed"
    if status == "skipped":
        return "skipped"
    return "unavailable"


def _message_key_for_status(status: str) -> str:
    if status == "pending":
        return "onboarding.required"
    if status == "completed":
        return "onboarding.completed"
    if status == "skipped":
        return "onboarding.skipped"
    return "onboarding.state_unavailable"


def _safe_application_snapshot(applied_code: CustomerOnboardingAppliedCode) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "message_key": applied_code.message_key,
        "masked_code": applied_code.masked_code,
        "result": applied_code.result,
        "code_type": applied_code.code_type,
        "next_destination": applied_code.next_destination,
        "connection_required": _connection_required_for_applied_code(applied_code),
    }
    optional_ids = {
        "resolved_code_id": applied_code.resolved_code_id,
        "growth_code_id": applied_code.growth_code_id,
        "redemption_id": applied_code.redemption_id,
        "entitlement_grant_id": applied_code.entitlement_grant_id,
    }
    for key, value in optional_ids.items():
        if value is not None:
            snapshot[key] = str(value)
    if applied_code.entitlement_snapshot is not None:
        snapshot["entitlement_snapshot"] = dict(applied_code.entitlement_snapshot)
    if applied_code.safe_details is not None:
        snapshot.update(dict(applied_code.safe_details))
    return snapshot


def _connection_required_for_applied_code(applied_code: CustomerOnboardingAppliedCode) -> bool:
    return (
        applied_code.result == "accepted"
        and applied_code.code_type in {"invite", "gift"}
        and (applied_code.entitlement_grant_id is not None or bool(applied_code.entitlement_snapshot))
    )


def _snapshot_code_type(snapshot: dict[str, object]) -> _OnboardingApplyCodeType | None:
    value = snapshot.get("code_type")
    if value == "promo":
        return "promo"
    if value == "invite":
        return "invite"
    if value == "gift":
        return "gift"
    return None


def _bounded(value: str, max_length: int) -> str:
    return value.strip()[:max_length] or "unknown"


def _bounded_or_none(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()[:max_length]
    return normalized or None


def _hash_public_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _connection_session_metadata(
    *,
    metadata: dict[str, object],
    flow_key: str,
    version: int,
) -> dict[str, object]:
    safe: dict[str, object] = {
        "flow_key": _bounded(flow_key, 80),
        "version": version,
    }
    for key in ("config_profile_name", "entitlement_status", "service_identity_ready"):
        value = metadata.get(key)
        if isinstance(value, str):
            safe[key] = _bounded(value, 120)
        elif isinstance(value, bool):
            safe[key] = value
        elif value is not None:
            safe[key] = str(value)[:120]
    return safe


def _metadata_str(metadata: dict[str, object] | None, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    return value if isinstance(value, str) and value else None


def _metadata_int(metadata: dict[str, object] | None, key: str) -> int | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
