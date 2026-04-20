from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.partner import PartnerAccount
from src.domain.entities.partner_account_user import PartnerAccountUser


class PartnerAccountRepository(ABC):
    @abstractmethod
    async def get_account_by_id(self, id: UUID) -> PartnerAccount | None: ...

    @abstractmethod
    async def get_account_by_key(self, account_key: str) -> PartnerAccount | None: ...

    @abstractmethod
    async def get_account_by_legacy_owner_user_id(self, user_id: UUID) -> PartnerAccount | None: ...

    @abstractmethod
    async def create_account(self, account: PartnerAccount) -> PartnerAccount: ...

    @abstractmethod
    async def get_membership(self, partner_account_id: UUID, admin_user_id: UUID) -> PartnerAccountUser | None: ...

    @abstractmethod
    async def create_membership(self, membership: PartnerAccountUser) -> PartnerAccountUser: ...
