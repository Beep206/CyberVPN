"""Infrastructure repository for FCM tokens table."""

from typing import Literal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.fcm_token import FCMToken
from src.domain.repositories.fcm_token_repository import FCMTokenRepository
from src.infrastructure.database.models.fcm_token_model import FCMTokenModel


class FCMTokenRepositoryImpl(FCMTokenRepository):
    """SQLAlchemy implementation of FCM token repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        user_id: UUID,
        token: str,
        device_id: str,
        platform: Literal["android", "ios"],
    ) -> FCMToken:
        """Insert or update FCM token using PostgreSQL ON CONFLICT."""
        stmt = (
            insert(FCMTokenModel)
            .values(
                user_id=user_id,
                token=token,
                device_id=device_id,
                platform=platform,
            )
            .on_conflict_do_update(
                constraint="uq_fcm_tokens_user_device",
                set_={
                    "token": token,
                    "platform": platform,
                    "updated_at": FCMTokenModel.updated_at,
                },
            )
            .returning(FCMTokenModel)
        )

        result = await self._session.execute(stmt)
        model = result.scalar_one()
        await self._session.flush()

        return self._model_to_entity(model)

    async def delete(
        self,
        user_id: UUID,
        device_id: str,
    ) -> None:
        """Delete FCM token for a specific device."""
        stmt = select(FCMTokenModel).where(
            and_(
                FCMTokenModel.user_id == user_id,
                FCMTokenModel.device_id == device_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def get_by_user(
        self,
        user_id: UUID,
    ) -> list[FCMToken]:
        """Get all FCM tokens for a user (all devices)."""
        stmt = (
            select(FCMTokenModel)
            .where(FCMTokenModel.user_id == user_id)
            .order_by(FCMTokenModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_entity(m) for m in models]

    async def get_by_device(
        self,
        user_id: UUID,
        device_id: str,
    ) -> FCMToken | None:
        """Get FCM token for a specific device."""
        stmt = select(FCMTokenModel).where(
            and_(
                FCMTokenModel.user_id == user_id,
                FCMTokenModel.device_id == device_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._model_to_entity(model)

    @staticmethod
    def _model_to_entity(model: FCMTokenModel) -> FCMToken:
        """Convert ORM model to domain entity."""
        return FCMToken(
            id=model.id,
            user_id=model.user_id,
            token=model.token,
            device_id=model.device_id,
            platform=model.platform,  # type: ignore[arg-type]
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
