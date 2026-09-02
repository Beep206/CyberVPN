from __future__ import annotations

import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from src.application.services.remnawave_create_attempts import (
    RemnawaveCreateAttemptConflict,
    RemnawaveCreateAttemptDecision,
)
from src.application.use_cases.auth_realms import RealmResolution
from src.config.settings import settings
from src.domain.enums import AdminRole
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.auth_realm_model import AuthRealmModel
from src.infrastructure.database.models.partner_model import ApiIdempotencyRecordModel
from src.infrastructure.remnawave.client import (
    RemnawaveClient,
    RemnawaveHTTPStatusError,
    RemnawaveTransportError,
)
from src.presentation.api.v1.remnawave_operator import routes
from src.presentation.api.v1.remnawave_operator.schemas import (
    CreateNodeIntegrationRequest,
    GeoCheckJobResponse,
    GeoCheckRequest,
    GeoCheckResultResponse,
    NodeIntegration,
    NodeIntegrationCollection,
    OperatorMutationReceipt,
    SetTagsRequest,
    SetTagsResponse,
    SharedList,
    SharedListMutationRequest,
    SharedListNameRequest,
    Snippet,
    SnippetCollection,
    SnippetMutationRequest,
    SnippetNameRequest,
    TagResource,
    UpdateNodeIntegrationRequest,
    UpstreamTagsResponse,
)
from src.presentation.dependencies import get_remnawave_client
from src.presentation.dependencies.auth import get_current_active_user
from src.presentation.dependencies.auth_realms import get_request_admin_realm
from src.presentation.dependencies.database import get_db


class _AttemptServiceFake:
    """Small stateful fake that preserves the production stop-before-retry state machine."""

    def __init__(self, *, should_mutate: bool = True, status: str = "pending") -> None:
        self.record = cast(
            ApiIdempotencyRecordModel,
            SimpleNamespace(
                id=uuid4(),
                status=status,
                response_payload={},
            ),
        )
        self._first_should_mutate = should_mutate
        self.begin_calls: list[dict[str, object]] = []
        self.completed_references: list[dict[str, str | int | bool]] = []
        self.reconciliation_marks = 0
        self.rejected_codes: list[str] = []

    async def begin(self, **kwargs: object) -> RemnawaveCreateAttemptDecision:
        self.begin_calls.append(kwargs)
        should_mutate = self._first_should_mutate and len(self.begin_calls) == 1
        return RemnawaveCreateAttemptDecision(record=self.record, should_mutate=should_mutate)

    async def stage_reconciliation_required(self, record: ApiIdempotencyRecordModel) -> None:
        assert record is self.record
        record.status = "reconciliation_required"
        record.response_payload = {}
        self.reconciliation_marks += 1

    async def mark_completed_reference(
        self,
        record: ApiIdempotencyRecordModel,
        *,
        reference: dict[str, str | int | bool],
    ) -> None:
        assert record is self.record
        record.status = "completed"
        record.response_payload = dict(reference)
        self.completed_references.append(dict(reference))

    async def stage_rejected(self, record: ApiIdempotencyRecordModel, *, error_code: str) -> None:
        assert record is self.record
        record.status = "rejected"
        record.response_payload = {"error_code": error_code}
        self.rejected_codes.append(error_code)

    @staticmethod
    def completed_reference(record: ApiIdempotencyRecordModel) -> dict[str, str | int | bool] | None:
        if record.status != "completed":
            return None
        return cast(dict[str, str | int | bool], record.response_payload)


def _request(path: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 443),
        }
    )


def _db() -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    return cast(AsyncSession, session)


def _actor() -> AdminUserModel:
    return cast(
        AdminUserModel,
        SimpleNamespace(
            id=uuid4(),
            role=AdminRole.ADMIN.value,
            totp_enabled=True,
        ),
    )


def _install_attempt_service(monkeypatch: pytest.MonkeyPatch, service: _AttemptServiceFake) -> None:
    monkeypatch.setattr(
        routes,
        "RemnawaveMutationAttemptService",
        lambda _session, *, resource_type: service,
    )


def _json_response(response: httpx.Response | Any) -> dict[str, Any]:
    if isinstance(response, httpx.Response):
        return cast(dict[str, Any], response.json())
    return cast(dict[str, Any], json.loads(response.body))


@pytest.mark.unit
async def test_stale_operator_replay_reports_committed_completion_without_reconciliation_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake(should_mutate=False)

    async def refresh_terminal(record: ApiIdempotencyRecordModel) -> None:
        record.status = "completed"
        record.response_payload = {"resource_uuid": str(uuid4())}

    monkeypatch.setattr(attempt, "stage_reconciliation_required", refresh_terminal)

    outcome = await routes._mark_reconciliation_required(
        cast(Any, attempt),
        attempt.record,
        resource_kind="node-integration",
    )

    assert outcome.receipt is not None
    assert outcome.receipt.state == "accepted"
    assert attempt.record.status == "completed"


def _operator_app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    role: AdminRole,
    client: RemnawaveClient,
    realm_type: str | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    session = _db()

    async def current_user() -> AdminUserModel:
        return cast(
            AdminUserModel,
            SimpleNamespace(role=role.value, totp_enabled=True, id=uuid4()),
        )

    async def admin_realm() -> RealmResolution | object:
        if realm_type is None:
            # A non-RealmResolution object is the established unit-test sentinel.
            return object()
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

    async def remnawave_client() -> RemnawaveClient:
        return client

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    monkeypatch.setattr(settings, "admin_2fa_required", False)
    app.dependency_overrides[get_current_active_user] = current_user
    app.dependency_overrides[get_request_admin_realm] = admin_realm
    app.dependency_overrides[get_remnawave_client] = remnawave_client
    app.dependency_overrides[get_db] = database
    return app


@pytest.mark.unit
def test_operator_openapi_is_namespaced_and_every_mutation_requires_bounded_idempotency_key() -> None:
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    schema = app.openapi()
    prefix = "/api/v1/admin/remnawave-operator"

    expected_operations = {
        f"{prefix}/tags/{{resource}}": {"get", "patch"},
        f"{prefix}/geocheck/nodes/{{node_uuid}}": {"post"},
        f"{prefix}/geocheck/jobs/{{job_id}}": {"get"},
        f"{prefix}/node-integrations": {"get", "post", "patch"},
        f"{prefix}/node-integrations/{{integration_uuid}}": {"delete"},
        f"{prefix}/shared-lists": {"get", "post", "patch", "delete"},
        f"{prefix}/shared-lists/by-name": {"get"},
        f"{prefix}/shared-lists/actions/sync": {"post"},
        f"{prefix}/snippets": {"get", "post", "patch", "delete"},
        f"{prefix}/snippets/actions/sync": {"post"},
    }
    assert set(schema["paths"]) == set(expected_operations)

    for path, operations in expected_operations.items():
        assert set(schema["paths"][path]) == operations
        for method in operations - {"get"}:
            parameters = {
                parameter["name"]: parameter for parameter in schema["paths"][path][method].get("parameters", [])
            }
            idempotency = parameters["Idempotency-Key"]
            assert idempotency["in"] == "header"
            assert idempotency["required"] is True
            assert idempotency["schema"]["minLength"] == 8
            assert idempotency["schema"]["maxLength"] == 160
            assert idempotency["schema"]["pattern"] == "^[A-Za-z0-9._:-]+$"


@pytest.mark.unit
@pytest.mark.parametrize(
    "role",
    [AdminRole.OPERATOR, AdminRole.FINANCE, AdminRole.SUPPORT, AdminRole.VIEWER],
)
async def test_non_admin_roles_are_denied_on_direct_read_and_mutation_urls_before_provider_io(
    monkeypatch: pytest.MonkeyPatch,
    role: AdminRole,
) -> None:
    provider = AsyncMock(spec=RemnawaveClient)
    app = _operator_app(monkeypatch, role=role, client=provider)
    integration_uuid = uuid4()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        responses = [
            await client.get("/api/v1/admin/remnawave-operator/tags/users"),
            await client.post(
                "/api/v1/admin/remnawave-operator/node-integrations",
                headers={"Idempotency-Key": "role-denial-1"},
                json={"name": "prometheus", "config": {"url": "https://metrics.invalid"}},
            ),
            await client.request(
                "DELETE",
                "/api/v1/admin/remnawave-operator/shared-lists",
                headers={"Idempotency-Key": "role-denial-2"},
                json={"name": "blocked/domains"},
            ),
            await client.delete(
                f"/api/v1/admin/remnawave-operator/node-integrations/{integration_uuid}",
                headers={"Idempotency-Key": "role-denial-3"},
            ),
        ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    provider.get_validated.assert_not_awaited()
    provider.post_validated.assert_not_awaited()
    provider.patch_validated.assert_not_awaited()
    provider.delete_validated.assert_not_awaited()


@pytest.mark.unit
async def test_admin_role_from_partner_realm_is_denied_on_direct_operator_url_before_provider_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AsyncMock(spec=RemnawaveClient)
    app = _operator_app(
        monkeypatch,
        role=AdminRole.ADMIN,
        client=provider,
        realm_type="partner",
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/remnawave-operator/node-integrations")

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin realm required"}
    provider.get_validated.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize("job_id", ["../secret", "job?next", "job#fragment", "job\\name", "job/name", "has space"])
async def test_geocheck_job_id_rejects_path_or_query_metacharacters_before_provider_io(job_id: str) -> None:
    provider = AsyncMock(spec=RemnawaveClient)

    with pytest.raises(HTTPException) as caught:
        await routes.get_geocheck_result(
            job_id=job_id,
            _current_user=_actor(),
            client=provider,
        )

    assert caught.value.status_code == 422
    provider.get_validated.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"uuid": str(uuid4()), "name": None},
        {"uuid": str(uuid4()), "config": None},
        {"uuid": str(uuid4()), "restartNodes": None},
    ],
)
def test_integration_update_rejects_explicit_null_for_non_nullable_upstream_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        UpdateNodeIntegrationRequest.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "idempotency_key",
    [None, "short", "contains whitespace", "x" * 161],
)
async def test_invalid_idempotency_key_is_rejected_before_provider_io(
    monkeypatch: pytest.MonkeyPatch,
    idempotency_key: str | None,
) -> None:
    provider = AsyncMock(spec=RemnawaveClient)
    app = _operator_app(monkeypatch, role=AdminRole.ADMIN, client=provider)
    headers = {} if idempotency_key is None else {"Idempotency-Key": idempotency_key}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/admin/remnawave-operator/tags/subscription-templates",
            headers=headers,
            json={"uuid": str(uuid4()), "tags": ["PREMIUM"]},
        )

    assert response.status_code == 422
    provider.patch_validated.assert_not_awaited()
    provider.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_reused_idempotency_key_with_different_payload_returns_conflict_before_provider_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MagicMock()
    service.begin = AsyncMock(
        side_effect=RemnawaveCreateAttemptConflict("same key was already bound to a different request hash")
    )
    monkeypatch.setattr(
        routes,
        "RemnawaveMutationAttemptService",
        lambda _session, *, resource_type: service,
    )
    provider = AsyncMock(spec=RemnawaveClient)

    with pytest.raises(HTTPException) as exc_info:
        await routes.set_tags(
            resource="subscription-templates",
            body=SetTagsRequest(uuid=uuid4(), tags=["PREMIUM"]),
            request=_request(
                "/api/v1/admin/remnawave-operator/tags/subscription-templates",
                method="PATCH",
            ),
            idempotency_key="already-used-key-1",
            current_user=_actor(),
            db=_db(),
            client=provider,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {"code": "remnawave_operator_idempotency_conflict"}
    provider.patch_validated.assert_not_awaited()
    provider.get_validated.assert_not_awaited()


@pytest.mark.unit
async def test_tag_reads_and_mutations_use_exact_343_resource_paths_and_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    resource_uuid = uuid4()
    provider.get_validated.return_value = UpstreamTagsResponse(tags=["PREMIUM", "RU"])
    provider.patch_validated.return_value = SetTagsResponse(
        uuid=resource_uuid,
        tags=["PREMIUM"],
    )

    listed = await routes.list_tags(
        resource=cast(TagResource, "nodes"),
        _current_user=_actor(),
        client=provider,
    )
    updated = await routes.set_tags(
        resource="subscription-templates",
        body=SetTagsRequest(uuid=resource_uuid, tags=["PREMIUM"]),
        request=_request(
            "/api/v1/admin/remnawave-operator/tags/subscription-templates",
            method="PATCH",
        ),
        idempotency_key="subscription-template-tags-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert listed.resource == "nodes"
    assert listed.tags == ["PREMIUM", "RU"]
    assert updated == SetTagsResponse(uuid=resource_uuid, tags=["PREMIUM"])
    provider.get_validated.assert_awaited_once_with("/nodes/tags", UpstreamTagsResponse)
    provider.patch_validated.assert_awaited_once_with(
        "/subscription-templates/tags",
        SetTagsResponse,
        json={"uuid": str(resource_uuid), "tags": ["PREMIUM"]},
    )
    assert attempt.completed_references == [{"resource_uuid": str(resource_uuid), "tag_count": 1}]


@pytest.mark.unit
async def test_transport_ambiguity_latches_then_exact_integration_readback_settles_without_second_mutation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    audit = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    provider = AsyncMock(spec=RemnawaveClient)
    provider.post_validated.side_effect = RemnawaveTransportError()
    secret_config = {"apiToken": "must-not-enter-receipt-or-audit", "url": "https://metrics.invalid"}
    integration = NodeIntegration(
        uuid=uuid4(),
        name="prometheus",
        description="metrics",
        config=secret_config,
    )
    provider.get_validated.return_value = NodeIntegrationCollection(
        total=1,
        node_integrations=[integration],
    )
    body = CreateNodeIntegrationRequest(
        name="prometheus",
        description="metrics",
        config=secret_config,
    )
    db = _db()
    request = _request("/api/v1/admin/remnawave-operator/node-integrations")
    actor = _actor()

    first = await routes.create_node_integration(
        body=body,
        request=request,
        idempotency_key="integration-create-1",
        current_user=actor,
        db=db,
        client=provider,
    )
    first_receipt = _json_response(first)
    assert isinstance(first, JSONResponse)
    assert first.status_code == 202
    assert first_receipt == {
        "attempt_id": str(attempt.record.id),
        "state": "reconciliation_required",
        "resource_kind": "node-integration",
        "requires_reconciliation": True,
    }
    assert "apiToken" not in json.dumps(first_receipt)
    provider.get_validated.assert_not_awaited()

    second = await routes.create_node_integration(
        body=body,
        request=request,
        idempotency_key="integration-create-1",
        current_user=actor,
        db=db,
        client=provider,
    )

    assert second == integration
    provider.post_validated.assert_awaited_once_with(
        "/node-integrations",
        NodeIntegration,
        json={
            "name": "prometheus",
            "description": "metrics",
            "config": secret_config,
        },
    )
    provider.get_validated.assert_awaited_once_with(
        "/node-integrations",
        NodeIntegrationCollection,
    )
    assert attempt.completed_references == [{"resource_uuid": str(integration.uuid)}]
    assert attempt.record.response_payload == {"resource_uuid": str(integration.uuid)}
    assert secret_config["apiToken"] not in json.dumps(attempt.record.response_payload)
    assert secret_config["apiToken"] not in json.dumps(attempt.begin_calls)
    assert secret_config["apiToken"] not in caplog.text
    assert audit.await_count == 2
    for audit_call in audit.await_args_list:
        serialized = json.dumps(audit_call.kwargs["details"], default=str)
        assert "apiToken" not in serialized


@pytest.mark.unit
async def test_audit_failure_never_commits_operator_completion_and_replay_does_not_repeat_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    audit = AsyncMock(side_effect=[RuntimeError("audit unavailable"), None])
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    provider = AsyncMock(spec=RemnawaveClient)
    integration = NodeIntegration(
        uuid=uuid4(),
        name="audit-atomic",
        description="operator audit atomicity",
        config={"url": "https://metrics.invalid"},
    )
    provider.post_validated.return_value = integration
    provider.get_validated.return_value = NodeIntegrationCollection(
        total=1,
        node_integrations=[integration],
    )
    body = CreateNodeIntegrationRequest(
        name=integration.name,
        description=integration.description,
        config=integration.config,
    )
    db = _db()
    request = _request("/api/v1/admin/remnawave-operator/node-integrations")

    with pytest.raises(RuntimeError, match="audit unavailable"):
        await routes.create_node_integration(
            body=body,
            request=request,
            idempotency_key="integration-audit-atomic",
            current_user=_actor(),
            db=db,
            client=provider,
        )

    db.commit.assert_not_awaited()
    # Simulate the request dependency rolling back the uncommitted completion;
    # the separately committed initial stop marker remains pending.
    attempt.record.status = "pending"
    attempt.record.response_payload = {}
    replay = await routes.create_node_integration(
        body=body,
        request=request,
        idempotency_key="integration-audit-atomic",
        current_user=_actor(),
        db=db,
        client=provider,
    )

    assert replay == integration
    provider.post_validated.assert_awaited_once()
    provider.get_validated.assert_awaited_once()
    assert db.commit.await_count == 1
    assert audit.await_count == 2


@pytest.mark.unit
async def test_definitive_provider_rejection_is_recorded_in_required_admin_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    audit = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    provider = AsyncMock(spec=RemnawaveClient)
    provider.post_validated.side_effect = RemnawaveHTTPStatusError(status_code=409)

    with pytest.raises(RemnawaveHTTPStatusError):
        await routes.create_shared_list(
            body=SharedListMutationRequest(name="routing/private", config={"type": "cidr"}),
            request=_request("/api/v1/admin/remnawave-operator/shared-lists"),
            idempotency_key="shared-list-rejected-1",
            current_user=_actor(),
            db=_db(),
            client=provider,
        )

    assert attempt.rejected_codes == ["provider_request_rejected"]
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["details"] == {
        "attempt_id": str(attempt.record.id),
        "resource_kind": "shared-list",
        "operation": "create",
        "state": "rejected",
    }


@pytest.mark.unit
async def test_latched_integration_update_settles_only_from_exact_uuid_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake(should_mutate=False, status="reconciliation_required")
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    integration = NodeIntegration(
        uuid=uuid4(),
        name="prometheus",
        description="updated",
        config={"url": "https://metrics.invalid"},
    )
    provider.get_validated.return_value = integration
    body = UpdateNodeIntegrationRequest(
        uuid=integration.uuid,
        description="updated",
        config=integration.config,
    )

    response = await routes.update_node_integration(
        body=body,
        request=_request("/api/v1/admin/remnawave-operator/node-integrations", method="PATCH"),
        idempotency_key="integration-update-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert response == integration
    provider.patch_validated.assert_not_awaited()
    provider.get_validated.assert_awaited_once_with(
        f"/node-integrations/{integration.uuid}",
        NodeIntegration,
    )
    assert attempt.completed_references == [{"resource_uuid": str(integration.uuid)}]


@pytest.mark.unit
async def test_latched_integration_restart_is_not_falsely_settled_by_resource_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake(should_mutate=False, status="reconciliation_required")
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    integration = NodeIntegration(
        uuid=uuid4(),
        name="prometheus",
        description="updated",
        config={"url": "https://metrics.invalid"},
    )
    provider.get_validated.return_value = integration
    body = UpdateNodeIntegrationRequest(
        uuid=integration.uuid,
        description="updated",
        restart_nodes=True,
    )

    response = await routes.update_node_integration(
        body=body,
        request=_request("/api/v1/admin/remnawave-operator/node-integrations", method="PATCH"),
        idempotency_key="integration-restart-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    assert _json_response(response)["state"] == "reconciliation_required"
    assert attempt.completed_references == []
    provider.patch_validated.assert_not_awaited()


@pytest.mark.unit
async def test_empty_shared_list_create_is_settled_by_exact_name_and_config_readback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    provider.post_validated.return_value = None
    shared_list = SharedList(name="routing/private", config={"type": "cidr", "items": ["10.0.0.0/8"]})
    provider.get_validated.return_value = shared_list
    body = SharedListMutationRequest(name=shared_list.name, config=shared_list.config)

    response = await routes.create_shared_list(
        body=body,
        request=_request("/api/v1/admin/remnawave-operator/shared-lists"),
        idempotency_key="shared-list-create-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert response == shared_list
    provider.post_validated.assert_awaited_once_with(
        "/node-plugins/shared-lists",
        SharedList,
        json={"name": "routing/private", "config": shared_list.config},
    )
    provider.get_validated.assert_awaited_once_with(
        "/node-plugins/shared-lists/by-name",
        SharedList,
        params={"name": "routing/private"},
    )
    assert attempt.completed_references == [{"resource_name": "routing/private"}]


@pytest.mark.unit
async def test_empty_snippet_create_without_authoritative_match_stays_latched_and_is_not_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    provider.post_validated.return_value = None
    provider.get_validated.return_value = SnippetCollection(total=0, snippets=[])
    body = SnippetMutationRequest(
        name="root/default",
        snippet=[{"protocol": "vless", "flow": "xtls-rprx-vision"}],
    )
    request = _request("/api/v1/admin/remnawave-operator/snippets")
    first = await routes.create_snippet(
        body=body,
        request=request,
        idempotency_key="snippet-create-empty-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )
    second = await routes.create_snippet(
        body=body,
        request=request,
        idempotency_key="snippet-create-empty-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert isinstance(first, JSONResponse)
    assert isinstance(second, JSONResponse)
    assert first.status_code == 202
    assert second.status_code == 202
    for response in (first, second):
        assert _json_response(response)["state"] == "reconciliation_required"
        assert _json_response(response)["requires_reconciliation"] is True
    provider.post_validated.assert_awaited_once_with(
        "/snippets",
        SnippetCollection,
        json={
            "name": "root/default",
            "snippet": [{"protocol": "vless", "flow": "xtls-rprx-vision"}],
        },
    )
    assert provider.get_validated.await_count == 2
    assert provider.get_validated.await_args_list == [
        call("/snippets", SnippetCollection),
        call("/snippets", SnippetCollection),
    ]
    assert attempt.reconciliation_marks == 1
    assert attempt.completed_references == []


@pytest.mark.unit
async def test_reconciliation_latched_snippet_uses_exact_collection_readback_without_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake(should_mutate=False, status="reconciliation_required")
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    snippet = Snippet(name="root/default", snippet=[{"protocol": "vless", "flow": "xtls-rprx-vision"}])
    provider.get_validated.return_value = SnippetCollection(total=1, snippets=[snippet])
    body = SnippetMutationRequest(name=snippet.name, snippet=snippet.snippet)

    response = await routes.create_snippet(
        body=body,
        request=_request("/api/v1/admin/remnawave-operator/snippets"),
        idempotency_key="snippet-create-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert response == snippet
    provider.post_validated.assert_not_awaited()
    provider.get_validated.assert_awaited_once_with("/snippets", SnippetCollection)
    assert attempt.completed_references == [{"resource_name": "root/default"}]


@pytest.mark.unit
async def test_sync_returns_safe_accepted_receipt_and_uses_exact_343_action_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    audit = AsyncMock()
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", audit)
    provider = AsyncMock(spec=RemnawaveClient)
    provider.post_validated.return_value = None

    response = await routes.sync_shared_list(
        body=SharedListNameRequest(name="routing/private"),
        request=_request("/api/v1/admin/remnawave-operator/shared-lists/actions/sync"),
        idempotency_key="shared-list-sync-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert response.status_code == 202
    assert _json_response(response) == {
        "attempt_id": str(attempt.record.id),
        "state": "accepted",
        "resource_kind": "shared-list",
        "requires_reconciliation": False,
    }
    provider.post_validated.assert_awaited_once_with(
        "/node-plugins/shared-lists/actions/sync",
        OperatorMutationReceipt,
        json={"name": "routing/private"},
    )
    assert attempt.completed_references == [{"resource_name": "routing/private", "accepted": True}]
    assert audit.await_args.kwargs["details"] == {
        "attempt_id": str(attempt.record.id),
        "resource_kind": "shared-list",
        "operation": "sync",
        "state": "accepted",
    }


@pytest.mark.unit
async def test_delete_requires_authoritative_absence_and_completed_replay_never_deletes_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    provider.delete_validated.return_value = None
    provider.get_validated.return_value = SnippetCollection(total=0, snippets=[])
    body = SnippetNameRequest(name="root/default")
    request = _request("/api/v1/admin/remnawave-operator/snippets", method="DELETE")

    first = await routes.delete_snippet(
        body=body,
        request=request,
        idempotency_key="snippet-delete-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )
    second = await routes.delete_snippet(
        body=body,
        request=request,
        idempotency_key="snippet-delete-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )

    assert first.status_code == 204
    assert second.status_code == 204
    provider.delete_validated.assert_awaited_once_with(
        "/snippets",
        json={"name": "root/default"},
    )
    provider.get_validated.assert_awaited_once_with("/snippets", SnippetCollection)
    assert attempt.completed_references == [{"resource_name": "root/default", "deleted": True}]


@pytest.mark.unit
async def test_geocheck_uses_exact_connections_paths_and_target_alias_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = _AttemptServiceFake()
    _install_attempt_service(monkeypatch, attempt)
    monkeypatch.setattr(routes, "write_required_admin_audit_entry", AsyncMock())
    provider = AsyncMock(spec=RemnawaveClient)
    node_uuid = uuid4()
    job = GeoCheckJobResponse.model_validate({"jobId": "geo-job-42"})
    pending = GeoCheckResultResponse.model_validate({"isCompleted": False, "isFailed": False, "result": None})
    provider.post_validated.return_value = job
    provider.get_validated.return_value = pending

    started = await routes.start_geocheck(
        node_uuid=node_uuid,
        body=GeoCheckRequest(ip="198.51.100.42"),
        request=_request(f"/api/v1/admin/remnawave-operator/geocheck/nodes/{node_uuid}"),
        idempotency_key="geocheck-start-1",
        current_user=_actor(),
        db=_db(),
        client=provider,
    )
    fetched = await routes.get_geocheck_result(
        job_id=job.job_id,
        _current_user=_actor(),
        client=provider,
    )

    assert started == job
    assert fetched == pending
    provider.post_validated.assert_awaited_once_with(
        f"/connections/geocheck/{node_uuid}",
        GeoCheckJobResponse,
        json={"ip": "198.51.100.42"},
    )
    provider.get_validated.assert_awaited_once_with(
        "/connections/geocheck/geo-job-42",
        GeoCheckResultResponse,
    )
    assert attempt.completed_references == [{"job_id": "geo-job-42", "node_uuid": str(node_uuid)}]


@pytest.mark.unit
async def test_exact_343_collection_paths_and_shapes_are_preserved() -> None:
    provider = AsyncMock(spec=RemnawaveClient)
    integration = NodeIntegration(
        uuid=uuid4(),
        name="prometheus",
        description=None,
        config={"url": "https://metrics.invalid"},
    )
    shared_list = SharedList(name="routing/private", config={"items": ["10.0.0.0/8"]})
    snippet = Snippet(name="root/default", snippet=[{"protocol": "vless"}])
    provider.get_validated.side_effect = [
        NodeIntegrationCollection(total=1, node_integrations=[integration]),
        shared_list,
        SnippetCollection(total=1, snippets=[snippet]),
    ]

    integrations = await routes.list_node_integrations(_current_user=_actor(), client=provider)
    fetched_shared_list = await routes.get_shared_list(
        name="routing/private",
        _current_user=_actor(),
        client=provider,
    )
    snippets = await routes.list_snippets(_current_user=_actor(), client=provider)

    assert integrations.total == 1 and integrations.items == [integration]
    assert fetched_shared_list == shared_list
    assert snippets.total == 1 and snippets.items == [snippet]
    assert provider.get_validated.await_args_list == [
        call("/node-integrations", NodeIntegrationCollection),
        call(
            "/node-plugins/shared-lists/by-name",
            SharedList,
            params={"name": "routing/private"},
        ),
        call("/snippets", SnippetCollection),
    ]
