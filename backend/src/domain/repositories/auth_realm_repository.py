from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.auth_realm import AuthRealm
from src.domain.entities.principal_session import PrincipalSession


class AuthRealmRepository(ABC):
    @abstractmethod
    async def list_realms(self) -> list[AuthRealm]: ...

    @abstractmethod
    async def get_realm_by_id(self, id: UUID) -> AuthRealm | None: ...

    @abstractmethod
    async def get_realm_by_key(self, realm_key: str) -> AuthRealm | None: ...

    @abstractmethod
    async def get_realm_by_storefront_host(self, host: str) -> AuthRealm | None: ...

    @abstractmethod
    async def get_default_realm(self, realm_type: str) -> AuthRealm | None: ...

    @abstractmethod
    async def create_realm(self, realm: AuthRealm) -> AuthRealm: ...

    @abstractmethod
    async def create_principal_session(self, principal_session: PrincipalSession) -> PrincipalSession: ...
