from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID

from src.application.services.config_service import CustomerOnboardingRuntimeConfig

ConnectionSurface = Literal["web", "miniapp", "telegram_bot"]
ConnectionPlatform = Literal["ios", "android", "windows", "macos", "linux", "unknown"]
ConnectionSupportedAction = Literal[
    "copy_subscription_url",
    "open_subscription_url",
    "show_qr",
    "send_qr_image",
    "show_instructions",
    "mark_connected",
    "open_dashboard",
    "open_miniapp",
]
ConnectionStatus = Literal[
    "available",
    "no_active_entitlement",
    "service_identity_pending",
    "config_unavailable",
    "disabled",
]
MarkConnectedStatus = Literal["recorded", "already_recorded", "not_required"]

_KNOWN_PLATFORMS: tuple[Literal["ios", "android", "windows", "macos", "linux"], ...] = (
    "ios",
    "android",
    "windows",
    "macos",
    "linux",
)
_ACTIVE_ENTITLEMENT_STATUSES = frozenset({"active", "trial", "grace_period"})
_SESSION_TTL = timedelta(days=30)


@dataclass(frozen=True, slots=True)
class CustomerConnectionInstructionStep:
    order: int
    title_key: str
    body_key: str
    action_url: str | None = None
    copy_value: str | None = None


@dataclass(frozen=True, slots=True)
class CustomerConnectionInstruction:
    platform: Literal["ios", "android", "windows", "macos", "linux"]
    title_key: str
    steps: tuple[CustomerConnectionInstructionStep, ...]
    recommended_apps: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CustomerConnectionBootstrapResult:
    available: bool
    status: ConnectionStatus
    message_key: str
    subscription_url: str | None = None
    qr_payload: str | None = None
    config_profile_name: str | None = None
    expires_at: datetime | None = None
    device_limit: int | None = None
    traffic_limit_bytes: int | None = None
    instructions: tuple[CustomerConnectionInstruction, ...] = ()
    surface: ConnectionSurface = "web"
    preferred_layout: Literal["desktop_panel", "mobile_panel", "bot_messages"] = "desktop_panel"
    supported_actions: tuple[ConnectionSupportedAction, ...] = ()
    flow_key: str | None = None
    version: int | None = None
    connection_session_id: str | None = None
    telegram_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CustomerConnectionMarkResult:
    status: MarkConnectedStatus
    next_destination: str
    connected_at: datetime | None = None
    flow_key: str | None = None
    version: int | None = None


class CustomerConnectionSessionRepository(Protocol):
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
    ) -> UUID: ...

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
    ) -> CustomerConnectionMarkResult: ...


class CustomerOnboardingConnectionBootstrapUseCase:
    def __init__(
        self,
        *,
        runtime_config: CustomerOnboardingRuntimeConfig,
        session_repo: CustomerConnectionSessionRepository | None = None,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._runtime = runtime_config
        self._session_repo = session_repo
        self._now_factory = now_factory

    async def execute(
        self,
        *,
        user_id: UUID,
        surface: ConnectionSurface,
        platform_hint: ConnectionPlatform,
        subscription_url: str | None,
        entitlement_status: str | None,
        service_identity_ready: bool,
        config_profile_name: str | None = None,
        device_limit: int | None = None,
        traffic_limit_bytes: int | None = None,
        entitlement_expires_at: datetime | None = None,
    ) -> CustomerConnectionBootstrapResult:
        preferred_layout: Literal["desktop_panel", "mobile_panel", "bot_messages"]
        if surface == "telegram_bot":
            preferred_layout = "bot_messages"
        elif surface == "miniapp":
            preferred_layout = "mobile_panel"
        else:
            preferred_layout = "desktop_panel"

        if not self._runtime.connection_bootstrap_available:
            return CustomerConnectionBootstrapResult(
                available=False,
                status="disabled",
                message_key="Auth.onboarding.connection.disabled",
                surface=surface,
                preferred_layout=preferred_layout,
                instructions=_connection_instructions(),
                flow_key=self._runtime.flow_key,
                version=self._runtime.version,
            )

        normalized_url = (subscription_url or "").strip() or None
        has_active_entitlement = entitlement_status in _ACTIVE_ENTITLEMENT_STATUSES
        if not has_active_entitlement:
            return CustomerConnectionBootstrapResult(
                available=False,
                status="no_active_entitlement",
                message_key="Auth.onboarding.connection.no_active_entitlement",
                surface=surface,
                preferred_layout=preferred_layout,
                instructions=_connection_instructions(),
                flow_key=self._runtime.flow_key,
                version=self._runtime.version,
            )

        if normalized_url is None:
            status: ConnectionStatus = (
                "service_identity_pending" if not service_identity_ready else "config_unavailable"
            )
            return CustomerConnectionBootstrapResult(
                available=False,
                status=status,
                message_key=f"Auth.onboarding.connection.{status}",
                surface=surface,
                preferred_layout=preferred_layout,
                instructions=_connection_instructions(),
                flow_key=self._runtime.flow_key,
                version=self._runtime.version,
            )

        session_id: UUID | None = None
        if self._session_repo is not None:
            config_hash = _hash_subscription_config(normalized_url)
            session_id = await self._session_repo.record_available(
                user_id=user_id,
                source_surface=surface,
                subscription_config_hash=config_hash,
                selected_platform=platform_hint,
                flow_key=self._runtime.flow_key,
                version=self._runtime.version,
                expires_at=self._now_factory() + _SESSION_TTL,
                metadata={
                    "flow_key": self._runtime.flow_key,
                    "version": self._runtime.version,
                    "config_profile_name": config_profile_name,
                    "entitlement_status": entitlement_status,
                    "service_identity_ready": service_identity_ready,
                },
            )

        telegram_payload: dict[str, object] | None = None
        if surface == "telegram_bot":
            telegram_payload = {
                "intro_message_key": "bot-onboarding-connection-ready",
                "safe_profile_label": config_profile_name,
                "subscription_url_button_text_key": "bot-onboarding-connection-open-link",
                "instructions_button_text_key": "bot-onboarding-connection-instructions",
                "mark_connected_button_text_key": "bot-onboarding-connection-connected",
                "dashboard_button_text_key": "bot-onboarding-connection-dashboard",
                "qr_caption_key": "bot-onboarding-connection-qr-caption",
                "bot_connection_session_id": str(session_id) if session_id is not None else None,
                "preferred_platform": platform_hint,
            }

        supported_actions = _supported_actions_for_surface(surface)
        return CustomerConnectionBootstrapResult(
            available=True,
            status="available",
            message_key="Auth.onboarding.connection.available",
            subscription_url=normalized_url,
            qr_payload=normalized_url,
            config_profile_name=config_profile_name,
            expires_at=entitlement_expires_at,
            device_limit=device_limit,
            traffic_limit_bytes=traffic_limit_bytes,
            instructions=_connection_instructions(),
            surface=surface,
            preferred_layout=preferred_layout,
            supported_actions=supported_actions,
            flow_key=self._runtime.flow_key,
            version=self._runtime.version,
            connection_session_id=str(session_id) if session_id is not None else None,
            telegram_payload=telegram_payload,
        )


class CustomerOnboardingMarkConnectedUseCase:
    def __init__(
        self,
        *,
        session_repo: CustomerConnectionSessionRepository,
        now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_repo = session_repo
        self._now_factory = now_factory

    async def execute(
        self,
        *,
        user_id: UUID,
        surface: ConnectionSurface,
        platform: ConnectionPlatform,
        flow_key: str | None,
        version: int | None,
        connection_session_id: UUID,
    ) -> CustomerConnectionMarkResult:
        result = await self._session_repo.mark_connected(
            user_id=user_id,
            connection_session_id=connection_session_id,
            source_surface=surface,
            selected_platform=platform,
            flow_key=flow_key,
            version=version,
            connected_at=self._now_factory(),
        )
        return CustomerConnectionMarkResult(
            status=result.status,
            next_destination=_next_destination(surface),
            connected_at=result.connected_at,
            flow_key=result.flow_key,
            version=result.version,
        )


def _connection_instructions() -> tuple[CustomerConnectionInstruction, ...]:
    return tuple(_instruction_for_platform(platform) for platform in _KNOWN_PLATFORMS)


def _supported_actions_for_surface(surface: ConnectionSurface) -> tuple[ConnectionSupportedAction, ...]:
    if surface == "telegram_bot":
        return (
            "open_subscription_url",
            "send_qr_image",
            "show_instructions",
            "mark_connected",
            "open_miniapp",
        )
    if surface == "miniapp":
        return (
            "copy_subscription_url",
            "open_subscription_url",
            "show_qr",
            "show_instructions",
            "mark_connected",
            "open_miniapp",
        )
    return (
        "copy_subscription_url",
        "open_subscription_url",
        "show_qr",
        "show_instructions",
        "mark_connected",
        "open_dashboard",
    )


def _instruction_for_platform(
    platform: Literal["ios", "android", "windows", "macos", "linux"],
) -> CustomerConnectionInstruction:
    return CustomerConnectionInstruction(
        platform=platform,
        title_key=f"Auth.onboarding.connection.platforms.{platform}",
        steps=tuple(
            CustomerConnectionInstructionStep(
                order=step,
                title_key=f"Auth.onboarding.connection.instructions.{platform}.step{step}.title",
                body_key=f"Auth.onboarding.connection.instructions.{platform}.step{step}.body",
            )
            for step in range(1, 5)
        ),
    )


def _hash_subscription_config(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _next_destination(surface: ConnectionSurface) -> str:
    return "/miniapp/home" if surface == "miniapp" else "/dashboard"
