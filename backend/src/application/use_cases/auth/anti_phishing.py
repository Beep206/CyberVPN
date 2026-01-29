from uuid import UUID

from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class AntiPhishingUseCase:
    def __init__(self, repo: AdminUserRepository) -> None:
        self._repo = repo

    async def set_code(self, user_id: UUID, code: str) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        user.anti_phishing_code = code
        await self._repo.update(user)

    async def get_code(self, user_id: UUID) -> str | None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            return None
        return user.anti_phishing_code

    async def remove_code(self, user_id: UUID) -> None:
        user = await self._repo.get_by_id(user_id)
        if user:
            user.anti_phishing_code = None
            await self._repo.update(user)
