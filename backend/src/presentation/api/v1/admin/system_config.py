from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.config_service import (
    CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
    ConfigService,
    CustomerSiteRuntimeConfig,
    MiniAppLaunchReadinessConfig,
    MiniAppRuntimeConfig,
)
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.audit_log_model import AuditLog
from src.infrastructure.database.models.system_config_model import SystemConfigModel
from src.infrastructure.database.repositories.audit_log_repo import AuditLogRepository
from src.infrastructure.database.repositories.system_config_repo import SystemConfigRepository
from src.infrastructure.monitoring.instrumentation.routes import (
    sync_miniapp_launch_control_metrics,
    track_miniapp_launch_action,
)
from src.infrastructure.monitoring.metrics import route_operations_total
from src.presentation.api.v1.admin.schemas import (
    AdminCustomerSiteRuntimeConfigResponse,
    AdminCustomerSiteRuntimeResponse,
    AdminCustomerSiteRuntimeTimelineEntryResponse,
    AdminMiniAppLaunchReadinessConfigResponse,
    AdminMiniAppLaunchReadinessResponse,
    AdminMiniAppLaunchSummaryResponse,
    AdminMiniAppLaunchTimelineEntryResponse,
    AdminMiniAppRuntimeConfigResponse,
    AdminMiniAppRuntimeRolloutResponse,
    ExecuteAdminCustomerSiteRuntimeActionRequest,
    ExecuteAdminMiniAppLaunchActionRequest,
    UpdateAdminCustomerSiteRuntimeConfigRequest,
    UpdateAdminMiniAppLaunchReadinessConfigRequest,
    UpdateAdminMiniAppRuntimeConfigRequest,
)
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.roles import require_role

router = APIRouter(prefix="/admin/system-config", tags=["admin", "system-config"])

MINIAPP_RUNTIME_CONFIG_KEY = "miniapp.runtime"
MINIAPP_RUNTIME_CONFIG_DESCRIPTION = "Operator-controlled rollout policy for Telegram Mini App runtime."
MINIAPP_LAUNCH_READINESS_CONFIG_KEY = "miniapp.launch_readiness"
MINIAPP_LAUNCH_READINESS_CONFIG_DESCRIPTION = "Production launch readiness gates for Telegram Mini App runtime."
CUSTOMER_SITE_RUNTIME_CONFIG_DESCRIPTION = "Operator-controlled runtime routing policy for customer web site mode."
MINIAPP_LAUNCH_TIMELINE_ACTIONS = (
    "system_config.miniapp_runtime.updated",
    "system_config.miniapp_launch_readiness.updated",
    "system_config.miniapp_launch_action.executed",
)
CUSTOMER_SITE_RUNTIME_TIMELINE_ACTIONS = (
    "system_config.customer_site_runtime.updated",
    "system_config.customer_site_runtime.action_executed",
)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_customer_site_hostname(value: str) -> str | None:
    candidate = value.strip().lower().rstrip(".")
    if not candidate or "://" in candidate or "/" in candidate or "?" in candidate or "#" in candidate:
        return None
    return candidate[:255]


def _normalize_customer_site_hostnames(values: list[str], *, fallback: tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        candidate = _normalize_customer_site_hostname(value)
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    if normalized:
        return normalized
    return list(fallback)


def _normalize_customer_site_path(value: str, *, fallback: str = "/dashboard") -> str:
    candidate = value.strip()
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    return candidate.rstrip("/") or "/"


def _normalize_customer_site_path_prefixes(values: list[str], *, fallback: tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        candidate = _normalize_customer_site_path(value, fallback="")
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    if normalized:
        return normalized
    return list(fallback)


def _normalize_customer_site_query_keys(values: list[str], *, fallback: tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        candidate = value.strip()
        if not candidate or len(candidate) > 80:
            continue
        if not all(ch.isalnum() or ch in {"_", "-"} for ch in candidate):
            continue
        if candidate not in normalized:
            normalized.append(candidate)
    if normalized:
        return normalized
    return list(fallback)


def _serialize_customer_site_runtime(
    config: CustomerSiteRuntimeConfig,
) -> AdminCustomerSiteRuntimeResponse:
    return AdminCustomerSiteRuntimeResponse(
        mode=config.mode,
        version=config.version,
        public_hosts=list(config.public_hosts),
        cabinet_hosts=list(config.cabinet_hosts),
        cabinet_destination_path=config.cabinet_destination_path,
        allowed_path_prefixes=list(config.allowed_path_prefixes),
        cabinet_allowed_prefixes=list(config.cabinet_allowed_prefixes),
        cabinet_marketing_route_action=config.cabinet_marketing_route_action,
        public_marketing_destination_path=config.public_marketing_destination_path,
        legal_path_prefixes=list(config.legal_path_prefixes),
        operational_path_prefixes=list(config.operational_path_prefixes),
        preserve_query_keys=list(config.preserve_query_keys),
        cabinet_only=config.cabinet_only,
        registration_policy_independent=True,
    )


def _serialize_customer_site_runtime_response(
    *,
    model: SystemConfigModel | None,
    config: CustomerSiteRuntimeConfig,
    last_change_reason: str | None = None,
) -> AdminCustomerSiteRuntimeConfigResponse:
    return AdminCustomerSiteRuntimeConfigResponse(
        key=CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
        site=_serialize_customer_site_runtime(config),
        description=(model.description if model is not None else CUSTOMER_SITE_RUNTIME_CONFIG_DESCRIPTION),
        updated_at=model.updated_at if model is not None else None,
        updated_by=model.updated_by if model is not None else None,
        last_change_reason=last_change_reason,
    )


def _serialize_rollout(config: MiniAppRuntimeConfig) -> AdminMiniAppRuntimeRolloutResponse:
    return AdminMiniAppRuntimeRolloutResponse(
        enabled=config.enabled,
        mode=config.mode,
        trial_enabled=config.trial_enabled,
        checkout_enabled=config.checkout_enabled,
        config_enabled=config.config_enabled,
        maintenance_message=config.maintenance_message,
        canary_telegram_user_ids=list(config.canary_telegram_user_ids),
    )


def _serialize_runtime_response(
    *,
    model: SystemConfigModel | None,
    config: MiniAppRuntimeConfig,
) -> AdminMiniAppRuntimeConfigResponse:
    return AdminMiniAppRuntimeConfigResponse(
        key=MINIAPP_RUNTIME_CONFIG_KEY,
        rollout=_serialize_rollout(config),
        description=model.description if model is not None else MINIAPP_RUNTIME_CONFIG_DESCRIPTION,
        updated_at=model.updated_at if model is not None else None,
        updated_by=model.updated_by if model is not None else None,
    )


def _serialize_launch_readiness(
    config: MiniAppLaunchReadinessConfig,
) -> AdminMiniAppLaunchReadinessResponse:
    return AdminMiniAppLaunchReadinessResponse(
        observability_acknowledged=config.observability_acknowledged,
        incident_runbook_acknowledged=config.incident_runbook_acknowledged,
        checkout_canary_passed=config.checkout_canary_passed,
        config_delivery_canary_passed=config.config_delivery_canary_passed,
        rollback_drill_acknowledged=config.rollback_drill_acknowledged,
        support_window_confirmed=config.support_window_confirmed,
        customer_comms_ready=config.customer_comms_ready,
        status_page_template_ready=config.status_page_template_ready,
        incident_channel=config.incident_channel,
        rollback_commander=config.rollback_commander,
        primary_oncall_contact=config.primary_oncall_contact,
        release_window_note=config.release_window_note,
        is_ready=config.is_ready,
    )


def _serialize_launch_readiness_response(
    *,
    model: SystemConfigModel | None,
    config: MiniAppLaunchReadinessConfig,
) -> AdminMiniAppLaunchReadinessConfigResponse:
    return AdminMiniAppLaunchReadinessConfigResponse(
        key=MINIAPP_LAUNCH_READINESS_CONFIG_KEY,
        readiness=_serialize_launch_readiness(config),
        description=(model.description if model is not None else MINIAPP_LAUNCH_READINESS_CONFIG_DESCRIPTION),
        updated_at=model.updated_at if model is not None else None,
        updated_by=model.updated_by if model is not None else None,
    )


def _build_launch_readiness_blockers(
    config: MiniAppLaunchReadinessConfig,
) -> list[str]:
    blockers: list[str] = []
    if not config.observability_acknowledged:
        blockers.append("observability_unacknowledged")
    if not config.incident_runbook_acknowledged:
        blockers.append("incident_runbook_unacknowledged")
    if not config.checkout_canary_passed:
        blockers.append("checkout_canary_not_passed")
    if not config.config_delivery_canary_passed:
        blockers.append("config_delivery_canary_not_passed")
    if not config.rollback_drill_acknowledged:
        blockers.append("rollback_drill_unacknowledged")
    if not config.support_window_confirmed:
        blockers.append("support_window_unconfirmed")
    if not config.customer_comms_ready:
        blockers.append("customer_comms_not_ready")
    if not config.status_page_template_ready:
        blockers.append("status_page_template_not_ready")
    if not config.incident_channel:
        blockers.append("incident_channel_missing")
    if not config.rollback_commander:
        blockers.append("rollback_commander_missing")
    if not config.primary_oncall_contact:
        blockers.append("primary_oncall_contact_missing")
    return blockers


def _build_launch_actions(
    *,
    runtime: MiniAppRuntimeConfig,
    readiness: MiniAppLaunchReadinessConfig,
    launch_state: str,
) -> tuple[list[str], str | None]:
    available_actions: list[str] = []
    primary_action: str | None = None
    has_canary_allowlist = bool(runtime.canary_telegram_user_ids)

    if launch_state == "ready_for_live":
        available_actions = ["promote_to_live", "enter_maintenance", "start_rollback"]
        primary_action = "promote_to_live"
    elif launch_state == "canary_in_progress":
        available_actions = ["enter_maintenance", "start_rollback"]
    elif launch_state == "live":
        available_actions = ["start_rollback", "enter_maintenance"]
        if has_canary_allowlist:
            available_actions.append("return_to_canary")
    elif launch_state == "rollback_in_progress":
        available_actions = ["enter_maintenance"]
        if has_canary_allowlist:
            available_actions.insert(0, "return_to_canary")
            primary_action = "return_to_canary"
        else:
            primary_action = "enter_maintenance"
    elif launch_state == "maintenance":
        if has_canary_allowlist:
            available_actions = ["return_to_canary"]
            primary_action = "return_to_canary"
        elif readiness.is_ready:
            available_actions = ["promote_to_live"]
            primary_action = "promote_to_live"
    elif launch_state == "blocked":
        available_actions = ["enter_maintenance"]

    return available_actions, primary_action


def _build_launch_summary(
    *,
    runtime: MiniAppRuntimeConfig,
    readiness: MiniAppLaunchReadinessConfig,
) -> AdminMiniAppLaunchSummaryResponse:
    blockers = _build_launch_readiness_blockers(readiness)
    launch_state = "blocked"
    live_switch_allowed = False
    next_action = "stabilize_runtime"
    if not runtime.enabled or runtime.mode == "maintenance":
        if not runtime.enabled:
            blockers = ["runtime_disabled", *blockers]
        else:
            blockers = ["maintenance_mode_active", *blockers]
        launch_state = "maintenance"
        next_action = "hold_maintenance"
    elif runtime.mode == "rollback":
        blockers = ["rollback_mode_active", *blockers]
        launch_state = "rollback_in_progress"
        next_action = "finish_rollback"
    elif runtime.mode == "canary":
        if readiness.is_ready:
            launch_state = "ready_for_live"
            live_switch_allowed = True
            next_action = "promote_to_live"
            blockers = []
        else:
            launch_state = "canary_in_progress"
            next_action = "complete_launch_gates"
    elif runtime.mode == "live":
        if readiness.is_ready:
            launch_state = "live"
            live_switch_allowed = True
            next_action = "keep_canary"
            blockers = []
        else:
            launch_state = "blocked"
            next_action = "stabilize_runtime"

    available_actions, primary_action = _build_launch_actions(
        runtime=runtime,
        readiness=readiness,
        launch_state=launch_state,
    )

    return AdminMiniAppLaunchSummaryResponse(
        launch_state=launch_state,
        live_switch_allowed=live_switch_allowed,
        next_action=next_action,
        primary_action=primary_action,
        available_actions=available_actions,
        blockers=blockers,
        runtime=_serialize_rollout(runtime),
        readiness=_serialize_launch_readiness(readiness),
    )


def _sync_launch_summary_metrics(summary: AdminMiniAppLaunchSummaryResponse) -> None:
    sync_miniapp_launch_control_metrics(
        launch_state=summary.launch_state,
        runtime_mode=summary.runtime.mode,
        live_switch_allowed=summary.live_switch_allowed,
        blockers_count=len(summary.blockers),
    )


def _serialize_launch_timeline_entry(
    entry: AuditLog,
) -> AdminMiniAppLaunchTimelineEntryResponse:
    payload = entry.new_value if isinstance(entry.new_value, dict) else {}
    resulting_runtime_mode = None
    resulting_launch_state = None
    readiness_ready = None
    action_name = None

    if entry.action == "system_config.miniapp_runtime.updated":
        event_type = "runtime_update"
        resulting_runtime_mode = payload.get("mode")
    elif entry.action == "system_config.miniapp_launch_readiness.updated":
        event_type = "launch_readiness_update"
        readiness_ready = payload.get("is_ready")
    else:
        event_type = "launch_action"
        action_name = payload.get("action")
        runtime_payload = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
        summary_payload = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        resulting_runtime_mode = runtime_payload.get("mode")
        resulting_launch_state = summary_payload.get("launch_state")

    return AdminMiniAppLaunchTimelineEntryResponse(
        id=entry.id,
        created_at=entry.created_at,
        admin_id=entry.admin_id,
        action=entry.action,
        event_type=event_type,
        action_name=action_name,
        resulting_runtime_mode=resulting_runtime_mode,
        resulting_launch_state=resulting_launch_state,
        readiness_ready=readiness_ready,
        change_reason=payload.get("change_reason"),
        entity_id=entry.entity_id,
    )


def _serialize_customer_site_runtime_timeline_entry(
    entry: AuditLog,
) -> AdminCustomerSiteRuntimeTimelineEntryResponse:
    payload = entry.new_value if isinstance(entry.new_value, dict) else {}
    site_payload = payload.get("site") if isinstance(payload.get("site"), dict) else payload
    return AdminCustomerSiteRuntimeTimelineEntryResponse(
        id=entry.id,
        created_at=entry.created_at,
        admin_id=entry.admin_id,
        action=entry.action,
        event_type=(
            "site_mode_action"
            if entry.action == "system_config.customer_site_runtime.action_executed"
            else "site_mode_update"
        ),
        resulting_mode=site_payload.get("mode"),
        resulting_version=site_payload.get("version"),
        change_reason=payload.get("change_reason"),
        entity_id=entry.entity_id,
    )


async def _write_customer_site_runtime_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    action: str,
    previous_payload: dict[str, object],
    next_payload: dict[str, object],
    change_reason: str,
) -> None:
    audit_entry = AuditLog(
        admin_id=actor.id,
        action=action,
        entity_type="system_config",
        entity_id=CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
        old_value=previous_payload,
        new_value={
            "site": next_payload,
            "change_reason": change_reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_entry)
    await db.flush()


def _customer_site_runtime_payload(
    config: CustomerSiteRuntimeConfig,
) -> dict[str, object]:
    return _serialize_customer_site_runtime(config).model_dump()


def _assert_customer_site_expected_version(
    *,
    current_version: int,
    expected_version: int,
) -> None:
    if current_version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "customer_site_runtime_version_conflict",
                "message_key": "growth.siteMode.errors.versionConflict",
                "current_version": current_version,
                "expected_version": expected_version,
            },
        )


def _build_customer_site_runtime_update_payload(
    *,
    payload: UpdateAdminCustomerSiteRuntimeConfigRequest,
    current: CustomerSiteRuntimeConfig,
) -> dict[str, object]:
    public_hosts = _normalize_customer_site_hostnames(
        payload.public_hosts,
        fallback=current.public_hosts,
    )
    cabinet_hosts = _normalize_customer_site_hostnames(
        payload.cabinet_hosts,
        fallback=current.cabinet_hosts,
    )
    if set(public_hosts) & set(cabinet_hosts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "customer_site_runtime_host_overlap",
                "message_key": "growth.siteMode.errors.hostOverlap",
            },
        )

    return {
        "mode": payload.mode,
        "version": current.version + 1,
        "public_hosts": public_hosts,
        "cabinet_hosts": cabinet_hosts,
        "cabinet_destination_path": _normalize_customer_site_path(
            payload.cabinet_destination_path,
            fallback=current.cabinet_destination_path,
        ),
        "allowed_path_prefixes": _normalize_customer_site_path_prefixes(
            payload.allowed_path_prefixes,
            fallback=current.allowed_path_prefixes,
        ),
        "cabinet_allowed_prefixes": _normalize_customer_site_path_prefixes(
            payload.cabinet_allowed_prefixes,
            fallback=current.cabinet_allowed_prefixes,
        ),
        "cabinet_marketing_route_action": (
            payload.cabinet_marketing_route_action or current.cabinet_marketing_route_action
        ),
        "public_marketing_destination_path": _normalize_customer_site_path(
            payload.public_marketing_destination_path or current.public_marketing_destination_path,
            fallback=current.public_marketing_destination_path,
        ),
        "legal_path_prefixes": _normalize_customer_site_path_prefixes(
            payload.legal_path_prefixes,
            fallback=current.legal_path_prefixes,
        ),
        "operational_path_prefixes": _normalize_customer_site_path_prefixes(
            payload.operational_path_prefixes,
            fallback=current.operational_path_prefixes,
        ),
        "preserve_query_keys": _normalize_customer_site_query_keys(
            payload.preserve_query_keys,
            fallback=current.preserve_query_keys,
        ),
    }


@router.get(
    "/customer-site-runtime",
    response_model=AdminCustomerSiteRuntimeConfigResponse,
)
async def get_admin_customer_site_runtime_config(
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminCustomerSiteRuntimeConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    model = await repo.get_by_key(CUSTOMER_SITE_RUNTIME_CONFIG_KEY)
    config = await service.get_customer_site_runtime_config()
    route_operations_total.labels(
        route="admin_system_config",
        action="get_customer_site_runtime",
        status="success",
    ).inc()
    return _serialize_customer_site_runtime_response(model=model, config=config)


@router.put(
    "/customer-site-runtime",
    response_model=AdminCustomerSiteRuntimeConfigResponse,
)
async def update_admin_customer_site_runtime_config(
    payload: UpdateAdminCustomerSiteRuntimeConfigRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminCustomerSiteRuntimeConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    existing_model = await repo.get_by_key(CUSTOMER_SITE_RUNTIME_CONFIG_KEY)
    previous_config = await service.get_customer_site_runtime_config()
    _assert_customer_site_expected_version(
        current_version=previous_config.version,
        expected_version=payload.expected_version,
    )

    next_payload = _build_customer_site_runtime_update_payload(payload=payload, current=previous_config)
    change_reason = payload.change_reason.strip()
    await service.set(
        CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=existing_model.description
        if existing_model is not None and existing_model.description
        else CUSTOMER_SITE_RUNTIME_CONFIG_DESCRIPTION,
    )
    updated_model = await repo.get_by_key(CUSTOMER_SITE_RUNTIME_CONFIG_KEY)
    updated_config = await service.get_customer_site_runtime_config()
    await _write_customer_site_runtime_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        action="system_config.customer_site_runtime.updated",
        previous_payload=_customer_site_runtime_payload(previous_config),
        next_payload=_customer_site_runtime_payload(updated_config),
        change_reason=change_reason,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="update_customer_site_runtime",
        status="success",
    ).inc()
    return _serialize_customer_site_runtime_response(
        model=updated_model,
        config=updated_config,
        last_change_reason=change_reason,
    )


@router.post(
    "/customer-site-runtime/actions",
    response_model=AdminCustomerSiteRuntimeConfigResponse,
)
async def execute_admin_customer_site_runtime_action(
    payload: ExecuteAdminCustomerSiteRuntimeActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminCustomerSiteRuntimeConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    existing_model = await repo.get_by_key(CUSTOMER_SITE_RUNTIME_CONFIG_KEY)
    previous_config = await service.get_customer_site_runtime_config()
    _assert_customer_site_expected_version(
        current_version=previous_config.version,
        expected_version=payload.expected_version,
    )

    if payload.action != "rollback_to_full_site":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "customer_site_runtime_unknown_action",
                "message_key": "growth.siteMode.errors.unknownAction",
            },
        )

    next_payload = {
        "mode": "full_site",
        "version": previous_config.version + 1,
        "public_hosts": list(previous_config.public_hosts),
        "cabinet_hosts": list(previous_config.cabinet_hosts),
        "cabinet_destination_path": previous_config.cabinet_destination_path,
        "allowed_path_prefixes": list(previous_config.allowed_path_prefixes),
        "preserve_query_keys": list(previous_config.preserve_query_keys),
    }
    change_reason = payload.change_reason.strip()
    await service.set(
        CUSTOMER_SITE_RUNTIME_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=existing_model.description
        if existing_model is not None and existing_model.description
        else CUSTOMER_SITE_RUNTIME_CONFIG_DESCRIPTION,
    )
    updated_model = await repo.get_by_key(CUSTOMER_SITE_RUNTIME_CONFIG_KEY)
    updated_config = await service.get_customer_site_runtime_config()
    await _write_customer_site_runtime_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        action="system_config.customer_site_runtime.action_executed",
        previous_payload=_customer_site_runtime_payload(previous_config),
        next_payload=_customer_site_runtime_payload(updated_config),
        change_reason=change_reason,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="execute_customer_site_runtime_action",
        status="success",
    ).inc()
    return _serialize_customer_site_runtime_response(
        model=updated_model,
        config=updated_config,
        last_change_reason=change_reason,
    )


@router.get(
    "/customer-site-runtime/timeline",
    response_model=list[AdminCustomerSiteRuntimeTimelineEntryResponse],
)
async def get_admin_customer_site_runtime_timeline(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> list[AdminCustomerSiteRuntimeTimelineEntryResponse]:
    audit_repo = AuditLogRepository(db)
    entries = await audit_repo.get_recent_by_actions(
        CUSTOMER_SITE_RUNTIME_TIMELINE_ACTIONS,
        limit=limit,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="get_customer_site_runtime_timeline",
        status="success",
    ).inc()
    return [_serialize_customer_site_runtime_timeline_entry(entry) for entry in entries]


async def _write_runtime_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    previous_payload: dict[str, object],
    next_payload: dict[str, object],
    change_reason: str | None,
) -> None:
    audit_entry = AuditLog(
        admin_id=actor.id,
        action="system_config.miniapp_runtime.updated",
        entity_type="system_config",
        entity_id=MINIAPP_RUNTIME_CONFIG_KEY,
        old_value=previous_payload,
        new_value={
            **next_payload,
            "change_reason": change_reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_entry)
    await db.flush()


async def _write_launch_readiness_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    previous_payload: dict[str, object],
    next_payload: dict[str, object],
    change_reason: str | None,
) -> None:
    audit_entry = AuditLog(
        admin_id=actor.id,
        action="system_config.miniapp_launch_readiness.updated",
        entity_type="system_config",
        entity_id=MINIAPP_LAUNCH_READINESS_CONFIG_KEY,
        old_value=previous_payload,
        new_value={
            **next_payload,
            "change_reason": change_reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_entry)
    await db.flush()


async def _write_launch_action_audit_entry(
    *,
    db: AsyncSession,
    request: Request,
    actor: AdminUserModel,
    action_name: str,
    previous_runtime_payload: dict[str, object],
    next_runtime_payload: dict[str, object],
    previous_summary_payload: dict[str, object],
    next_summary_payload: dict[str, object],
    change_reason: str | None,
) -> None:
    audit_entry = AuditLog(
        admin_id=actor.id,
        action="system_config.miniapp_launch_action.executed",
        entity_type="system_config",
        entity_id=MINIAPP_RUNTIME_CONFIG_KEY,
        old_value={
            "runtime": previous_runtime_payload,
            "summary": previous_summary_payload,
        },
        new_value={
            "action": action_name,
            "runtime": next_runtime_payload,
            "summary": next_summary_payload,
            "change_reason": change_reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_entry)
    await db.flush()


@router.get(
    "/miniapp-runtime",
    response_model=AdminMiniAppRuntimeConfigResponse,
)
async def get_admin_miniapp_runtime_config(
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppRuntimeConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    model = await repo.get_by_key(MINIAPP_RUNTIME_CONFIG_KEY)
    config = await service.get_miniapp_runtime_config()
    route_operations_total.labels(
        route="admin_system_config",
        action="get_miniapp_runtime",
        status="success",
    ).inc()
    return _serialize_runtime_response(model=model, config=config)


@router.put(
    "/miniapp-runtime",
    response_model=AdminMiniAppRuntimeConfigResponse,
)
async def update_admin_miniapp_runtime_config(
    payload: UpdateAdminMiniAppRuntimeConfigRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppRuntimeConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)

    existing_model = await repo.get_by_key(MINIAPP_RUNTIME_CONFIG_KEY)
    previous_config = await service.get_miniapp_runtime_config()
    previous_payload = _serialize_rollout(previous_config).model_dump()
    launch_readiness = await service.get_miniapp_launch_readiness_config()
    canary_telegram_user_ids = sorted({candidate for candidate in payload.canary_telegram_user_ids if candidate > 0})

    if payload.mode == "canary" and not canary_telegram_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="canary_telegram_user_ids must contain at least one Telegram user id in canary mode",
        )
    if payload.enabled and payload.mode == "live" and not launch_readiness.is_ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Mini App launch readiness gates are incomplete. Complete launch "
                "readiness before switching runtime to live."
            ),
        )

    next_payload = {
        "enabled": payload.enabled,
        "mode": payload.mode,
        "trial_enabled": payload.trial_enabled,
        "checkout_enabled": payload.checkout_enabled,
        "config_enabled": payload.config_enabled,
        "maintenance_message": _normalize_optional_text(payload.maintenance_message),
        "canary_telegram_user_ids": canary_telegram_user_ids,
    }
    change_reason = _normalize_optional_text(payload.change_reason)

    await service.set(
        MINIAPP_RUNTIME_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=existing_model.description
        if existing_model is not None and existing_model.description
        else MINIAPP_RUNTIME_CONFIG_DESCRIPTION,
    )
    updated_model = await repo.get_by_key(MINIAPP_RUNTIME_CONFIG_KEY)
    updated_config = await service.get_miniapp_runtime_config()
    launch_summary = _build_launch_summary(
        runtime=updated_config,
        readiness=launch_readiness,
    )
    _sync_launch_summary_metrics(launch_summary)

    await _write_runtime_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        previous_payload=previous_payload,
        next_payload=_serialize_rollout(updated_config).model_dump(),
        change_reason=change_reason,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="update_miniapp_runtime",
        status="success",
    ).inc()
    return _serialize_runtime_response(model=updated_model, config=updated_config)


@router.get(
    "/miniapp-launch-readiness",
    response_model=AdminMiniAppLaunchReadinessConfigResponse,
)
async def get_admin_miniapp_launch_readiness_config(
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppLaunchReadinessConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    model = await repo.get_by_key(MINIAPP_LAUNCH_READINESS_CONFIG_KEY)
    config = await service.get_miniapp_launch_readiness_config()
    route_operations_total.labels(
        route="admin_system_config",
        action="get_miniapp_launch_readiness",
        status="success",
    ).inc()
    return _serialize_launch_readiness_response(model=model, config=config)


@router.get(
    "/miniapp-launch-summary",
    response_model=AdminMiniAppLaunchSummaryResponse,
)
async def get_admin_miniapp_launch_summary(
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppLaunchSummaryResponse:
    service = ConfigService(SystemConfigRepository(db))
    runtime = await service.get_miniapp_runtime_config()
    readiness = await service.get_miniapp_launch_readiness_config()
    route_operations_total.labels(
        route="admin_system_config",
        action="get_miniapp_launch_summary",
        status="success",
    ).inc()
    summary = _build_launch_summary(runtime=runtime, readiness=readiness)
    _sync_launch_summary_metrics(summary)
    return summary


@router.get(
    "/miniapp-launch-timeline",
    response_model=list[AdminMiniAppLaunchTimelineEntryResponse],
)
async def get_admin_miniapp_launch_timeline(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> list[AdminMiniAppLaunchTimelineEntryResponse]:
    audit_repo = AuditLogRepository(db)
    entries = await audit_repo.get_recent_by_actions(
        MINIAPP_LAUNCH_TIMELINE_ACTIONS,
        limit=limit,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="get_miniapp_launch_timeline",
        status="success",
    ).inc()
    return [_serialize_launch_timeline_entry(entry) for entry in entries]


@router.post(
    "/miniapp-launch-actions",
    response_model=AdminMiniAppLaunchSummaryResponse,
)
async def execute_admin_miniapp_launch_action(
    payload: ExecuteAdminMiniAppLaunchActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppLaunchSummaryResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)
    existing_model = await repo.get_by_key(MINIAPP_RUNTIME_CONFIG_KEY)
    runtime = await service.get_miniapp_runtime_config()
    readiness = await service.get_miniapp_launch_readiness_config()
    previous_summary = _build_launch_summary(runtime=runtime, readiness=readiness)
    _sync_launch_summary_metrics(previous_summary)

    if payload.action not in previous_summary.available_actions:
        track_miniapp_launch_action(action=payload.action, status="blocked")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Launch action '{payload.action}' is not allowed while Mini App "
                f"launch state is '{previous_summary.launch_state}'."
            ),
        )

    next_payload = {
        "enabled": runtime.enabled,
        "mode": runtime.mode,
        "trial_enabled": runtime.trial_enabled,
        "checkout_enabled": runtime.checkout_enabled,
        "config_enabled": runtime.config_enabled,
        "maintenance_message": runtime.maintenance_message,
        "canary_telegram_user_ids": list(runtime.canary_telegram_user_ids),
    }

    if payload.action == "promote_to_live":
        next_payload["enabled"] = True
        next_payload["mode"] = "live"
        next_payload["maintenance_message"] = None
    elif payload.action == "enter_maintenance":
        next_payload["enabled"] = True
        next_payload["mode"] = "maintenance"
    elif payload.action == "start_rollback":
        next_payload["enabled"] = True
        next_payload["mode"] = "rollback"
    elif payload.action == "return_to_canary":
        next_payload["enabled"] = True
        next_payload["mode"] = "canary"
        next_payload["maintenance_message"] = None

    change_reason = _normalize_optional_text(payload.change_reason)
    previous_runtime_payload = _serialize_rollout(runtime).model_dump()
    previous_summary_payload = previous_summary.model_dump()

    await service.set(
        MINIAPP_RUNTIME_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=existing_model.description
        if existing_model is not None and existing_model.description
        else MINIAPP_RUNTIME_CONFIG_DESCRIPTION,
    )

    updated_runtime = await service.get_miniapp_runtime_config()
    next_summary = _build_launch_summary(runtime=updated_runtime, readiness=readiness)
    _sync_launch_summary_metrics(next_summary)
    track_miniapp_launch_action(action=payload.action, status="executed")

    await _write_launch_action_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        action_name=payload.action,
        previous_runtime_payload=previous_runtime_payload,
        next_runtime_payload=_serialize_rollout(updated_runtime).model_dump(),
        previous_summary_payload=previous_summary_payload,
        next_summary_payload=next_summary.model_dump(),
        change_reason=change_reason,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="execute_miniapp_launch_action",
        status="success",
    ).inc()
    return next_summary


@router.put(
    "/miniapp-launch-readiness",
    response_model=AdminMiniAppLaunchReadinessConfigResponse,
)
async def update_admin_miniapp_launch_readiness_config(
    payload: UpdateAdminMiniAppLaunchReadinessConfigRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUserModel = Depends(require_role(AdminRole.OPERATOR)),
) -> AdminMiniAppLaunchReadinessConfigResponse:
    repo = SystemConfigRepository(db)
    service = ConfigService(repo)

    existing_model = await repo.get_by_key(MINIAPP_LAUNCH_READINESS_CONFIG_KEY)
    previous_config = await service.get_miniapp_launch_readiness_config()
    previous_payload = _serialize_launch_readiness(previous_config).model_dump()

    next_payload = {
        "observability_acknowledged": payload.observability_acknowledged,
        "incident_runbook_acknowledged": payload.incident_runbook_acknowledged,
        "checkout_canary_passed": payload.checkout_canary_passed,
        "config_delivery_canary_passed": payload.config_delivery_canary_passed,
        "rollback_drill_acknowledged": payload.rollback_drill_acknowledged,
        "support_window_confirmed": payload.support_window_confirmed,
        "customer_comms_ready": payload.customer_comms_ready,
        "status_page_template_ready": payload.status_page_template_ready,
        "incident_channel": _normalize_optional_text(payload.incident_channel),
        "rollback_commander": _normalize_optional_text(payload.rollback_commander),
        "primary_oncall_contact": _normalize_optional_text(payload.primary_oncall_contact),
        "release_window_note": _normalize_optional_text(payload.release_window_note),
    }
    change_reason = _normalize_optional_text(payload.change_reason)

    await service.set(
        MINIAPP_LAUNCH_READINESS_CONFIG_KEY,
        next_payload,
        updated_by=current_user.id,
        description=existing_model.description
        if existing_model is not None and existing_model.description
        else MINIAPP_LAUNCH_READINESS_CONFIG_DESCRIPTION,
    )
    updated_model = await repo.get_by_key(MINIAPP_LAUNCH_READINESS_CONFIG_KEY)
    updated_config = await service.get_miniapp_launch_readiness_config()
    runtime = await service.get_miniapp_runtime_config()
    launch_summary = _build_launch_summary(
        runtime=runtime,
        readiness=updated_config,
    )
    _sync_launch_summary_metrics(launch_summary)

    await _write_launch_readiness_audit_entry(
        db=db,
        request=request,
        actor=current_user,
        previous_payload=previous_payload,
        next_payload=_serialize_launch_readiness(updated_config).model_dump(),
        change_reason=change_reason,
    )
    route_operations_total.labels(
        route="admin_system_config",
        action="update_miniapp_launch_readiness",
        status="success",
    ).inc()
    return _serialize_launch_readiness_response(model=updated_model, config=updated_config)
