from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.vpn_tester_model import (
    VpnTestEvidenceArtifactModel,
    VpnTestRunModel,
    VpnTestSuiteModel,
)
from src.infrastructure.database.repositories.vpn_tester_repo import VpnTesterRepository

pytestmark = pytest.mark.asyncio


class StaleReadVpnTesterRepository(VpnTesterRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.force_stale_suite_read = True

    async def get_suite(self, suite_key: str, version: str = "v1") -> VpnTestSuiteModel | None:
        if self.force_stale_suite_read:
            self.force_stale_suite_read = False
            return None
        return await super().get_suite(suite_key, version)


async def test_upsert_suite_recovers_from_unique_conflict_after_stale_read(db: AsyncSession) -> None:
    suite_key = f"pytest_vpn_suite_{uuid4().hex}"
    existing = VpnTestSuiteModel(
        suite_key=suite_key,
        version="v1",
        display_name="Existing suite",
        mode="contract",
        description="Existing description",
        spec={"suite_key": suite_key, "version": "v1"},
        enabled=False,
    )
    db.add(existing)
    await db.flush()

    suite = await StaleReadVpnTesterRepository(db).upsert_suite(
        {
            "suite_key": suite_key,
            "version": "v1",
            "display_name": "Updated suite",
            "mode": "runtime",
            "description": "Updated description",
            "checks": [{"key": "route.contract", "severity": "warning"}],
        }
    )

    rows = (
        (
            await db.execute(
                select(VpnTestSuiteModel).where(
                    VpnTestSuiteModel.suite_key == suite_key,
                    VpnTestSuiteModel.version == "v1",
                )
            )
        )
        .scalars()
        .all()
    )

    assert suite.id == existing.id
    assert len(rows) == 1
    assert rows[0].display_name == "Updated suite"
    assert rows[0].mode == "runtime"
    assert rows[0].description == "Updated description"
    assert rows[0].enabled is True
    assert rows[0].spec["checks"][0]["key"] == "route.contract"


async def test_reexecution_removes_signed_evidence_from_previous_attempt(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    run = VpnTestRunModel(
        suite_key="premium_spb_de_exceptions_v1",
        suite_version="v1",
        mode="runtime",
        trigger="manual",
        status="pass",
        request_context={},
        summary={"status": "pass", "execution_attempt_id": "0" * 32},
        runtime_mode="proxy-only",
        route_registry_version="premium_spb_de_exceptions_v1",
        started_at=now - timedelta(minutes=2),
        finished_at=now - timedelta(minutes=1),
    )
    db.add(run)
    await db.flush()
    signed = VpnTestEvidenceArtifactModel(
        run_id=run.id,
        artifact_key=f"task2-runtime-fault:{'0' * 32}",
        artifact_type="task2_runtime_fault_evidence",
        sha256="a" * 64,
        preview={
            "summary": {
                "nonce": "1" * 32,
                "evidence_id": "task2-evidence-first",
            }
        },
    )
    replaceable = VpnTestEvidenceArtifactModel(
        run_id=run.id,
        artifact_key="contract-summary",
        artifact_type="json_preview",
        sha256="b" * 64,
        preview={},
    )
    db.add_all([signed, replaceable])
    await db.flush()
    repository = VpnTesterRepository(db)

    await repository.mark_run_running(run, execution_attempt_id="2" * 32)

    assert run.status == "running"
    assert run.finished_at is None
    assert run.summary == {"status": "running", "execution_attempt_id": "2" * 32}
    artifacts_while_running = (
        (await db.execute(select(VpnTestEvidenceArtifactModel).where(VpnTestEvidenceArtifactModel.run_id == run.id)))
        .scalars()
        .all()
    )
    assert artifacts_while_running == []
    await repository.replace_run_results(
        run,
        results=[],
        evidence=[
            {
                "artifact_key": "contract-summary",
                "artifact_type": "json_preview",
                "sha256": "c" * 64,
                "preview": {},
                "storage_uri": None,
                "expires_at": None,
            }
        ],
        summary={"status": "pass", "execution_attempt_id": "2" * 32},
        status="pass",
    )

    artifacts = (
        (await db.execute(select(VpnTestEvidenceArtifactModel).where(VpnTestEvidenceArtifactModel.run_id == run.id)))
        .scalars()
        .all()
    )
    assert {(artifact.artifact_type, artifact.sha256) for artifact in artifacts} == {
        ("json_preview", "c" * 64),
    }
    await repository.lock_signed_evidence_identity(
        nonce="1" * 32,
        evidence_id="unused-evidence-id",
    )
    replay_matches = await repository.find_evidence_by_signed_identity(
        artifact_type="task2_runtime_fault_evidence",
        nonce="1" * 32,
        evidence_id="unused-evidence-id",
    )
    assert replay_matches == []
