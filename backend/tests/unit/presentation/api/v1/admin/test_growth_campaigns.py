from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from src.application.use_cases.growth_campaigns.admin_lifecycle import (
    CampaignTransitionError,
    GrowthCampaignRecord,
)
from src.domain.enums import AdminRole
from src.presentation.api.v1.admin import growth_campaigns

ADMIN_ID = UUID("00000000-0000-0000-0000-000000000111")
CAMPAIGN_ID = UUID("00000000-0000-0000-0000-000000000222")
NOW = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


class RecordingDB:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


def _request():
    return SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.45"),
        state=SimpleNamespace(),
        headers={"user-agent": "pytest-admin"},
    )


def _admin():
    return SimpleNamespace(
        id=ADMIN_ID,
        role=AdminRole.ADMIN.value,
        login="growth-admin",
        email="growth-admin@example.test",
    )


def _record(*, status: str = "draft", version: int = 1) -> GrowthCampaignRecord:
    return GrowthCampaignRecord(
        id=CAMPAIGN_ID,
        campaign_key="pro-free-invites-2026",
        name="PRO 100% + invites",
        description=None,
        status=status,
        priority=100,
        starts_at=None,
        expires_at=None,
        stacking_mode="exclusive",
        stacking_group="checkout_discount",
        current_version=version,
        created_by_admin_id=ADMIN_ID,
        updated_by_admin_id=None,
        published_at=None,
        paused_at=None,
        archived_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_create_admin_growth_campaign_writes_audit_with_reason(monkeypatch) -> None:
    class FakeUseCase:
        async def create_campaign(self, **kwargs):
            assert kwargs["created_by_admin_id"] == ADMIN_ID
            assert kwargs["campaign_key"] == "PRO-Free-Invites-2026"
            return _record()

    monkeypatch.setattr(growth_campaigns, "_use_case", lambda _db: FakeUseCase())
    db = RecordingDB()

    response = await growth_campaigns.create_admin_growth_campaign(
        payload=growth_campaigns.AdminGrowthCampaignCreateRequest(
            campaign_key="PRO-Free-Invites-2026",
            name="PRO 100% + invites",
            schedule=growth_campaigns.AdminGrowthCampaignScheduleRequest(),
            priority=100,
            stacking=growth_campaigns.AdminGrowthCampaignStackingRequest(group="checkout_discount"),
        ),
        request=_request(),
        db=db,
        current_user=_admin(),
    )

    assert response.id == CAMPAIGN_ID
    assert response.status == "draft"
    audit_entry = db.added[0]
    assert audit_entry.action == "growth_campaign.created"
    assert audit_entry.entity_type == "growth_campaign"
    assert audit_entry.entity_id == str(CAMPAIGN_ID)
    assert audit_entry.new_value["reason_code"] == "campaign_created"
    assert audit_entry.new_value["campaign_key"] == "pro-free-invites-2026"


@pytest.mark.asyncio
async def test_update_admin_growth_campaign_maps_active_immutability_to_conflict(monkeypatch) -> None:
    class FakeUseCase:
        async def get_campaign(self, campaign_id):
            assert campaign_id == CAMPAIGN_ID
            return _record(status="active")

        async def update_draft_campaign(self, **kwargs):
            raise CampaignTransitionError("active_campaign_immutable")

    monkeypatch.setattr(growth_campaigns, "_use_case", lambda _db: FakeUseCase())

    with pytest.raises(HTTPException) as exc_info:
        await growth_campaigns.update_admin_growth_campaign(
            campaign_id=CAMPAIGN_ID,
            payload=growth_campaigns.AdminGrowthCampaignPatchRequest(
                name="Mutated active campaign",
                expected_version=1,
                reason_code="operator_update",
            ),
            request=_request(),
            db=RecordingDB(),
            current_user=_admin(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "ACTIVE_CAMPAIGN_IMMUTABLE"


@pytest.mark.asyncio
async def test_revoke_admin_growth_campaign_writes_required_audit_reason_without_auto_entitlement_revoke(
    monkeypatch,
) -> None:
    class FakeUseCase:
        async def get_campaign(self, campaign_id):
            assert campaign_id == CAMPAIGN_ID
            return _record(status="active")

        async def revoke_campaign(self, **kwargs):
            assert kwargs["campaign_id"] == CAMPAIGN_ID
            assert kwargs["actor_admin_id"] == ADMIN_ID
            assert kwargs["expected_version"] == 3
            return _record(status="revoked", version=3)

    monkeypatch.setattr(growth_campaigns, "_use_case", lambda _db: FakeUseCase())
    db = RecordingDB()

    response = await growth_campaigns.revoke_admin_growth_campaign(
        campaign_id=CAMPAIGN_ID,
        payload=growth_campaigns.AdminGrowthCampaignActionRequest(
            expected_version=3,
            reason_code="refund_abuse_campaign_stop",
        ),
        request=_request(),
        db=db,
        current_user=_admin(),
    )

    assert response.status == "revoked"
    audit_entry = db.added[0]
    assert audit_entry.action == "growth_campaign.revoked"
    assert audit_entry.entity_type == "growth_campaign"
    assert audit_entry.entity_id == str(CAMPAIGN_ID)
    assert audit_entry.old_value["status"] == "active"
    assert audit_entry.new_value["status"] == "revoked"
    assert audit_entry.new_value["reason_code"] == "refund_abuse_campaign_stop"
    assert "entitlement" not in audit_entry.new_value
