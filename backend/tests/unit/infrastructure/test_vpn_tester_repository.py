from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.vpn_tester_model import VpnTestSuiteModel
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
