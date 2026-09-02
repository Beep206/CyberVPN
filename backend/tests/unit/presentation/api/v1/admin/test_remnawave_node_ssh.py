from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.websockets import WebSocketState

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.domain.enums import AdminRole, PrincipalClass
from src.infrastructure.cache.passkey_fresh_auth import PasskeyFreshAuthGrantStore
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.remnawave_node_ssh_tickets import (
    RemnawaveNodeSshTicketError,
    RemnawaveNodeSshTicketStore,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.remnawave.node_ssh_gateway import RemnawaveUpstreamSshTicket
from src.presentation.api.v1.admin import remnawave_node_ssh as routes
from src.presentation.api.v1.admin.remnawave_node_ssh_schemas import (
    AdminRemnawaveNodeSshRevokeRequest,
    AdminRemnawaveNodeSshTicketRequest,
)
from src.presentation.api.v1.remnawave_status.routes import get_admin_remnawave_capabilities_and_streams
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db


@pytest.mark.parametrize(
    "schema,payload",
    [
        (AdminRemnawaveNodeSshTicketRequest, {"reason": "        "}),
        (
            AdminRemnawaveNodeSshRevokeRequest,
            {"ticket": "a" * 32, "reason": "        "},
        ),
    ],
)
def test_node_ssh_audit_reason_rejects_whitespace_only(schema, payload) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_node_ssh_audit_reason_is_normalized_before_persistence() -> None:
    request = AdminRemnawaveNodeSshTicketRequest(reason="  Approved incident response  ")

    assert request.reason == "Approved incident response"


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def set(
        self,
        key: str,
        value: object,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool:
        _ = ex
        if nx and key in self.values:
            return False
        self.values[key] = str(value)
        return True

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def getdel(self, key: str) -> str | None:
        return self.values.pop(key, None)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            deleted += int(self.values.pop(key, None) is not None)
        return deleted

    async def exists(self, key: str) -> int:
        return int(key in self.values)

    async def eval(self, _script: str, numkeys: int, *args: object) -> object | None:
        if numkeys == 2 and len(args) == 3:
            pending_key, active_key, _active_ttl = (str(item) for item in args)
            raw = self.values.pop(pending_key, None)
            if raw is not None:
                self.values[active_key] = raw
            return raw
        if numkeys == 2 and len(args) == 2:
            pending_key, active_key = (str(item) for item in args)
            for key, state in ((pending_key, "pending"), (active_key, "active")):
                raw = self.values.pop(key, None)
                if raw is not None:
                    return [raw, state]
            return None
        key, expected = (str(item) for item in args)
        if self.values.get(key) != expected:
            return 0
        await self.delete(key)
        return 1


class _FakeGateway:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, str]] = []

    async def create_ticket(self, node_uuid: str, *, actor_reference: str) -> RemnawaveUpstreamSshTicket:
        self.create_calls.append((node_uuid, actor_reference))
        return RemnawaveUpstreamSshTicket.model_validate(
            {
                "ticket": "t" * 43,
                "credential": "c" * 43,
                "path": "/api/cybervpn/node-ssh/ws",
                "protocol": "rw-cybervpn",
                "expiresInSeconds": 10,
            }
        )


class _RelayGateway:
    def __init__(self) -> None:
        self.connected_tickets: list[RemnawaveUpstreamSshTicket] = []

    def connect(self, ticket: RemnawaveUpstreamSshTicket):
        self.connected_tickets.append(ticket)

        class _Connection:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, *_args):
                return None

        return _Connection()


def _admin(
    *,
    admin_id: UUID | None = None,
    role: AdminRole = AdminRole.ADMIN,
    auth_realm_id: UUID | None = None,
) -> AdminUserModel:
    return AdminUserModel(
        id=admin_id or uuid4(),
        auth_realm_id=auth_realm_id,
        login=f"ssh-{uuid4()}",
        role=role.value,
        is_active=True,
        deleted_at=None,
        totp_enabled=True,
    )


def _realm(realm_type: str = "admin") -> RealmResolution:
    realm = AuthRealmModel(
        id=uuid4(),
        realm_key=f"{realm_type}-{uuid4()}",
        realm_type=realm_type,
        display_name=realm_type,
        audience=f"cybervpn-{realm_type}-{uuid4()}",
        cookie_namespace=realm_type,
        status="active",
        is_default=False,
    )
    return RealmResolution(auth_realm=realm, source="test")


def _request(
    *,
    grant_id: str | None = None,
    origin: str = "http://localhost:3001",
    admin: AdminUserModel | None = None,
    realm: RealmResolution | None = None,
    auth_service: AuthService | None = None,
    access_jti: str = "node-ssh-access-session-a",
    device_cookie: str = "d" * 43,
) -> Request:
    headers = [(b"origin", origin.encode("ascii"))]
    if grant_id is not None:
        headers.append((b"x-fresh-auth-grant-id", grant_id.encode("ascii")))
    if admin is not None and realm is not None and auth_service is not None:
        admin.auth_realm_id = realm.auth_realm.id
        token, _jti, _expires_at = auth_service.create_access_token(
            subject=str(admin.id),
            role=admin.role,
            jti=access_jti,
            audience=realm.auth_realm.audience,
            principal_type=PrincipalClass.ADMIN.value,
            realm_id=str(realm.auth_realm.id),
            realm_key=realm.realm_key,
            scope_family="admin",
        )
        cookie = f"access_token={token}; {settings.web_device_cookie_name}={device_cookie}"
        headers.append((b"cookie", cookie.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/admin/remnawave/node-ssh/tickets",
            "raw_path": b"/api/v1/admin/remnawave/node-ssh/tickets",
            "query_string": b"",
            "headers": headers,
            "client": ("203.0.113.10", 54321),
            "server": ("admin.cyber-vpn.net", 443),
        }
    )


def _enable_ssh(
    monkeypatch,
    *,
    admin_ids: list[UUID],
    node_ids: list[UUID],
    scoped_broker_available: bool = True,
) -> None:
    monkeypatch.setattr(settings, "remnawave_node_ssh_enabled", True)
    monkeypatch.setattr(settings, "remnawave_node_ssh_broker_url", "http://remnawave-ssh-proxy:8080")
    monkeypatch.setattr(
        settings,
        "remnawave_node_ssh_broker_secret",
        SecretStr("a" * 128 if scoped_broker_available else ""),
    )
    monkeypatch.setattr(settings, "remnawave_node_ssh_trusted_admin_ids", ",".join(map(str, admin_ids)))
    monkeypatch.setattr(settings, "remnawave_node_ssh_allowed_node_ids", ",".join(map(str, node_ids)))
    monkeypatch.setattr(settings, "passkey_enabled", True)
    monkeypatch.setattr(settings, "passkey_admin_enabled", True)
    monkeypatch.setattr(settings, "remnawave_token", SecretStr("server-only-upstream-token"))


@pytest.mark.unit
def test_node_ssh_is_fail_closed_without_scoped_upstream_broker(monkeypatch) -> None:
    admin = _admin()
    node_id = uuid4()
    _enable_ssh(
        monkeypatch,
        admin_ids=[admin.id],
        node_ids=[node_id],
        scoped_broker_available=False,
    )

    assert routes.is_remnawave_node_ssh_available_for(admin) is False
    with pytest.raises(HTTPException) as blocked:
        routes._require_trusted_admin(admin)
    assert blocked.value.status_code == 404


@pytest.mark.unit
def test_capability_is_true_only_for_explicitly_trusted_active_admin(monkeypatch) -> None:
    trusted = _admin()
    untrusted = _admin()
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[trusted.id], node_ids=[node_id])

    assert routes.is_remnawave_node_ssh_available_for(trusted) is True
    assert routes.is_remnawave_node_ssh_available_for(untrusted) is False
    assert routes.is_remnawave_node_ssh_available_for(_admin(role=AdminRole.OPERATOR)) is False

    trusted.is_active = False
    assert routes.is_remnawave_node_ssh_available_for(trusted) is False


@pytest.mark.unit
async def test_admin_status_reports_node_ssh_for_current_trusted_admin_only(monkeypatch) -> None:
    trusted = _admin()
    untrusted = _admin()
    _enable_ssh(monkeypatch, admin_ids=[trusted.id], node_ids=[uuid4()])
    monkeypatch.setattr(settings, "remnawave_stream_ingestion_enabled", False)
    empty_rows = SimpleNamespace(
        all=lambda: [],
        scalar_one=lambda: 0,
        scalars=lambda: SimpleNamespace(all=lambda: []),
    )
    client = AsyncMock()
    client.get.return_value = {"version": "3.4.3"}

    trusted_db = AsyncMock()
    trusted_db.execute.return_value = empty_rows
    trusted_response = await get_admin_remnawave_capabilities_and_streams(
        current_user=trusted,
        db=trusted_db,
        client=client,
    )

    untrusted_db = AsyncMock()
    untrusted_db.execute.return_value = empty_rows
    untrusted_response = await get_admin_remnawave_capabilities_and_streams(
        current_user=untrusted,
        db=untrusted_db,
        client=client,
    )

    assert trusted_response.capabilities.node_ssh is True
    assert untrusted_response.capabilities.node_ssh is False


@pytest.mark.unit
def test_disabled_boundary_is_hidden_and_admin_outside_allowlist_is_denied(monkeypatch) -> None:
    admin = _admin()
    monkeypatch.setattr(settings, "remnawave_node_ssh_enabled", False)

    with pytest.raises(HTTPException) as disabled:
        routes._require_trusted_admin(admin)
    assert disabled.value.status_code == 404

    _enable_ssh(monkeypatch, admin_ids=[uuid4()], node_ids=[uuid4()])
    with pytest.raises(HTTPException) as denied:
        routes._require_trusted_admin(admin)
    assert denied.value.status_code == 403


@pytest.mark.unit
def test_node_outside_explicit_allowlist_is_hidden(monkeypatch) -> None:
    admin = _admin()
    allowed_node = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[allowed_node])

    routes._require_allowed_node(allowed_node)
    with pytest.raises(HTTPException) as denied:
        routes._require_allowed_node(uuid4())
    assert denied.value.status_code == 404


@pytest.mark.unit
async def test_issue_requires_one_use_fresh_passkey_and_returns_only_local_ticket(monkeypatch) -> None:
    admin = _admin()
    realm = _realm()
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[node_id])
    fake_redis = _FakeRedis()
    redis_client = cast(redis.Redis, fake_redis)
    grant = await PasskeyFreshAuthGrantStore(redis_client).create(
        principal_subject=str(admin.id),
        principal_class=PrincipalClass.ADMIN.value,
        auth_realm_id=str(realm.auth_realm.id),
        realm_key=realm.realm_key,
        action=f"remnawave_node_ssh:issue:{node_id}",
    )
    gateway = _FakeGateway()
    auth_service = AuthService()
    audited: list[dict[str, object]] = []

    async def capture_audit(**kwargs: object) -> None:
        audited.append(kwargs)

    monkeypatch.setattr(routes, "_commit_audit", capture_audit)
    response = await routes.issue_remnawave_node_ssh_ticket(
        node_uuid=node_id,
        body=AdminRemnawaveNodeSshTicketRequest(reason="Approved incident response"),
        request=_request(
            grant_id=grant.grant_id,
            admin=admin,
            realm=realm,
            auth_service=auth_service,
        ),
        current_admin=admin,
        current_realm=realm,
        db=cast(AsyncSession, object()),
        redis_client=redis_client,
        auth_service=auth_service,
        gateway=cast(routes.RemnawaveNodeSshGateway, gateway),
    )

    serialized = response.model_dump_json()
    assert response.node_uuid == node_id
    assert response.websocket_path == routes.LOCAL_SSH_WS_PATH
    assert response.websocket_protocol == routes.LOCAL_SSH_WS_PROTOCOL
    assert response.ticket != "t" * 43
    assert "t" * 43 not in serialized
    assert "c" * 43 not in serialized
    assert "server-only-upstream-token" not in serialized
    assert gateway.create_calls == [(str(node_id), str(admin.id))]
    assert audited[0]["action"] == "remnawave.node_ssh.ticket_issued"
    assert f"passkey:fresh:{grant.grant_id}" not in fake_redis.values

    consumed = await RemnawaveNodeSshTicketStore(redis_client).consume(
        response.ticket,
        expected_admin_id=admin.id,
        expected_auth_realm_id=realm.auth_realm.id,
        expected_auth_session_binding=RemnawaveNodeSshTicketStore(redis_client).build_session_binding(
            admin_id=admin.id,
            auth_realm_id=realm.auth_realm.id,
            access_jti="node-ssh-access-session-a",
            device_cookie="d" * 43,
        ),
        expected_origin=routes.CANONICAL_ADMIN_ORIGIN,
        expected_issue_ip="203.0.113.10",
        active_ttl_seconds=600,
    )
    assert consumed.node_uuid == str(node_id)
    with pytest.raises(RemnawaveNodeSshTicketError, match="node_ssh_ticket_missing"):
        await RemnawaveNodeSshTicketStore(redis_client).consume(
            response.ticket,
            expected_admin_id=admin.id,
            expected_auth_realm_id=realm.auth_realm.id,
            expected_auth_session_binding=consumed.auth_session_binding,
            expected_origin=routes.CANONICAL_ADMIN_ORIGIN,
            expected_issue_ip="203.0.113.10",
            active_ttl_seconds=600,
        )


@pytest.mark.unit
async def test_websocket_consumes_once_and_reaches_strict_upstream_connect(monkeypatch) -> None:
    admin = _admin()
    realm = _realm()
    admin.auth_realm_id = realm.auth_realm.id
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[node_id])
    fake_redis = _FakeRedis()
    redis_client = cast(redis.Redis, fake_redis)
    store = RemnawaveNodeSshTicketStore(redis_client)
    session = routes._AuthenticatedAdminSshSession(
        admin=admin,
        auth_realm_id=realm.auth_realm.id,
        access_jti="node-ssh-relay-session",
        access_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        device_cookie="d" * 43,
    )
    binding = store.build_session_binding(
        admin_id=admin.id,
        auth_realm_id=realm.auth_realm.id,
        access_jti=session.access_jti,
        device_cookie=session.device_cookie,
    )
    record = await store.create(
        admin_id=admin.id,
        auth_realm_id=realm.auth_realm.id,
        auth_session_binding=binding,
        node_uuid=node_id,
        origin=routes.CANONICAL_ADMIN_ORIGIN,
        issue_ip="203.0.113.10",
        upstream_ticket="u" * 43,
        upstream_credential="c" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=10,
    )

    def websocket_double():
        return SimpleNamespace(
            headers={
                "sec-websocket-protocol": f"{routes.LOCAL_SSH_WS_PROTOCOL},{record.ticket_id}",
            },
            application_state=WebSocketState.CONNECTING,
            accept=AsyncMock(),
            close=AsyncMock(),
        )

    gateway = _RelayGateway()
    audit = AsyncMock(return_value=admin)
    relay = AsyncMock(return_value="browser_disconnected")
    monkeypatch.setattr(routes, "_authenticate_websocket_admin_session", AsyncMock(return_value=session))
    monkeypatch.setattr(routes, "_canonical_admin_origin", lambda _websocket: routes.CANONICAL_ADMIN_ORIGIN)
    monkeypatch.setattr(routes, "resolve_client_ip", lambda _websocket: SimpleNamespace(ip="203.0.113.10"))
    monkeypatch.setattr(routes, "_is_active_session_policy_allowed", AsyncMock(return_value=True))
    monkeypatch.setattr(routes, "_audit_websocket_event", audit)
    monkeypatch.setattr(routes, "_relay_session", relay)

    first = websocket_double()
    await routes.proxy_remnawave_node_ssh(
        cast(routes.WebSocket, first),
        redis_client=redis_client,
        gateway=cast(routes.RemnawaveNodeSshGateway, gateway),
    )

    assert len(gateway.connected_tickets) == 1
    assert gateway.connected_tickets[0].expires_in_seconds == 10
    first.accept.assert_awaited_once_with(subprotocol=routes.LOCAL_SSH_WS_PROTOCOL)
    relay.assert_awaited_once()

    second = websocket_double()
    await routes.proxy_remnawave_node_ssh(
        cast(routes.WebSocket, second),
        redis_client=redis_client,
        gateway=cast(routes.RemnawaveNodeSshGateway, gateway),
    )

    assert len(gateway.connected_tickets) == 1
    second.accept.assert_not_awaited()
    second.close.assert_awaited_once_with(code=1008)


@pytest.mark.unit
async def test_issue_rejects_missing_fresh_auth_before_upstream_mutation(monkeypatch) -> None:
    admin = _admin()
    realm = _realm()
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[node_id])
    gateway = _FakeGateway()
    auth_service = AuthService()

    with pytest.raises(HTTPException) as rejected:
        await routes.issue_remnawave_node_ssh_ticket(
            node_uuid=node_id,
            body=AdminRemnawaveNodeSshTicketRequest(reason="Approved incident response"),
            request=_request(admin=admin, realm=realm, auth_service=auth_service),
            current_admin=admin,
            current_realm=realm,
            db=cast(AsyncSession, object()),
            redis_client=cast(redis.Redis, _FakeRedis()),
            auth_service=auth_service,
            gateway=cast(routes.RemnawaveNodeSshGateway, gateway),
        )

    assert rejected.value.status_code == 403
    assert gateway.create_calls == []


@pytest.mark.unit
async def test_ticket_owner_can_revoke_and_foreign_admin_gets_hidden_not_found(monkeypatch) -> None:
    owner = _admin()
    foreign = _admin()
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[owner.id, foreign.id], node_ids=[node_id])
    fake_redis = _FakeRedis()
    redis_client = cast(redis.Redis, fake_redis)
    record = await RemnawaveNodeSshTicketStore(redis_client).create(
        admin_id=owner.id,
        auth_realm_id=uuid4(),
        auth_session_binding="a" * 64,
        node_uuid=node_id,
        origin=routes.CANONICAL_ADMIN_ORIGIN,
        issue_ip="203.0.113.10",
        upstream_ticket="u" * 43,
        upstream_credential="c" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=15,
    )
    audited: list[dict[str, object]] = []

    async def capture_audit(**kwargs: object) -> None:
        audited.append(kwargs)

    monkeypatch.setattr(routes, "_commit_audit", capture_audit)
    body = AdminRemnawaveNodeSshRevokeRequest(ticket=record.ticket_id, reason="Incident response complete")

    with pytest.raises(HTTPException) as hidden:
        await routes.revoke_remnawave_node_ssh_ticket(
            body=body,
            request=_request(),
            current_admin=foreign,
            db=cast(AsyncSession, object()),
            redis_client=redis_client,
        )
    assert hidden.value.status_code == 404

    response = await routes.revoke_remnawave_node_ssh_ticket(
        body=body,
        request=_request(),
        current_admin=owner,
        db=cast(AsyncSession, object()),
        redis_client=redis_client,
    )
    assert response.status_code == 204
    assert audited[0]["action"] == "remnawave.node_ssh.ticket_revoked"


@pytest.mark.unit
@pytest.mark.parametrize("realm_type", ["partner", "customer"])
async def test_partner_and_customer_realms_cannot_call_direct_admin_ssh_url(monkeypatch, realm_type: str) -> None:
    admin = _admin()
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[node_id])
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def current_user_override() -> AdminUserModel:
        return admin

    async def realm_override() -> RealmResolution:
        return _realm(realm_type)

    async def db_override():
        yield cast(AsyncSession, object())

    async def redis_override():
        yield cast(redis.Redis, _FakeRedis())

    app.dependency_overrides[get_current_active_user] = current_user_override
    app.dependency_overrides[get_request_admin_realm] = realm_override
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_redis] = redis_override
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://admin.cyber-vpn.net") as client:
        response = await client.post(
            f"/api/v1/admin/remnawave/node-ssh/nodes/{node_id}/tickets",
            headers={"Origin": "https://admin.cyber-vpn.net"},
            json={"reason": "Attempted direct terminal access"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin realm required"


@pytest.mark.unit
def test_stolen_ticket_without_admin_cookie_session_is_rejected(monkeypatch) -> None:
    realm = _realm()
    admin = _admin(auth_realm_id=realm.auth_realm.id)
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[uuid4()])

    with pytest.raises(HTTPException) as denied:
        routes._resolve_strict_admin_ssh_session(
            connection=_request(),
            admin=admin,
            current_realm=realm,
            auth_service=AuthService(),
        )

    assert denied.value.status_code == 403
    assert denied.value.detail == "Node SSH access denied"


@pytest.mark.unit
async def test_security_supervisor_can_revoke_foreign_session_without_existence_leak(monkeypatch) -> None:
    owner = _admin()
    ordinary_admin = _admin()
    supervisor = _admin(role=AdminRole.SUPER_ADMIN)
    node_id = uuid4()
    fake_redis = _FakeRedis()
    redis_client = cast(redis.Redis, fake_redis)
    store = RemnawaveNodeSshTicketStore(redis_client)
    record = await store.create(
        admin_id=owner.id,
        auth_realm_id=uuid4(),
        auth_session_binding="a" * 64,
        node_uuid=node_id,
        origin=routes.CANONICAL_ADMIN_ORIGIN,
        issue_ip="203.0.113.10",
        upstream_ticket="u" * 43,
        upstream_credential="c" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=15,
    )
    body = AdminRemnawaveNodeSshRevokeRequest(ticket=record.ticket_id, reason="Emergency security revoke")
    audited: list[dict[str, object]] = []

    async def capture_audit(**kwargs: object) -> None:
        audited.append(kwargs)

    monkeypatch.setattr(routes, "_commit_audit", capture_audit)
    with pytest.raises(HTTPException) as denied:
        await routes.security_revoke_remnawave_node_ssh_ticket(
            body=body,
            request=_request(),
            current_admin=ordinary_admin,
            db=cast(AsyncSession, object()),
            redis_client=redis_client,
        )
    assert denied.value.status_code == 403
    assert await store.revoke(record.ticket_id, expected_admin_id=owner.id) is not None

    second = await store.create(
        admin_id=owner.id,
        auth_realm_id=uuid4(),
        auth_session_binding="b" * 64,
        node_uuid=node_id,
        origin=routes.CANONICAL_ADMIN_ORIGIN,
        issue_ip="203.0.113.10",
        upstream_ticket="v" * 43,
        upstream_credential="d" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=15,
    )
    response = await routes.security_revoke_remnawave_node_ssh_ticket(
        body=AdminRemnawaveNodeSshRevokeRequest(ticket=second.ticket_id, reason="Emergency security revoke"),
        request=_request(),
        current_admin=supervisor,
        db=cast(AsyncSession, object()),
        redis_client=redis_client,
    )
    assert response.status_code == 204
    assert audited[0]["action"] == "remnawave.node_ssh.ticket_security_revoked"

    with pytest.raises(HTTPException) as replay:
        await routes.security_revoke_remnawave_node_ssh_ticket(
            body=AdminRemnawaveNodeSshRevokeRequest(ticket=second.ticket_id, reason="Replay attempt"),
            request=_request(),
            current_admin=supervisor,
            db=cast(AsyncSession, object()),
            redis_client=redis_client,
        )
    assert replay.value.status_code == 404


@pytest.mark.unit
async def test_active_policy_recheck_denies_admin_deactivation_or_node_allowlist_removal(monkeypatch) -> None:
    realm = _realm()
    admin = _admin(auth_realm_id=realm.auth_realm.id)
    node_id = uuid4()
    _enable_ssh(monkeypatch, admin_ids=[admin.id], node_ids=[node_id])
    fake_redis = _FakeRedis()
    redis_client = cast(redis.Redis, fake_redis)
    store = RemnawaveNodeSshTicketStore(redis_client)
    record = await store.create(
        admin_id=admin.id,
        auth_realm_id=realm.auth_realm.id,
        auth_session_binding="c" * 64,
        node_uuid=node_id,
        origin=routes.CANONICAL_ADMIN_ORIGIN,
        issue_ip="203.0.113.10",
        upstream_ticket="u" * 43,
        upstream_credential="c" * 43,
        upstream_path="/api/cybervpn/node-ssh/ws",
        upstream_protocol="rw-cybervpn",
        ttl_seconds=15,
    )
    session = routes._AuthenticatedAdminSshSession(
        admin=admin,
        auth_realm_id=realm.auth_realm.id,
        access_jti="active-session-jti",
        access_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        device_cookie="d" * 43,
    )

    class _DbContext:
        async def __aenter__(self):
            return SimpleNamespace(get=AsyncMock(return_value=realm.auth_realm))

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(routes, "AsyncSessionLocal", lambda: _DbContext())
    monkeypatch.setattr(
        routes,
        "AdminUserRepository",
        lambda _db: SimpleNamespace(get_by_id=AsyncMock(return_value=admin)),
    )

    assert (
        await routes._is_active_session_policy_allowed(
            record=record,
            session=session,
            redis_client=redis_client,
        )
        is True
    )

    monkeypatch.setattr(settings, "remnawave_node_ssh_allowed_node_ids", "")
    assert (
        await routes._is_active_session_policy_allowed(
            record=record,
            session=session,
            redis_client=redis_client,
        )
        is False
    )

    monkeypatch.setattr(settings, "remnawave_node_ssh_allowed_node_ids", str(node_id))
    admin.is_active = False
    assert (
        await routes._is_active_session_policy_allowed(
            record=record,
            session=session,
            redis_client=redis_client,
        )
        is False
    )
