from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    REVOKED = "revoked"
    EXPIRED = "expired"


class GrowthCampaignNotFoundError(LookupError):
    pass


class DuplicateCampaignKeyError(ValueError):
    pass


class CampaignValidationError(ValueError):
    pass


class CampaignTransitionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class CampaignVersionConflictError(ValueError):
    def __init__(self, *, expected_version: int, actual_version: int) -> None:
        super().__init__("campaign_version_conflict")
        self.expected_version = expected_version
        self.actual_version = actual_version


@dataclass(frozen=True, slots=True)
class GrowthCampaignRecord:
    id: UUID
    campaign_key: str
    name: str
    description: str | None
    status: str
    priority: int
    starts_at: datetime | None
    expires_at: datetime | None
    stacking_mode: str
    stacking_group: str | None
    current_version: int
    created_by_admin_id: UUID
    updated_by_admin_id: UUID | None
    published_at: datetime | None
    paused_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class NewGrowthCampaign:
    campaign_key: str
    name: str
    description: str | None
    priority: int
    starts_at: datetime | None
    expires_at: datetime | None
    stacking_mode: str
    stacking_group: str | None
    created_by_admin_id: UUID


@dataclass(frozen=True, slots=True)
class GrowthCampaignListResult:
    items: tuple[GrowthCampaignRecord, ...]
    total: int
    offset: int
    limit: int


class GrowthCampaignRepository(Protocol):
    async def create_campaign(self, data: NewGrowthCampaign) -> GrowthCampaignRecord:
        raise NotImplementedError

    async def get_campaign(self, campaign_id: UUID) -> GrowthCampaignRecord | None:
        raise NotImplementedError

    async def get_campaign_by_key(self, campaign_key: str) -> GrowthCampaignRecord | None:
        raise NotImplementedError

    async def list_campaigns(
        self,
        *,
        status: str | None,
        campaign_key: str | None,
        offset: int,
        limit: int,
        sort: str,
    ) -> GrowthCampaignListResult:
        raise NotImplementedError

    async def save_campaign(self, record: GrowthCampaignRecord) -> GrowthCampaignRecord:
        raise NotImplementedError


_CAMPAIGN_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")
_STACKING_MODES = frozenset({"exclusive", "allow_with_same_campaign", "benefits_only_append", "max_discount"})
_PATCH_FIELDS = frozenset(
    {
        "name",
        "description",
        "priority",
        "starts_at",
        "expires_at",
        "stacking_mode",
        "stacking_group",
    }
)


class GrowthCampaignLifecycleUseCase:
    def __init__(self, repository: GrowthCampaignRepository) -> None:
        self._repository = repository

    async def create_campaign(
        self,
        *,
        campaign_key: str,
        name: str,
        description: str | None,
        priority: int,
        starts_at: datetime | None,
        expires_at: datetime | None,
        stacking_mode: str,
        stacking_group: str | None,
        created_by_admin_id: UUID,
    ) -> GrowthCampaignRecord:
        normalized_key = _normalize_campaign_key(campaign_key)
        if await self._repository.get_campaign_by_key(normalized_key) is not None:
            raise DuplicateCampaignKeyError("campaign_key_already_exists")
        starts_at = _normalize_optional_datetime(starts_at, "starts_at")
        expires_at = _normalize_optional_datetime(expires_at, "expires_at")
        _validate_campaign_shape(
            campaign_key=normalized_key,
            name=name,
            priority=priority,
            starts_at=starts_at,
            expires_at=expires_at,
            stacking_mode=stacking_mode,
            stacking_group=stacking_group,
        )
        return await self._repository.create_campaign(
            NewGrowthCampaign(
                campaign_key=normalized_key,
                name=name.strip(),
                description=_blank_to_none(description),
                priority=priority,
                starts_at=starts_at,
                expires_at=expires_at,
                stacking_mode=stacking_mode,
                stacking_group=_blank_to_none(stacking_group),
                created_by_admin_id=created_by_admin_id,
            )
        )

    async def list_campaigns(
        self,
        *,
        status: str | None = None,
        campaign_key: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str = "-created_at",
    ) -> GrowthCampaignListResult:
        if status is not None:
            _coerce_status(status)
        if offset < 0:
            raise CampaignValidationError("offset_must_be_non_negative")
        if limit < 1 or limit > 100:
            raise CampaignValidationError("limit_must_be_between_1_and_100")
        return await self._repository.list_campaigns(
            status=status,
            campaign_key=_blank_to_none(campaign_key),
            offset=offset,
            limit=limit,
            sort=sort,
        )

    async def get_campaign(self, campaign_id: UUID) -> GrowthCampaignRecord:
        return await self._require_campaign(campaign_id)

    async def update_draft_campaign(
        self,
        *,
        campaign_id: UUID,
        changes: Mapping[str, Any],
        actor_admin_id: UUID,
        expected_version: int | None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status != CampaignStatus.DRAFT.value:
            raise CampaignTransitionError("active_campaign_immutable")
        unknown_fields = set(changes) - _PATCH_FIELDS
        if unknown_fields:
            raise CampaignValidationError(f"unsupported_campaign_fields:{','.join(sorted(unknown_fields))}")

        next_values = _campaign_to_dict(current)
        for key, value in changes.items():
            next_values[key] = value
        starts_at = _normalize_optional_datetime(next_values["starts_at"], "starts_at")
        expires_at = _normalize_optional_datetime(next_values["expires_at"], "expires_at")
        _validate_campaign_shape(
            campaign_key=current.campaign_key,
            name=str(next_values["name"]),
            priority=int(next_values["priority"]),
            starts_at=starts_at,
            expires_at=expires_at,
            stacking_mode=str(next_values["stacking_mode"]),
            stacking_group=next_values["stacking_group"],
        )
        now = datetime.now(UTC)
        updated = replace(
            current,
            name=str(next_values["name"]).strip(),
            description=_blank_to_none(next_values["description"]),
            priority=int(next_values["priority"]),
            starts_at=starts_at,
            expires_at=expires_at,
            stacking_mode=str(next_values["stacking_mode"]),
            stacking_group=_blank_to_none(next_values["stacking_group"]),
            current_version=current.current_version + 1,
            updated_by_admin_id=actor_admin_id,
            updated_at=now,
        )
        return await self._repository.save_campaign(updated)

    async def publish_campaign(
        self,
        *,
        campaign_id: UUID,
        actor_admin_id: UUID,
        expected_version: int | None,
        now: datetime | None = None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status != CampaignStatus.DRAFT.value:
            raise CampaignTransitionError("campaign_publish_requires_draft")
        now = _normalize_optional_datetime(now, "now") or datetime.now(UTC)
        if current.expires_at is not None and current.expires_at <= now:
            raise CampaignValidationError("campaign_expires_before_publish")
        next_status = (
            CampaignStatus.SCHEDULED if current.starts_at and current.starts_at > now else CampaignStatus.ACTIVE
        )
        return await self._repository.save_campaign(
            replace(
                current,
                status=next_status.value,
                published_at=now,
                updated_by_admin_id=actor_admin_id,
                updated_at=now,
            )
        )

    async def pause_campaign(
        self,
        *,
        campaign_id: UUID,
        actor_admin_id: UUID,
        expected_version: int | None,
        now: datetime | None = None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status not in {CampaignStatus.ACTIVE.value, CampaignStatus.SCHEDULED.value}:
            raise CampaignTransitionError("campaign_pause_requires_active_or_scheduled")
        now = _normalize_optional_datetime(now, "now") or datetime.now(UTC)
        return await self._repository.save_campaign(
            replace(
                current,
                status=CampaignStatus.PAUSED.value,
                paused_at=now,
                updated_by_admin_id=actor_admin_id,
                updated_at=now,
            )
        )

    async def resume_campaign(
        self,
        *,
        campaign_id: UUID,
        actor_admin_id: UUID,
        expected_version: int | None,
        now: datetime | None = None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status != CampaignStatus.PAUSED.value:
            raise CampaignTransitionError("campaign_resume_requires_paused")
        now = _normalize_optional_datetime(now, "now") or datetime.now(UTC)
        next_status = (
            CampaignStatus.SCHEDULED if current.starts_at and current.starts_at > now else CampaignStatus.ACTIVE
        )
        return await self._repository.save_campaign(
            replace(
                current,
                status=next_status.value,
                updated_by_admin_id=actor_admin_id,
                updated_at=now,
            )
        )

    async def archive_campaign(
        self,
        *,
        campaign_id: UUID,
        actor_admin_id: UUID,
        expected_version: int | None,
        now: datetime | None = None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status == CampaignStatus.ACTIVE.value:
            raise CampaignTransitionError("campaign_archive_requires_non_active")
        if current.status == CampaignStatus.ARCHIVED.value:
            return current
        now = _normalize_optional_datetime(now, "now") or datetime.now(UTC)
        return await self._repository.save_campaign(
            replace(
                current,
                status=CampaignStatus.ARCHIVED.value,
                archived_at=now,
                updated_by_admin_id=actor_admin_id,
                updated_at=now,
            )
        )

    async def revoke_campaign(
        self,
        *,
        campaign_id: UUID,
        actor_admin_id: UUID,
        expected_version: int | None,
        now: datetime | None = None,
    ) -> GrowthCampaignRecord:
        current = await self._require_campaign(campaign_id)
        _check_expected_version(current, expected_version)
        if current.status not in {
            CampaignStatus.ACTIVE.value,
            CampaignStatus.SCHEDULED.value,
            CampaignStatus.PAUSED.value,
        }:
            raise CampaignTransitionError("campaign_revoke_requires_active_scheduled_or_paused")
        now = _normalize_optional_datetime(now, "now") or datetime.now(UTC)
        return await self._repository.save_campaign(
            replace(
                current,
                status=CampaignStatus.REVOKED.value,
                updated_by_admin_id=actor_admin_id,
                updated_at=now,
            )
        )

    async def _require_campaign(self, campaign_id: UUID) -> GrowthCampaignRecord:
        record = await self._repository.get_campaign(campaign_id)
        if record is None:
            raise GrowthCampaignNotFoundError("growth_campaign_not_found")
        return record


def _campaign_to_dict(record: GrowthCampaignRecord) -> dict[str, Any]:
    return {
        "name": record.name,
        "description": record.description,
        "priority": record.priority,
        "starts_at": record.starts_at,
        "expires_at": record.expires_at,
        "stacking_mode": record.stacking_mode,
        "stacking_group": record.stacking_group,
    }


def campaign_audit_snapshot(record: GrowthCampaignRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "campaign_key": record.campaign_key,
        "name": record.name,
        "status": record.status,
        "priority": record.priority,
        "starts_at": record.starts_at.isoformat() if record.starts_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "stacking_mode": record.stacking_mode,
        "stacking_group": record.stacking_group,
        "current_version": record.current_version,
    }


def _check_expected_version(record: GrowthCampaignRecord, expected_version: int | None) -> None:
    if expected_version is None:
        return
    if expected_version != record.current_version:
        raise CampaignVersionConflictError(
            expected_version=expected_version,
            actual_version=record.current_version,
        )


def _validate_campaign_shape(
    *,
    campaign_key: str,
    name: str,
    priority: int,
    starts_at: datetime | None,
    expires_at: datetime | None,
    stacking_mode: str,
    stacking_group: str | None,
) -> None:
    if not _CAMPAIGN_KEY_RE.fullmatch(campaign_key):
        raise CampaignValidationError("campaign_key_format_invalid")
    if not name or not name.strip():
        raise CampaignValidationError("campaign_name_required")
    if priority < 0:
        raise CampaignValidationError("priority_must_be_non_negative")
    if expires_at is not None and starts_at is not None and expires_at <= starts_at:
        raise CampaignValidationError("campaign_schedule_invalid")
    if stacking_mode not in _STACKING_MODES:
        raise CampaignValidationError("stacking_mode_invalid")
    if stacking_group is not None and len(stacking_group) > 80:
        raise CampaignValidationError("stacking_group_too_long")


def _normalize_campaign_key(value: str) -> str:
    return value.strip().lower()


def _normalize_optional_datetime(value: object, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise CampaignValidationError(f"{field_name}_invalid")
    if value.tzinfo is None:
        raise CampaignValidationError(f"{field_name}_must_be_timezone_aware")
    return value.astimezone(UTC)


def _blank_to_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_status(value: str) -> CampaignStatus:
    try:
        return CampaignStatus(value)
    except ValueError as exc:
        raise CampaignValidationError("campaign_status_invalid") from exc
