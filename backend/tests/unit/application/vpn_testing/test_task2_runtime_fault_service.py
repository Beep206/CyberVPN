from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.vpn_testing import service as service_module
from src.application.vpn_testing.service import VpnTesterService
from src.application.vpn_testing.task2_runtime_fault_evidence import (
    TASK2_RUNTIME_FAULT_EVIDENCE_ARTIFACT_TYPE,
    Task2RuntimeFaultEvidenceConflict,
    Task2RuntimeFaultEvidenceRejected,
)

ATTEMPT_ID = "1" * 32


def _run() -> SimpleNamespace:
    now = datetime(2026, 7, 13, 12, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid4(),
        suite_key="premium_spb_de_exceptions_v1",
        suite_version="v1",
        mode="runtime",
        trigger="manual",
        status="degraded",
        summary={
            "execution_attempt_id": ATTEMPT_ID,
            "route_registry_version": "premium_spb_de_exceptions_v1",
            "task2_runtime_identity": {
                "bound": True,
                "backend_sha256": "a" * 64,
                "agent_sha256": "b" * 64,
                "credentials_redacted": True,
            },
        },
        route_registry_version="premium_spb_de_exceptions_v1",
        runtime_mode="proxy-only",
        results=[],
        evidence_artifacts=[],
        started_at=now,
        finished_at=now,
    )


def _repository(run: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(
        get_run_for_update=AsyncMock(return_value=run),
        get_evidence_artifact=AsyncMock(return_value=None),
        get_suite=AsyncMock(
            return_value=SimpleNamespace(
                spec={
                    "suite_key": "premium_spb_de_exceptions_v1",
                    "version": "v1",
                    "required_route_registry": "premium_spb_de_exceptions_v1",
                }
            )
        ),
        get_route_registry=AsyncMock(return_value=[]),
        lock_signed_evidence_identity=AsyncMock(),
        find_evidence_by_signed_identity=AsyncMock(return_value=[]),
        list_active_plans=AsyncMock(return_value=[]),
        replace_run_results=AsyncMock(return_value=run),
        add_evidence_artifact=AsyncMock(return_value=SimpleNamespace(id=uuid4(), sha256="a" * 64)),
        get_run=AsyncMock(return_value=run),
    )


@pytest.mark.asyncio
async def test_ingest_promotes_and_persists_signed_evidence_atomically(monkeypatch) -> None:
    run = _run()
    repository = _repository(run)
    verified = SimpleNamespace(
        nonce="2" * 32,
        evidence_id="task2-evidence-20260713-a",
        payload_sha256="3" * 64,
        envelope_sha256="4" * 64,
        artifact=lambda: {
            "artifact_key": f"task2-runtime-fault:{ATTEMPT_ID}",
            "artifact_type": TASK2_RUNTIME_FAULT_EVIDENCE_ARTIFACT_TYPE,
            "sha256": "4" * 64,
            "preview": {"summary": {"nonce": "2" * 32}},
            "storage_uri": None,
            "expires_at": None,
        },
    )
    promoted = [
        {
            "check_key": "premium_spb_de_exceptions.runtime.completeness",
            "check_name": "Task2 runtime completeness",
            "category": "runtime",
            "status": "pass",
            "severity": "error",
            "target": "task2",
            "safe_summary": "Signed evidence passed",
            "details": {"execution_attempt_id": ATTEMPT_ID},
            "duration_ms": 0,
        }
    ]
    monkeypatch.setattr(service_module, "verify_task2_runtime_fault_evidence", MagicMock(return_value=verified))
    monkeypatch.setattr(service_module, "promote_task2_runtime_fault_results", MagicMock(return_value=promoted))
    service = VpnTesterService(repository)
    service._evidence = MagicMock(return_value=[])

    result = await service.ingest_task2_runtime_fault_evidence(run.id, b"{}")

    assert result is not None
    returned_run, _artifact, created = result
    assert returned_run is run
    assert created is True
    replace_kwargs = repository.replace_run_results.await_args.kwargs
    assert replace_kwargs["status"] == "pass"
    assert replace_kwargs["summary"]["execution_attempt_id"] == ATTEMPT_ID
    assert replace_kwargs["summary"]["task2_runtime_fault_evidence"]["canonical_sha256"] == "4" * 64
    assert "preserve_evidence_types" not in replace_kwargs
    repository.lock_signed_evidence_identity.assert_awaited_once_with(
        nonce="2" * 32,
        evidence_id="task2-evidence-20260713-a",
    )
    artifact_payload = repository.add_evidence_artifact.await_args.args[1]
    assert artifact_payload["artifact_key"] == f"task2-runtime-fault:{ATTEMPT_ID}"
    assert artifact_payload["expires_at"] is not None


@pytest.mark.asyncio
async def test_ingest_exact_retry_is_idempotent_after_revalidation(monkeypatch) -> None:
    run = _run()
    repository = _repository(run)
    existing = SimpleNamespace(sha256="a" * 64)
    repository.get_evidence_artifact.return_value = existing
    verify_mock = MagicMock(return_value=SimpleNamespace(envelope_sha256="a" * 64))
    monkeypatch.setattr(service_module, "verify_task2_runtime_fault_evidence", verify_mock)

    result = await VpnTesterService(repository).ingest_task2_runtime_fault_evidence(run.id, b"same")

    assert result == (run, existing, False)
    verify_mock.assert_called_once()
    repository.replace_run_results.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_conflicting_retry_is_rejected(monkeypatch) -> None:
    run = _run()
    repository = _repository(run)
    repository.get_evidence_artifact.return_value = SimpleNamespace(sha256="a" * 64)
    monkeypatch.setattr(
        service_module,
        "verify_task2_runtime_fault_evidence",
        MagicMock(return_value=SimpleNamespace(envelope_sha256="b" * 64)),
    )

    with pytest.raises(Task2RuntimeFaultEvidenceConflict):
        await VpnTesterService(repository).ingest_task2_runtime_fault_evidence(run.id, b"conflict")

    repository.replace_run_results.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_rejects_replayed_nonce_or_evidence_id(monkeypatch) -> None:
    run = _run()
    repository = _repository(run)
    repository.find_evidence_by_signed_identity.return_value = [SimpleNamespace(id=uuid4())]
    verified = SimpleNamespace(
        nonce="2" * 32,
        evidence_id="task2-evidence-20260713-a",
    )
    monkeypatch.setattr(service_module, "verify_task2_runtime_fault_evidence", MagicMock(return_value=verified))

    with pytest.raises(Task2RuntimeFaultEvidenceRejected, match="signed_evidence_identity_replayed"):
        await VpnTesterService(repository).ingest_task2_runtime_fault_evidence(run.id, b"replay")

    repository.replace_run_results.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_returns_none_for_unknown_run() -> None:
    repository = SimpleNamespace(get_run_for_update=AsyncMock(return_value=None))

    result = await VpnTesterService(repository).ingest_task2_runtime_fault_evidence(uuid4(), b"{}")

    assert result is None


@pytest.mark.asyncio
async def test_execute_persists_bound_backend_and_agent_identity_digests(monkeypatch) -> None:
    run = _run()
    run.status = "queued"
    run.request_context = {}
    run.agent_id = None
    repository = SimpleNamespace(
        mark_run_running=AsyncMock(),
        get_suite=AsyncMock(
            return_value=SimpleNamespace(
                spec={
                    "suite_key": "premium_spb_de_exceptions_v1",
                    "version": "v1",
                    "required_route_registry": "premium_spb_de_exceptions_v1",
                }
            )
        ),
        list_active_plans=AsyncMock(return_value=[]),
        get_route_registry=AsyncMock(return_value=[]),
        replace_run_results=AsyncMock(side_effect=lambda current_run, **_kwargs: current_run),
    )
    for name, value in {
        "runtime_git_sha": "9" * 40,
        "runtime_container_image": "cybervpn/cybervpn-backend:task2-runtime",
        "runtime_origin_marker": "prod-app-1",
        "vpn_tester_task2_operator_evidence_backend_image_id": "sha256:" + "2" * 64,
        "vpn_tester_task2_operator_evidence_agent_git_sha": "8" * 40,
        "vpn_tester_task2_operator_evidence_agent_image_ref": ("cybervpn/cybervpn-vpn-test-agent:task2-runtime"),
        "vpn_tester_task2_operator_evidence_agent_image_id": "sha256:" + "3" * 64,
    }.items():
        monkeypatch.setattr(service_module.settings, name, value)
    matrix = {
        "check_key": "premium_spb_de_exceptions.selected_outbound.matrix",
        "check_name": "Task2 selected-outbound matrix",
        "category": "runtime",
        "status": "degraded",
        "severity": "warning",
        "target": "spb-xray",
        "safe_summary": "Bridge-down evidence pending",
        "details": {"agent_id": "spb-agent-1"},
        "duration_ms": 0,
    }
    service = VpnTesterService(repository)
    service._generated_mihomo_artifact = AsyncMock(return_value={"generated_mihomo_yaml": "proxies: []"})
    service._contract_results = AsyncMock(return_value=[])
    service._runtime_results = AsyncMock(return_value=[matrix])
    service._evidence = MagicMock(return_value=[])

    await service.execute_run(run)

    summary = repository.replace_run_results.await_args.kwargs["summary"]
    assert summary["task2_runtime_identity"]["bound"] is True
    assert len(summary["task2_runtime_identity"]["backend_sha256"]) == 64
    assert len(summary["task2_runtime_identity"]["agent_sha256"]) == 64
    assert run.agent_id == "spb-agent-1"
