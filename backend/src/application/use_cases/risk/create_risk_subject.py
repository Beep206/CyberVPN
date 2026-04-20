from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import PrincipalClass
from src.infrastructure.database.models.risk_subject_model import RiskSubjectModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository
from src.infrastructure.database.repositories.auth_realm_repo import AuthRealmRepository
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository
from src.infrastructure.database.repositories.risk_subject_repo import RiskSubjectGraphRepository
from src.infrastructure.database.repositories.storefront_repo import StorefrontRepository


class CreateRiskSubjectUseCase:
    def __init__(self, session: AsyncSession) -> None:
        self._risk_repo = RiskSubjectGraphRepository(session)
        self._realm_repo = AuthRealmRepository(session)
        self._storefront_repo = StorefrontRepository(session)
        self._mobile_user_repo = MobileUserRepository(session)
        self._admin_user_repo = AdminUserRepository(session)

    async def execute(
        self,
        *,
        principal_class: PrincipalClass | str,
        principal_subject: UUID,
        auth_realm_id: UUID | None,
        storefront_id: UUID | None,
        status: str = "active",
        risk_level: str = "low",
        metadata: dict | None = None,
    ) -> RiskSubjectModel:
        normalized_principal_class = PrincipalClass(principal_class)
        if auth_realm_id is not None and await self._realm_repo.get_realm_by_id(auth_realm_id) is None:
            raise ValueError("Auth realm not found")

        storefront = None
        if storefront_id is not None:
            storefront = await self._storefront_repo.get_storefront_by_id(storefront_id)
            if storefront is None:
                raise ValueError("Storefront not found")

        principal_realm_id: UUID | None = None
        if normalized_principal_class == PrincipalClass.CUSTOMER:
            principal = await self._mobile_user_repo.get_by_id(principal_subject)
            if principal is None:
                raise ValueError("Customer principal not found")
            principal_realm_id = principal.auth_realm_id
        elif normalized_principal_class in {PrincipalClass.ADMIN, PrincipalClass.PARTNER_OPERATOR}:
            principal = await self._admin_user_repo.get_by_id(principal_subject)
            if principal is None:
                raise ValueError("Admin principal not found")
            principal_realm_id = principal.auth_realm_id
        else:
            raise ValueError("Unsupported principal_class for risk subjects")

        resolved_auth_realm_id = auth_realm_id or principal_realm_id
        if auth_realm_id is not None and principal_realm_id is not None and auth_realm_id != principal_realm_id:
            raise ValueError("Risk subject auth_realm_id must match the principal realm")
        if storefront is not None and storefront.auth_realm_id and resolved_auth_realm_id:
            if storefront.auth_realm_id != resolved_auth_realm_id:
                raise ValueError("Storefront realm binding must match the risk subject realm")

        existing = await self._risk_repo.get_subject_by_principal(
            principal_class=normalized_principal_class.value,
            principal_subject=str(principal_subject),
            auth_realm_id=resolved_auth_realm_id,
        )
        if existing is not None:
            raise ValueError("Risk subject already exists for this principal in the resolved realm")

        model = RiskSubjectModel(
            principal_class=normalized_principal_class.value,
            principal_subject=str(principal_subject),
            auth_realm_id=resolved_auth_realm_id,
            storefront_id=storefront_id,
            status=status,
            risk_level=risk_level,
            metadata_payload=metadata or {},
        )
        return await self._risk_repo.create_subject(model)
