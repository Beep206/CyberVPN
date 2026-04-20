"""Create partner workspace roots and optional owner memberships."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.models.partner_account_user_model import PartnerAccountUserModel
from src.infrastructure.database.models.partner_model import PartnerAccountModel
from src.infrastructure.database.repositories.partner_account_repository import PartnerAccountRepository


class CreatePartnerWorkspaceUseCase:
    def __init__(self, session: AsyncSession, partner_account_repo: PartnerAccountRepository) -> None:
        self._session = session
        self._repo = partner_account_repo

    async def execute(
        self,
        *,
        display_name: str,
        account_key: str | None = None,
        initial_status: str = "active",
        legacy_owner_user_id: UUID | None = None,
        owner_admin_user_id: UUID | None = None,
        created_by_admin_user_id: UUID | None = None,
    ) -> tuple[PartnerAccountModel, PartnerAccountUserModel | None]:
        await self._repo.ensure_builtin_roles()

        legacy_owner = None
        if legacy_owner_user_id is not None:
            legacy_owner = await self._session.get(MobileUserModel, legacy_owner_user_id)
            if legacy_owner is None:
                msg = f"Legacy partner owner not found: {legacy_owner_user_id}"
                raise ValueError(msg)

        if owner_admin_user_id is not None:
            operator = await self._session.get(AdminUserModel, owner_admin_user_id)
            if operator is None:
                msg = f"Partner workspace operator not found: {owner_admin_user_id}"
                raise ValueError(msg)

        if legacy_owner_user_id is not None:
            existing = await self._repo.get_account_by_legacy_owner_user_id(legacy_owner_user_id)
            if existing is not None:
                membership = None
                if owner_admin_user_id is not None:
                    membership = await self._ensure_owner_membership(
                        existing.id,
                        owner_admin_user_id,
                        created_by_admin_user_id,
                    )
                return existing, membership

        resolved_key = await self._resolve_account_key(account_key, display_name)
        account = PartnerAccountModel(
            account_key=resolved_key,
            display_name=display_name,
            legacy_owner_user_id=legacy_owner_user_id,
            created_by_admin_user_id=created_by_admin_user_id,
            status=initial_status,
        )
        account = await self._repo.create_account(account)

        if legacy_owner is not None:
            legacy_owner.is_partner = True
            if legacy_owner.partner_promoted_at is None:
                legacy_owner.partner_promoted_at = datetime.now(UTC)
            legacy_owner.partner_account_id = account.id
            await self._session.flush()

        membership = None
        if owner_admin_user_id is not None:
            membership = await self._ensure_owner_membership(account.id, owner_admin_user_id, created_by_admin_user_id)

        return account, membership

    async def _ensure_owner_membership(
        self,
        partner_account_id: UUID,
        owner_admin_user_id: UUID,
        created_by_admin_user_id: UUID | None,
    ) -> PartnerAccountUserModel:
        existing_membership = await self._repo.get_membership(partner_account_id, owner_admin_user_id)
        owner_role = await self._repo.get_role_by_key("owner")
        if owner_role is None:
            msg = "Builtin owner role is missing"
            raise ValueError(msg)

        if existing_membership is not None:
            existing_membership.role_id = owner_role.id
            existing_membership.membership_status = "active"
            return await self._repo.update_membership(existing_membership)

        membership = PartnerAccountUserModel(
            partner_account_id=partner_account_id,
            admin_user_id=owner_admin_user_id,
            role_id=owner_role.id,
            membership_status="active",
            invited_by_admin_user_id=created_by_admin_user_id,
        )
        return await self._repo.create_membership(membership)

    async def _resolve_account_key(self, account_key: str | None, display_name: str) -> str:
        if account_key:
            normalized = self._normalize_key(account_key)
            existing = await self._repo.get_account_by_key(normalized)
            if existing is not None:
                msg = f"Partner workspace key already exists: {normalized}"
                raise ValueError(msg)
            return normalized

        base = self._normalize_key(display_name) or "partner-workspace"
        candidate = base
        while await self._repo.get_account_by_key(candidate) is not None:
            candidate = f"{base}-{secrets.token_hex(2)}"
        return candidate

    @staticmethod
    def _normalize_key(raw_value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", raw_value.lower()).strip("-")
        return normalized[:50]
