"""CyberVPN-owned, admin-only proxy boundary for Remnawave 3.4 Node SSH."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import cast
from urllib.parse import urlparse
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, status
from httpx import HTTPStatusError, RequestError
from jwt.exceptions import PyJWTError as JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from src.application.services.auth_service import AuthService
from src.application.services.jwt_revocation_service import JWTRevocationService
from src.application.use_cases.auth.permissions import Permission, has_permission
from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.domain.enums import AdminRole, PrincipalClass
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.remnawave_node_ssh_tickets import (
    RemnawaveNodeSshTicketError,
    RemnawaveNodeSshTicketRecord,
    RemnawaveNodeSshTicketStore,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.remnawave.node_ssh_gateway import (
    MAX_SSH_WS_MESSAGE_BYTES,
    RemnawaveNodeSshGateway,
    RemnawaveNodeSshScopedBrokerUnavailable,
    RemnawaveUpstreamSshTicket,
    is_valid_remnawave_node_ssh_broker_secret,
    is_valid_remnawave_node_ssh_broker_url,
    remnawave_node_ssh_gateway,
)
from src.presentation.api.v1.admin.audit import write_required_admin_audit_entry
from src.presentation.api.v1.admin.remnawave_node_ssh_schemas import (
    AdminRemnawaveNodeSshRevokeRequest,
    AdminRemnawaveNodeSshTicketRequest,
    AdminRemnawaveNodeSshTicketResponse,
    AdminRemnawaveNodeSshVaultEvaluateRequest,
    AdminRemnawaveNodeSshVaultEvaluateResponse,
)
from src.presentation.api.v1.auth.cookies import get_access_token_cookie, get_web_device_cookie
from src.presentation.api.v1.auth.realm_context import get_principal_type_for_realm
from src.presentation.dependencies.auth import _resolve_current_admin_user_for_realm
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.client_ip import resolve_client_ip
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.passkey_fresh_auth import enforce_passkey_fresh_auth
from src.presentation.dependencies.roles import require_permission
from src.presentation.dependencies.services import get_auth_service
from src.presentation.middleware.csrf import normalize_origin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/remnawave/node-ssh", tags=["admin", "remnawave", "node-ssh"])

LOCAL_SSH_WS_PROTOCOL = "cybervpn-remnawave-ssh-v1"
LOCAL_SSH_WS_PATH = "/api/v1/admin/remnawave/node-ssh/ws"
CANONICAL_ADMIN_ORIGIN = "https://admin.cyber-vpn.net"
LOCAL_ADMIN_ORIGINS = frozenset(
    {
        "http://127.0.0.1:13001",
        "http://localhost:13001",
        "http://admin.localhost:13001",
        "http://127.0.0.1:3001",
        "http://localhost:3001",
        "http://admin.localhost:3001",
    }
)


def get_remnawave_node_ssh_gateway() -> RemnawaveNodeSshGateway:
    return remnawave_node_ssh_gateway


def _trusted_admin_ids() -> frozenset[UUID]:
    trusted: set[UUID] = set()
    for item in settings.remnawave_node_ssh_trusted_admin_ids.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        try:
            trusted.add(UUID(normalized))
        except ValueError:
            logger.error("Remnawave Node SSH trusted-admin allowlist contains an invalid UUID")
            return frozenset()
    return frozenset(trusted)


def _allowed_node_ids() -> frozenset[UUID]:
    allowed: set[UUID] = set()
    for item in settings.remnawave_node_ssh_allowed_node_ids.split(","):
        normalized = item.strip()
        if not normalized:
            continue
        try:
            allowed.add(UUID(normalized))
        except ValueError:
            logger.error("Remnawave Node SSH node allowlist contains an invalid UUID")
            return frozenset()
    return frozenset(allowed)


def is_remnawave_node_ssh_available_for(admin: AdminUserModel) -> bool:
    """Report the backend-enforced SSH capability for one authenticated admin."""
    if (
        not settings.remnawave_node_ssh_enabled
        or not is_valid_remnawave_node_ssh_broker_url(settings.remnawave_node_ssh_broker_url)
        or not is_valid_remnawave_node_ssh_broker_secret(settings.remnawave_node_ssh_broker_secret)
        or not settings.passkey_enabled
        or not settings.passkey_admin_enabled
    ):
        return False
    try:
        role = AdminRole(admin.role)
    except ValueError:
        return False
    return (
        admin.is_active
        and admin.deleted_at is None
        and has_permission(role, Permission.NODE_SSH_EXECUTE)
        and admin.id in _trusted_admin_ids()
        and bool(_allowed_node_ids())
    )


def _require_trusted_admin(admin: AdminUserModel) -> None:
    if (
        not settings.remnawave_node_ssh_enabled
        or not is_valid_remnawave_node_ssh_broker_url(settings.remnawave_node_ssh_broker_url)
        or not is_valid_remnawave_node_ssh_broker_secret(settings.remnawave_node_ssh_broker_secret)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node SSH is not enabled")
    if not is_remnawave_node_ssh_available_for(admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")


def _require_security_supervisor(admin: AdminUserModel) -> None:
    try:
        role = AdminRole(admin.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied") from exc
    if not admin.is_active or admin.deleted_at is not None or not has_permission(role, Permission.MANAGE_ADMINS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")


def _require_allowed_node(node_uuid: UUID) -> None:
    if node_uuid not in _allowed_node_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave node not found")


@dataclass(frozen=True, slots=True)
class _AuthenticatedAdminSshSession:
    admin: AdminUserModel
    auth_realm_id: UUID
    access_jti: str
    access_expires_at: datetime
    device_cookie: str = field(repr=False)


def _canonical_admin_origin(connection: HTTPConnection) -> str:
    source_origin = normalize_origin(connection.headers.get("origin")) or normalize_origin(
        connection.headers.get("referer")
    )
    if source_origin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin origin is required")
    if settings.environment.lower() != "production" and source_origin in LOCAL_ADMIN_ORIGINS:
        return CANONICAL_ADMIN_ORIGIN

    parsed = urlparse(source_origin)
    allowed_origins = {origin.rstrip("/") for origin in settings.cors_origins if origin != "*"}
    if (
        source_origin not in allowed_origins
        or parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.hostname.lower() not in settings.admin_allowed_hosts
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin origin is not allowed")
    return source_origin


def _resolve_strict_admin_ssh_session(
    *,
    connection: HTTPConnection,
    admin: AdminUserModel,
    current_realm: RealmResolution,
    auth_service: AuthService,
) -> _AuthenticatedAdminSshSession:
    """Bind privileged SSH to one non-legacy admin access-token and device cookie."""

    realm = current_realm.auth_realm
    token = get_access_token_cookie(connection.cookies, realm.cookie_namespace)
    device_cookie = get_web_device_cookie(connection.cookies)
    if token is None or device_cookie is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")
    try:
        claims = auth_service.decode_token(token, audience=realm.audience)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied") from exc

    jti = claims.get("jti")
    expires_at_raw = claims.get("exp")
    if (
        realm.realm_type != "admin"
        or realm.status != "active"
        or admin.auth_realm_id != realm.id
        or claims.get("type") != "access"
        or claims.get("sub") != str(admin.id)
        or claims.get("principal_type") != PrincipalClass.ADMIN.value
        or claims.get("realm_id") != str(realm.id)
        or claims.get("realm_key") != realm.realm_key
        or claims.get("scope_family") != "admin"
        or not isinstance(jti, str)
        or not jti
        or isinstance(expires_at_raw, bool)
        or not isinstance(expires_at_raw, int | float)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")
    access_expires_at = datetime.fromtimestamp(float(expires_at_raw), tz=UTC)
    if access_expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")
    return _AuthenticatedAdminSshSession(
        admin=admin,
        auth_realm_id=realm.id,
        access_jti=jti,
        access_expires_at=access_expires_at,
        device_cookie=device_cookie,
    )


async def _authenticate_websocket_admin_session(
    websocket: WebSocket,
    *,
    redis_client: redis.Redis,
) -> _AuthenticatedAdminSshSession:
    """Authenticate the WebSocket cookie session before consuming a local ticket."""

    request = cast(Request, websocket)
    async with AsyncSessionLocal() as db:
        current_realm = await get_request_admin_realm(request=request, db=db)
        auth_service = get_auth_service()
        admin = await _resolve_current_admin_user_for_realm(
            request=request,
            credentials=None,
            db=db,
            auth_service=auth_service,
            redis_client=redis_client,
            current_realm=current_realm,
        )
        session = _resolve_strict_admin_ssh_session(
            connection=websocket,
            admin=admin,
            current_realm=current_realm,
            auth_service=auth_service,
        )
        _require_trusted_admin(admin)
        return session


def _reason_audit_fields(reason: str) -> dict[str, str | int]:
    normalized = reason.strip()
    return {
        "reason_length": len(normalized),
        "reason_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }


def _map_upstream_rest_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RemnawaveNodeSshScopedBrokerUnavailable):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node SSH capability is unavailable")
    if isinstance(exc, HTTPStatusError) and exc.response.status_code == status.HTTP_404_NOT_FOUND:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Remnawave node not found")
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Remnawave Node SSH is unavailable")


async def _commit_audit(
    *,
    db: AsyncSession,
    action: str,
    resource_id: UUID,
    actor: AdminUserModel,
    request: Request,
    details: dict[str, object],
) -> None:
    await write_required_admin_audit_entry(
        db=db,
        action=action,
        resource_type="remnawave_node",
        resource_id=resource_id,
        actor=actor,
        request=request,
        details=details,
    )
    await db.commit()


@router.post(
    "/nodes/{node_uuid}/tickets",
    response_model=AdminRemnawaveNodeSshTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def issue_remnawave_node_ssh_ticket(
    node_uuid: UUID,
    body: AdminRemnawaveNodeSshTicketRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_permission(Permission.NODE_SSH_EXECUTE)),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
    gateway: RemnawaveNodeSshGateway = Depends(get_remnawave_node_ssh_gateway),
) -> AdminRemnawaveNodeSshTicketResponse:
    _require_trusted_admin(current_admin)
    origin = _canonical_admin_origin(request)
    _require_allowed_node(node_uuid)
    ssh_session = _resolve_strict_admin_ssh_session(
        connection=request,
        admin=current_admin,
        current_realm=current_realm,
        auth_service=auth_service,
    )
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_admin.id),
        principal_class=get_principal_type_for_realm(current_realm),
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action=f"remnawave_node_ssh:issue:{node_uuid}",
    )
    store = RemnawaveNodeSshTicketStore(redis_client)
    auth_session_binding = store.build_session_binding(
        admin_id=current_admin.id,
        auth_realm_id=ssh_session.auth_realm_id,
        access_jti=ssh_session.access_jti,
        device_cookie=ssh_session.device_cookie,
    )
    try:
        issue_ip = str(ip_address(resolve_client_ip(request).ip))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied") from exc

    try:
        upstream_ticket = await gateway.create_ticket(
            str(node_uuid),
            actor_reference=str(current_admin.id),
        )
    except (
        HTTPStatusError,
        RequestError,
        RemnawaveNodeSshScopedBrokerUnavailable,
        ValidationError,
        ValueError,
    ) as exc:
        raise _map_upstream_rest_error(exc) from exc

    ttl_seconds = min(settings.remnawave_node_ssh_ticket_ttl_seconds, upstream_ticket.expires_in_seconds)
    record = await store.create(
        admin_id=current_admin.id,
        auth_realm_id=ssh_session.auth_realm_id,
        auth_session_binding=auth_session_binding,
        node_uuid=node_uuid,
        origin=origin,
        issue_ip=issue_ip,
        upstream_ticket=upstream_ticket.ticket,
        upstream_credential=upstream_ticket.credential,
        upstream_path=upstream_ticket.path,
        upstream_protocol=upstream_ticket.protocol,
        ttl_seconds=ttl_seconds,
    )
    try:
        await _commit_audit(
            db=db,
            action="remnawave.node_ssh.ticket_issued",
            resource_id=node_uuid,
            actor=current_admin,
            request=request,
            details={
                "ticket_reference": record.reference,
                "expires_in_seconds": ttl_seconds,
                "fresh_auth_method": "passkey",
                **_reason_audit_fields(body.reason),
            },
        )
    except Exception:
        await store.revoke_unchecked(record.ticket_id)
        raise

    return AdminRemnawaveNodeSshTicketResponse(
        ticket=record.ticket_id,
        node_uuid=node_uuid,
        websocket_path=LOCAL_SSH_WS_PATH,
        websocket_protocol=LOCAL_SSH_WS_PROTOCOL,
        expires_in_seconds=ttl_seconds,
    )


@router.post(
    "/tickets/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_remnawave_node_ssh_ticket(
    body: AdminRemnawaveNodeSshRevokeRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_permission(Permission.NODE_SSH_EXECUTE)),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Response:
    _require_trusted_admin(current_admin)
    _canonical_admin_origin(request)
    revoked = await RemnawaveNodeSshTicketStore(redis_client).revoke(
        body.ticket,
        expected_admin_id=current_admin.id,
    )
    if revoked is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node SSH ticket not found")
    record, ticket_state = revoked
    await _commit_audit(
        db=db,
        action="remnawave.node_ssh.ticket_revoked",
        resource_id=UUID(record.node_uuid),
        actor=current_admin,
        request=request,
        details={
            "ticket_reference": record.reference,
            "ticket_state": ticket_state,
            **_reason_audit_fields(body.reason),
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tickets/security-revoke",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def security_revoke_remnawave_node_ssh_ticket(
    body: AdminRemnawaveNodeSshRevokeRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_permission(Permission.MANAGE_ADMINS)),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> Response:
    """Allow an active security supervisor to terminate any pending/active ticket."""

    _require_security_supervisor(current_admin)
    _canonical_admin_origin(request)
    revoked = await RemnawaveNodeSshTicketStore(redis_client).revoke_as_supervisor(body.ticket)
    if revoked is None:
        # The same response covers missing, already-revoked, corrupt, and replayed
        # ticket values so this boundary is not a session-existence oracle.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node SSH ticket not found")
    record, ticket_state = revoked
    await _commit_audit(
        db=db,
        action="remnawave.node_ssh.ticket_security_revoked",
        resource_id=UUID(record.node_uuid),
        actor=current_admin,
        request=request,
        details={
            "ticket_reference": record.reference,
            "ticket_state": ticket_state,
            "target_admin_reference": hashlib.sha256(record.admin_id.encode("ascii")).hexdigest()[:16],
            **_reason_audit_fields(body.reason),
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/vault/evaluate",
    response_model=AdminRemnawaveNodeSshVaultEvaluateResponse,
)
async def evaluate_remnawave_node_ssh_vault(
    body: AdminRemnawaveNodeSshVaultEvaluateRequest,
    request: Request,
    current_admin: AdminUserModel = Depends(require_permission(Permission.NODE_SSH_EXECUTE)),
    current_realm: RealmResolution = Depends(get_request_admin_realm),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    gateway: RemnawaveNodeSshGateway = Depends(get_remnawave_node_ssh_gateway),
) -> AdminRemnawaveNodeSshVaultEvaluateResponse:
    _require_trusted_admin(current_admin)
    _canonical_admin_origin(request)
    await enforce_passkey_fresh_auth(
        request=request,
        redis_client=redis_client,
        principal_subject=str(current_admin.id),
        principal_class=get_principal_type_for_realm(current_realm),
        auth_realm_id=str(current_realm.auth_realm.id),
        realm_key=current_realm.realm_key,
        action="remnawave_node_ssh:vault:evaluate",
    )
    try:
        evaluation = await gateway.evaluate_vault(body.blinded)
    except (
        HTTPStatusError,
        RequestError,
        RemnawaveNodeSshScopedBrokerUnavailable,
        ValidationError,
        ValueError,
    ) as exc:
        raise _map_upstream_rest_error(exc) from exc
    await _commit_audit(
        db=db,
        action="remnawave.node_ssh.vault_evaluated",
        resource_id=current_admin.id,
        actor=current_admin,
        request=request,
        details={"fresh_auth_method": "passkey"},
    )
    return AdminRemnawaveNodeSshVaultEvaluateResponse(evaluated=evaluation.evaluated)


@dataclass(slots=True)
class _RelayStats:
    browser_messages: int = 0
    browser_bytes: int = 0
    upstream_messages: int = 0
    upstream_bytes: int = 0


def _message_size(message: str | bytes) -> int:
    return len(message.encode("utf-8")) if isinstance(message, str) else len(message)


async def _browser_to_upstream(websocket: WebSocket, upstream, stats: _RelayStats) -> str:
    while True:
        event = await websocket.receive()
        if event["type"] == "websocket.disconnect":
            return "browser_disconnected"
        message = event.get("text") if event.get("text") is not None else event.get("bytes")
        if not isinstance(message, str | bytes):
            continue
        size = _message_size(message)
        if size > MAX_SSH_WS_MESSAGE_BYTES:
            raise ValueError("browser_message_too_large")
        stats.browser_messages += 1
        stats.browser_bytes += size
        await upstream.send(message)


async def _upstream_to_browser(websocket: WebSocket, upstream, stats: _RelayStats) -> str:
    async for message in upstream:
        if not isinstance(message, str | bytes):
            raise ValueError("upstream_message_type_invalid")
        size = _message_size(message)
        if size > MAX_SSH_WS_MESSAGE_BYTES:
            raise ValueError("upstream_message_too_large")
        stats.upstream_messages += 1
        stats.upstream_bytes += size
        if isinstance(message, str):
            await websocket.send_text(message)
        else:
            await websocket.send_bytes(message)
    return "upstream_disconnected"


async def _is_active_session_policy_allowed(
    *,
    record: RemnawaveNodeSshTicketRecord,
    session: _AuthenticatedAdminSshSession,
    redis_client: redis.Redis,
) -> bool:
    if datetime.now(UTC) >= session.access_expires_at:
        return False
    if await JWTRevocationService(redis_client).is_revoked(session.access_jti):
        return False

    async with AsyncSessionLocal() as db:
        actor = await AdminUserRepository(db).get_by_id(UUID(record.admin_id))
        realm = await db.get(AuthRealmModel, UUID(record.auth_realm_id))
        if (
            actor is None
            or realm is None
            or realm.realm_type != "admin"
            or realm.status != "active"
            or actor.auth_realm_id != realm.id
            or session.admin.id != actor.id
            or session.auth_realm_id != realm.id
        ):
            return False
        try:
            _require_trusted_admin(actor)
            _require_allowed_node(UUID(record.node_uuid))
        except HTTPException:
            return False
    return True


async def _wait_for_revocation(
    store: RemnawaveNodeSshTicketStore,
    record: RemnawaveNodeSshTicketRecord,
    session: _AuthenticatedAdminSshSession,
    redis_client: redis.Redis,
) -> str:
    # Shared Redis state is the cross-process revocation signal. The same
    # bounded poll also rechecks DB/config/token policy, so deactivation,
    # allowlist removal, realm disablement, logout, and supervisor revocation
    # terminate an already-open relay promptly.
    while await store.is_session_active(record.ticket_id):  # noqa: ASYNC110
        if not await _is_active_session_policy_allowed(
            record=record,
            session=session,
            redis_client=redis_client,
        ):
            await store.revoke_unchecked(record.ticket_id)
            return "policy_revoked"
        await asyncio.sleep(settings.remnawave_node_ssh_revocation_poll_seconds)
    return "revoked"


async def _relay_session(
    websocket: WebSocket,
    upstream,
    store: RemnawaveNodeSshTicketStore,
    record: RemnawaveNodeSshTicketRecord,
    session: _AuthenticatedAdminSshSession,
    redis_client: redis.Redis,
    stats: _RelayStats,
) -> str:
    tasks = {
        asyncio.create_task(_browser_to_upstream(websocket, upstream, stats)),
        asyncio.create_task(_upstream_to_browser(websocket, upstream, stats)),
        asyncio.create_task(_wait_for_revocation(store, record, session, redis_client)),
    }
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    try:
        completed = next(iter(done))
        return completed.result()
    finally:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


def _extract_local_ticket(websocket: WebSocket) -> str:
    protocols = [part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    if len(protocols) != 2 or protocols[0] != LOCAL_SSH_WS_PROTOCOL:
        raise RemnawaveNodeSshTicketError("node_ssh_protocol_invalid")
    return protocols[1]


async def _audit_websocket_event(
    *,
    websocket: WebSocket,
    record: RemnawaveNodeSshTicketRecord,
    action: str,
    details: dict[str, object],
    enforce_access: bool,
) -> AdminUserModel:
    async with AsyncSessionLocal() as db:
        actor = await AdminUserRepository(db).get_by_id(UUID(record.admin_id))
        if actor is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Node SSH access denied")
        if enforce_access:
            _require_trusted_admin(actor)
        await write_required_admin_audit_entry(
            db=db,
            action=action,
            resource_type="remnawave_node",
            resource_id=record.node_uuid,
            actor=actor,
            request=cast(Request, websocket),
            details=details,
        )
        await db.commit()
        return actor


@router.websocket("/ws")
async def proxy_remnawave_node_ssh(
    websocket: WebSocket,
    redis_client: redis.Redis = Depends(get_redis),
    gateway: RemnawaveNodeSshGateway = Depends(get_remnawave_node_ssh_gateway),
) -> None:
    store = RemnawaveNodeSshTicketStore(redis_client)
    record: RemnawaveNodeSshTicketRecord | None = None
    stats = _RelayStats()
    started_at = time.monotonic()
    outcome = "rejected"
    try:
        ssh_session = await _authenticate_websocket_admin_session(websocket, redis_client=redis_client)
        origin = _canonical_admin_origin(websocket)
        ticket_id = _extract_local_ticket(websocket)
        auth_session_binding = store.build_session_binding(
            admin_id=ssh_session.admin.id,
            auth_realm_id=ssh_session.auth_realm_id,
            access_jti=ssh_session.access_jti,
            device_cookie=ssh_session.device_cookie,
        )
        record = await store.consume(
            ticket_id,
            expected_admin_id=ssh_session.admin.id,
            expected_auth_realm_id=ssh_session.auth_realm_id,
            expected_auth_session_binding=auth_session_binding,
            expected_origin=origin,
            expected_issue_ip=resolve_client_ip(websocket).ip,
            active_ttl_seconds=settings.remnawave_node_ssh_session_max_seconds,
        )
        if not await _is_active_session_policy_allowed(
            record=record,
            session=ssh_session,
            redis_client=redis_client,
        ):
            await store.revoke_unchecked(record.ticket_id)
            raise RemnawaveNodeSshTicketError("node_ssh_session_policy_denied")
        await _audit_websocket_event(
            websocket=websocket,
            record=record,
            action="remnawave.node_ssh.ticket_used",
            details={"ticket_reference": record.reference},
            enforce_access=True,
        )
        upstream_ticket = RemnawaveUpstreamSshTicket.model_validate(
            {
                "ticket": record.upstream_ticket,
                "credential": record.upstream_credential,
                "path": record.upstream_path,
                "protocol": record.upstream_protocol,
                # This reconstructs the already-issued opaque material after
                # the local atomic consume. The strict upstream DTO describes
                # the broker's fixed issuance contract; actual remaining life
                # is enforced by the upstream one-time store and our local TTL.
                "expiresInSeconds": 10,
            }
        )
        async with gateway.connect(upstream_ticket) as upstream:
            await websocket.accept(subprotocol=LOCAL_SSH_WS_PROTOCOL)
            await _audit_websocket_event(
                websocket=websocket,
                record=record,
                action="remnawave.node_ssh.session_started",
                details={"ticket_reference": record.reference},
                enforce_access=True,
            )
            async with asyncio.timeout(settings.remnawave_node_ssh_session_max_seconds):
                outcome = await _relay_session(
                    websocket,
                    upstream,
                    store,
                    record,
                    ssh_session,
                    redis_client,
                    stats,
                )
    except TimeoutError:
        outcome = "max_duration_reached"
    except (ConnectionClosed, InvalidHandshake):
        outcome = "upstream_disconnected"
    except (HTTPException, RemnawaveNodeSshTicketError):
        outcome = "access_rejected"
    except (OSError, ValueError):
        outcome = "proxy_failed"
    finally:
        if record is not None:
            try:
                await store.finish_session(record)
            except Exception as exc:
                logger.error(
                    "Failed to clear Remnawave Node SSH active-session marker",
                    extra={"error_type": type(exc).__name__, "ticket_reference": record.reference},
                )
            try:
                await _audit_websocket_event(
                    websocket=websocket,
                    record=record,
                    action="remnawave.node_ssh.session_closed",
                    details={
                        "ticket_reference": record.reference,
                        "outcome": outcome,
                        "duration_seconds": max(0, round(time.monotonic() - started_at)),
                        "browser_messages": stats.browser_messages,
                        "browser_bytes": stats.browser_bytes,
                        "upstream_messages": stats.upstream_messages,
                        "upstream_bytes": stats.upstream_bytes,
                    },
                    enforce_access=False,
                )
            except Exception as exc:
                logger.error(
                    "Failed to persist Remnawave Node SSH close audit",
                    extra={"error_type": type(exc).__name__, "ticket_reference": record.reference},
                )
        if websocket.application_state in {WebSocketState.CONNECTING, WebSocketState.CONNECTED}:
            close_code = {
                "browser_disconnected": status.WS_1000_NORMAL_CLOSURE,
                "max_duration_reached": status.WS_1000_NORMAL_CLOSURE,
                "revoked": status.WS_1008_POLICY_VIOLATION,
                "policy_revoked": status.WS_1008_POLICY_VIOLATION,
                "access_rejected": status.WS_1008_POLICY_VIOLATION,
            }.get(outcome, status.WS_1011_INTERNAL_ERROR)
            await websocket.close(code=close_code)
