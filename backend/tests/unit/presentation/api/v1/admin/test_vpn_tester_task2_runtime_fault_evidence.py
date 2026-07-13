from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from src.application.vpn_testing.task2_runtime_fault_evidence import (
    Task2RuntimeFaultEvidenceConflict,
    Task2RuntimeFaultEvidenceRejected,
)
from src.config.settings import settings
from src.presentation.api.v1.admin import vpn_tester as vpn_tester_module
from src.presentation.api.v1.admin.vpn_tester import get_vpn_tester_service, router

INTERNAL_SECRET = "task2RuntimeFaultInternalSecretAlpha123"
RUN_ID = UUID("00000000-0000-4000-8000-000000000001")
ARTIFACT_ID = UUID("00000000-0000-4000-8000-000000000002")
PATH = f"/admin/vpn-tester/internal/task2/runs/{RUN_ID}/signed-evidence"
VALID_BODY = b'{"schema":"test.signed-evidence"}'
OVERSIZED_BODY = b'{"evidence":"' + (b"x" * 256) + b'"}'
NOW = datetime(2026, 7, 13, 6, 30, tzinfo=UTC)


class FakeVpnTesterService:
    def __init__(self) -> None:
        self.result: tuple[Any, Any, bool] | None = None
        self.exception: Exception | None = None
        self.calls: list[tuple[UUID, bytes]] = []

    async def ingest_task2_runtime_fault_evidence(
        self,
        run_id: UUID,
        raw_body: bytes,
    ) -> tuple[Any, Any, bool] | None:
        self.calls.append((run_id, raw_body))
        if self.exception is not None:
            raise self.exception
        return self.result


def _configure_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool = True,
    max_body_bytes: int = 4096,
) -> None:
    monkeypatch.setattr(settings, "vpn_tester_task2_operator_evidence_enabled", enabled)
    monkeypatch.setattr(settings, "backend_internal_secret", SecretStr(INTERNAL_SECRET))
    monkeypatch.setattr(settings, "vpn_tester_task2_operator_evidence_max_body_bytes", max_body_bytes)


def _app(service: FakeVpnTesterService) -> FastAPI:
    app = FastAPI()

    async def override_get_vpn_tester_service() -> FakeVpnTesterService:
        return service

    app.dependency_overrides[get_vpn_tester_service] = override_get_vpn_tester_service
    app.include_router(router)
    return app


def _headers(
    *,
    marker: str | None = vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_MARKER,
    secret: str = INTERNAL_SECRET,
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Backend-Internal-Secret": secret,
    }
    if marker is not None:
        headers[vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_HEADER] = marker
    return headers


def _artifact() -> SimpleNamespace:
    return SimpleNamespace(
        id=ARTIFACT_ID,
        artifact_key="task2-runtime-fault:0123456789abcdef0123456789abcdef",
        artifact_type="task2_runtime_fault_evidence",
        sha256="a" * 64,
        preview={
            "summary": {
                "credentials_redacted": True,
                "execution_attempt_id": "0123456789abcdef0123456789abcdef",
            },
            "envelope": {
                "payload": {
                    "backend": {"image_id": "sha256:private-runtime-fingerprint"},
                    "operator": {"instance": "private-operator-instance"},
                    "fault_rows": [{"route_key": "private-firewall-row"}],
                }
            },
        },
        storage_uri=None,
        expires_at=None,
        created_at=NOW,
    )


def _run(artifact: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        id=RUN_ID,
        suite_key="premium_spb_de_exceptions_v1",
        suite_version="v1",
        mode="runtime",
        trigger="scheduled",
        status="pass",
        requested_by_admin_id=None,
        agent_id="spb-task2-runtime-agent",
        runtime_mode="proxy-only",
        route_registry_version="premium_spb_de_exceptions_v1",
        blocking=False,
        summary={
            "execution_attempt_id": "0123456789abcdef0123456789abcdef",
            "task2_runtime_fault_evidence": {"status": "signed_pass"},
        },
        pass_count=4,
        fail_count=0,
        degraded_count=0,
        started_at=NOW,
        finished_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        results=[],
        evidence_artifacts=[artifact],
    )


def _service_result(*, created: bool = True) -> tuple[SimpleNamespace, SimpleNamespace, bool]:
    artifact = _artifact()
    return _run(artifact), artifact, created


@pytest.fixture
def service() -> FakeVpnTesterService:
    return FakeVpnTesterService()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    service: FakeVpnTesterService,
) -> Generator[TestClient]:
    _configure_settings(monkeypatch)
    with TestClient(_app(service)) as test_client:
        yield test_client


def test_feature_disabled_returns_404_without_calling_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    service: FakeVpnTesterService,
) -> None:
    monkeypatch.setattr(settings, "vpn_tester_task2_operator_evidence_enabled", False)

    response = client.post(PATH, headers=_headers(), content=VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"] == "task2_operator_evidence_not_found"
    assert service.calls == []


@pytest.mark.parametrize("marker", [None, "wrong-marker"])
def test_missing_or_wrong_ingress_marker_returns_404_before_body_limits(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    service: FakeVpnTesterService,
    marker: str | None,
) -> None:
    monkeypatch.setattr(settings, "vpn_tester_task2_operator_evidence_max_body_bytes", 16)

    response = client.post(PATH, headers=_headers(marker=marker), content=OVERSIZED_BODY)

    assert response.status_code == 404
    assert response.json()["detail"] == "task2_operator_evidence_not_found"
    assert service.calls == []


def test_duplicate_ingress_marker_header_is_rejected_before_service(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    response = client.post(
        PATH,
        headers=[
            (
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_MARKER,
            ),
            (
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_MARKER,
            ),
            ("X-Backend-Internal-Secret", INTERNAL_SECRET),
            ("Content-Type", "application/json"),
        ],
        content=VALID_BODY,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "duplicate_ingress_marker_header"
    assert service.calls == []


def test_duplicate_internal_secret_header_is_rejected_before_auth(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    response = client.post(
        PATH,
        headers=[
            (
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_HEADER,
                vpn_tester_module.TASK2_OPERATOR_EVIDENCE_INGRESS_MARKER,
            ),
            ("X-Backend-Internal-Secret", INTERNAL_SECRET),
            ("X-Backend-Internal-Secret", INTERNAL_SECRET),
            ("Content-Type", "application/json"),
        ],
        content=VALID_BODY,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "duplicate_internal_secret_header"
    assert service.calls == []


@pytest.mark.parametrize(
    ("path_suffix", "extra_headers", "detail"),
    [
        ("?secret=leak", {}, "query_string_not_allowed"),
        ("", {"Authorization": "Bearer token"}, "authorization_header_not_allowed"),
        ("", {"Cookie": "session=secret"}, "cookie_header_not_allowed"),
        ("", {"Proxy-Authorization": "Basic token"}, "proxy-authorization_header_not_allowed"),
    ],
)
def test_query_auth_cookie_and_proxy_auth_are_rejected(
    client: TestClient,
    service: FakeVpnTesterService,
    path_suffix: str,
    extra_headers: dict[str, str],
    detail: str,
) -> None:
    response = client.post(
        f"{PATH}{path_suffix}",
        headers={**_headers(), **extra_headers},
        content=VALID_BODY,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == detail
    assert service.calls == []


def test_non_json_content_type_is_rejected_before_service(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    response = client.post(
        PATH,
        headers={**_headers(), "Content-Type": "text/plain"},
        content=VALID_BODY,
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "json_required"
    assert service.calls == []


def test_oversized_body_is_rejected_before_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    service: FakeVpnTesterService,
) -> None:
    monkeypatch.setattr(settings, "vpn_tester_task2_operator_evidence_max_body_bytes", 16)

    response = client.post(PATH, headers=_headers(), content=OVERSIZED_BODY)

    assert response.status_code == 413
    assert response.json()["detail"] == "body_too_large"
    assert service.calls == []


def test_wrong_internal_secret_returns_401_without_calling_service(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    response = client.post(
        PATH,
        headers=_headers(secret="wrong-secret"),
        content=b"{not-json",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."
    assert service.calls == []


def test_valid_service_result_is_serialized_and_endpoint_is_hidden_from_openapi(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    service.result = _service_result(created=True)

    response = client.post(PATH, headers=_headers(), content=VALID_BODY)

    assert response.status_code == 200
    assert service.calls == [(RUN_ID, VALID_BODY)]
    body = response.json()
    assert set(body) == {"run", "artifact", "created"}
    assert body["created"] is True
    assert body["run"]["id"] == str(RUN_ID)
    assert body["run"]["status"] == "pass"
    assert body["run"]["summary"] == {
        "execution_attempt_id": "0123456789abcdef0123456789abcdef",
        "task2_runtime_fault_evidence": {"status": "signed_pass"},
    }
    assert body["run"]["evidence_artifacts"][0]["artifact_key"] == (
        "task2-runtime-fault:0123456789abcdef0123456789abcdef"
    )
    assert body["artifact"]["id"] == str(ARTIFACT_ID)
    assert body["artifact"]["sha256"] == "a" * 64
    assert body["artifact"]["preview"] == {
        "summary": {
            "credentials_redacted": True,
            "execution_attempt_id": "0123456789abcdef0123456789abcdef",
        }
    }
    serialized = str(body)
    assert "private-runtime-fingerprint" not in serialized
    assert "private-operator-instance" not in serialized
    assert "private-firewall-row" not in serialized
    assert PATH not in client.get("/openapi.json").json()["paths"]


def test_service_conflict_maps_to_409(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    service.exception = Task2RuntimeFaultEvidenceConflict()

    response = client.post(PATH, headers=_headers(), content=VALID_BODY)

    assert response.status_code == 409
    assert response.json()["detail"] == "conflicting_task2_runtime_fault_evidence"
    assert service.calls == [(RUN_ID, VALID_BODY)]


def test_rejected_evidence_maps_to_422(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    service.exception = Task2RuntimeFaultEvidenceRejected("invalid_signature")

    response = client.post(PATH, headers=_headers(), content=VALID_BODY)

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_task2_runtime_fault_evidence"
    assert service.calls == [(RUN_ID, VALID_BODY)]


def test_run_not_found_maps_to_404(
    client: TestClient,
    service: FakeVpnTesterService,
) -> None:
    service.result = None

    response = client.post(PATH, headers=_headers(), content=VALID_BODY)

    assert response.status_code == 404
    assert response.json()["detail"] == "vpn_tester_run_not_found"
    assert service.calls == [(RUN_ID, VALID_BODY)]
