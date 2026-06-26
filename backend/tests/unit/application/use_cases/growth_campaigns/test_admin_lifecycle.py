from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.growth_campaigns.admin_lifecycle import (
    CampaignTransitionError,
    CampaignValidationError,
    CampaignVersionConflictError,
    DuplicateCampaignKeyError,
    GrowthCampaignLifecycleUseCase,
    GrowthCampaignListResult,
    GrowthCampaignRecord,
    NewGrowthCampaign,
)

ADMIN_ID = UUID("00000000-0000-0000-0000-000000000111")
CAMPAIGN_ID = UUID("00000000-0000-0000-0000-000000000222")
NOW = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


class FakeGrowthCampaignRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, GrowthCampaignRecord] = {}

    async def create_campaign(self, data: NewGrowthCampaign) -> GrowthCampaignRecord:
        if any(record.campaign_key == data.campaign_key for record in self.records.values()):
            raise DuplicateCampaignKeyError("campaign_key_already_exists")
        record = GrowthCampaignRecord(
            id=CAMPAIGN_ID if not self.records else uuid4(),
            campaign_key=data.campaign_key,
            name=data.name,
            description=data.description,
            status="draft",
            priority=data.priority,
            starts_at=data.starts_at,
            expires_at=data.expires_at,
            stacking_mode=data.stacking_mode,
            stacking_group=data.stacking_group,
            current_version=1,
            created_by_admin_id=data.created_by_admin_id,
            updated_by_admin_id=None,
            published_at=None,
            paused_at=None,
            archived_at=None,
            created_at=NOW,
            updated_at=NOW,
        )
        self.records[record.id] = record
        return record

    async def get_campaign(self, campaign_id: UUID) -> GrowthCampaignRecord | None:
        return self.records.get(campaign_id)

    async def get_campaign_by_key(self, campaign_key: str) -> GrowthCampaignRecord | None:
        return next((record for record in self.records.values() if record.campaign_key == campaign_key), None)

    async def list_campaigns(
        self,
        *,
        status: str | None,
        campaign_key: str | None,
        offset: int,
        limit: int,
        sort: str,
    ) -> GrowthCampaignListResult:
        items = list(self.records.values())
        if status:
            items = [record for record in items if record.status == status]
        if campaign_key:
            items = [record for record in items if campaign_key in record.campaign_key]
        if sort == "-created_at":
            items.reverse()
        return GrowthCampaignListResult(
            items=tuple(items[offset : offset + limit]),
            total=len(items),
            offset=offset,
            limit=limit,
        )

    async def save_campaign(self, record: GrowthCampaignRecord) -> GrowthCampaignRecord:
        self.records[record.id] = record
        return record


async def _create_campaign(repo: FakeGrowthCampaignRepository, **overrides) -> GrowthCampaignRecord:
    return await GrowthCampaignLifecycleUseCase(repo).create_campaign(
        campaign_key=overrides.pop("campaign_key", "pro-free-invites-2026"),
        name=overrides.pop("name", "PRO 100% + invites"),
        description=overrides.pop("description", "Internal acceptance campaign"),
        priority=overrides.pop("priority", 100),
        starts_at=overrides.pop("starts_at", None),
        expires_at=overrides.pop("expires_at", None),
        stacking_mode=overrides.pop("stacking_mode", "exclusive"),
        stacking_group=overrides.pop("stacking_group", "checkout_discount"),
        created_by_admin_id=ADMIN_ID,
    )


@pytest.mark.asyncio
async def test_create_campaign_normalizes_key_and_starts_as_draft() -> None:
    repo = FakeGrowthCampaignRepository()

    record = await _create_campaign(repo, campaign_key="  PRO-Free-Invites-2026  ")

    assert record.campaign_key == "pro-free-invites-2026"
    assert record.status == "draft"
    assert record.current_version == 1
    assert record.created_by_admin_id == ADMIN_ID


@pytest.mark.asyncio
async def test_create_campaign_rejects_duplicate_key_before_insert() -> None:
    repo = FakeGrowthCampaignRepository()
    await _create_campaign(repo)

    with pytest.raises(DuplicateCampaignKeyError):
        await _create_campaign(repo)

    assert len(repo.records) == 1


@pytest.mark.asyncio
async def test_campaign_schedule_and_shape_validation_fail_before_persistence() -> None:
    repo = FakeGrowthCampaignRepository()

    with pytest.raises(CampaignValidationError, match="campaign_schedule_invalid"):
        await _create_campaign(
            repo,
            starts_at=NOW + timedelta(days=2),
            expires_at=NOW + timedelta(days=1),
        )

    with pytest.raises(CampaignValidationError, match="stacking_mode_invalid"):
        await _create_campaign(repo, campaign_key="bad-stacking", stacking_mode="free_for_all")

    assert repo.records == {}


@pytest.mark.asyncio
async def test_update_draft_campaign_uses_expected_version_and_increments_version() -> None:
    repo = FakeGrowthCampaignRepository()
    record = await _create_campaign(repo)

    updated = await GrowthCampaignLifecycleUseCase(repo).update_draft_campaign(
        campaign_id=record.id,
        changes={"name": "Renamed campaign", "priority": 101},
        actor_admin_id=ADMIN_ID,
        expected_version=1,
    )

    assert updated.name == "Renamed campaign"
    assert updated.priority == 101
    assert updated.current_version == 2
    assert updated.updated_by_admin_id == ADMIN_ID


@pytest.mark.asyncio
async def test_update_draft_campaign_rejects_stale_expected_version_without_mutation() -> None:
    repo = FakeGrowthCampaignRepository()
    record = await _create_campaign(repo)

    with pytest.raises(CampaignVersionConflictError) as exc_info:
        await GrowthCampaignLifecycleUseCase(repo).update_draft_campaign(
            campaign_id=record.id,
            changes={"name": "Late editor"},
            actor_admin_id=ADMIN_ID,
            expected_version=2,
        )

    assert exc_info.value.expected_version == 2
    assert exc_info.value.actual_version == 1
    assert repo.records[record.id].name == record.name


@pytest.mark.asyncio
async def test_publish_sets_active_or_scheduled_and_active_patch_is_immutable() -> None:
    repo = FakeGrowthCampaignRepository()
    active_record = await _create_campaign(repo, campaign_key="active-now")
    scheduled_record = await _create_campaign(
        repo,
        campaign_key="scheduled-later",
        starts_at=NOW + timedelta(days=1),
    )
    use_case = GrowthCampaignLifecycleUseCase(repo)

    active = await use_case.publish_campaign(
        campaign_id=active_record.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW,
    )
    scheduled = await use_case.publish_campaign(
        campaign_id=scheduled_record.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW,
    )

    assert active.status == "active"
    assert scheduled.status == "scheduled"
    with pytest.raises(CampaignTransitionError, match="active_campaign_immutable"):
        await use_case.update_draft_campaign(
            campaign_id=active.id,
            changes={"name": "Forbidden mutation"},
            actor_admin_id=ADMIN_ID,
            expected_version=1,
        )
    assert repo.records[active.id].name == "PRO 100% + invites"


@pytest.mark.asyncio
async def test_pause_resume_revoke_and_archive_follow_state_machine() -> None:
    repo = FakeGrowthCampaignRepository()
    record = await _create_campaign(repo)
    use_case = GrowthCampaignLifecycleUseCase(repo)

    active = await use_case.publish_campaign(
        campaign_id=record.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW,
    )
    paused = await use_case.pause_campaign(
        campaign_id=active.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW + timedelta(minutes=1),
    )
    resumed = await use_case.resume_campaign(
        campaign_id=paused.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW + timedelta(minutes=2),
    )
    revoked = await use_case.revoke_campaign(
        campaign_id=resumed.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW + timedelta(minutes=3),
    )
    archived = await use_case.archive_campaign(
        campaign_id=revoked.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW + timedelta(minutes=4),
    )

    assert paused.status == "paused"
    assert paused.paused_at == NOW + timedelta(minutes=1)
    assert resumed.status == "active"
    assert revoked.status == "revoked"
    assert archived.status == "archived"
    assert archived.archived_at == NOW + timedelta(minutes=4)


@pytest.mark.asyncio
async def test_archive_active_campaign_requires_pause_or_revoke_first() -> None:
    repo = FakeGrowthCampaignRepository()
    record = await _create_campaign(repo)
    use_case = GrowthCampaignLifecycleUseCase(repo)
    active = await use_case.publish_campaign(
        campaign_id=record.id,
        actor_admin_id=ADMIN_ID,
        expected_version=1,
        now=NOW,
    )

    with pytest.raises(CampaignTransitionError, match="campaign_archive_requires_non_active"):
        await use_case.archive_campaign(
            campaign_id=active.id,
            actor_admin_id=ADMIN_ID,
            expected_version=1,
            now=NOW,
        )
