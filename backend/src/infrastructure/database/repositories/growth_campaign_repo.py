from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.growth_campaigns.admin_lifecycle import (
    DuplicateCampaignKeyError,
    GrowthCampaignListResult,
    GrowthCampaignRecord,
    NewGrowthCampaign,
)
from src.infrastructure.database.models.growth_campaign_model import GrowthCampaignModel


class SqlAlchemyGrowthCampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_campaign(self, data: NewGrowthCampaign) -> GrowthCampaignRecord:
        model = GrowthCampaignModel(
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
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _is_campaign_key_violation(exc):
                raise DuplicateCampaignKeyError("campaign_key_already_exists") from exc
            raise
        await self._session.refresh(model)
        return _record(model)

    async def get_campaign(self, campaign_id: UUID) -> GrowthCampaignRecord | None:
        stmt = select(GrowthCampaignModel).where(GrowthCampaignModel.id == campaign_id).with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return _record(model) if model is not None else None

    async def get_campaign_by_key(self, campaign_key: str) -> GrowthCampaignRecord | None:
        result = await self._session.execute(
            select(GrowthCampaignModel).where(GrowthCampaignModel.campaign_key == campaign_key)
        )
        model = result.scalars().first()
        return _record(model) if model is not None else None

    async def list_campaigns(
        self,
        *,
        status: str | None,
        campaign_key: str | None,
        offset: int,
        limit: int,
        sort: str,
    ) -> GrowthCampaignListResult:
        predicates = []
        if status is not None:
            predicates.append(GrowthCampaignModel.status == status)
        if campaign_key:
            predicates.append(GrowthCampaignModel.campaign_key.ilike(f"%{campaign_key}%"))

        query = select(GrowthCampaignModel).where(*predicates)
        count_result = await self._session.execute(select(func.count()).select_from(query.subquery()))
        total = int(count_result.scalar_one())
        sort_desc = sort.startswith("-")
        sort_field = sort[1:] if sort_desc else sort
        sort_columns = {
            "created_at": GrowthCampaignModel.created_at,
            "updated_at": GrowthCampaignModel.updated_at,
        }
        sort_column = sort_columns.get(sort_field, GrowthCampaignModel.created_at)
        order_by = sort_column.desc() if sort_desc else sort_column.asc()
        result = await self._session.execute(query.order_by(order_by).offset(offset).limit(limit))
        return GrowthCampaignListResult(
            items=tuple(_record(model) for model in result.scalars().all()),
            total=total,
            offset=offset,
            limit=limit,
        )

    async def save_campaign(self, record: GrowthCampaignRecord) -> GrowthCampaignRecord:
        model = await self._session.get(GrowthCampaignModel, record.id)
        if model is None:
            raise LookupError("growth_campaign_not_found")
        model.name = record.name
        model.description = record.description
        model.status = record.status
        model.priority = record.priority
        model.starts_at = record.starts_at
        model.expires_at = record.expires_at
        model.stacking_mode = record.stacking_mode
        model.stacking_group = record.stacking_group
        model.current_version = record.current_version
        model.updated_by_admin_id = record.updated_by_admin_id
        model.published_at = record.published_at
        model.paused_at = record.paused_at
        model.archived_at = record.archived_at
        model.updated_at = record.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return _record(model)


def _record(model: GrowthCampaignModel) -> GrowthCampaignRecord:
    return GrowthCampaignRecord(
        id=model.id,
        campaign_key=model.campaign_key,
        name=model.name,
        description=model.description,
        status=model.status,
        priority=model.priority,
        starts_at=model.starts_at,
        expires_at=model.expires_at,
        stacking_mode=model.stacking_mode,
        stacking_group=model.stacking_group,
        current_version=model.current_version,
        created_by_admin_id=model.created_by_admin_id,
        updated_by_admin_id=model.updated_by_admin_id,
        published_at=model.published_at,
        paused_at=model.paused_at,
        archived_at=model.archived_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _is_campaign_key_violation(exc: IntegrityError) -> bool:
    return "campaign_key" in str(exc).lower()
