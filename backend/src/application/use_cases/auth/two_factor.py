from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.totp.totp_service import TOTPService


class TwoFactorUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AdminUserRepository(session)
        self._totp = TOTPService()

    async def setup(self, user_id: UUID) -> dict:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        secret = self._totp.generate_secret()
        uri = self._totp.generate_qr_uri(secret, user.email or user.login, "CyberVPN")

        user.totp_secret = secret
        await self._repo.update(user)

        return {"secret": secret, "qr_uri": uri}

    async def verify_and_enable(self, user_id: UUID, code: str) -> bool:
        user = await self._repo.get_by_id(user_id)
        if not user or not user.totp_secret:
            return False

        if self._totp.verify_code(user.totp_secret, code):
            user.totp_enabled = True
            await self._repo.update(user)
            return True
        return False

    async def verify_code(self, user_id: UUID, code: str) -> bool:
        user = await self._repo.get_by_id(user_id)
        if not user or not user.totp_secret or not user.totp_enabled:
            return False
        return self._totp.verify_code(user.totp_secret, code)

    async def disable(self, user_id: UUID) -> None:
        user = await self._repo.get_by_id(user_id)
        if user:
            user.totp_enabled = False
            user.totp_secret = None
            await self._repo.update(user)
