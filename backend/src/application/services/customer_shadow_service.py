"""Customer web to mobile account shadow synchronization."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.public_uid_allocator import allocate_public_uid
from src.application.use_cases.auth_realms import RealmResolution
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.mobile_user_model import MobileUserModel
from src.infrastructure.database.repositories.mobile_user_repo import MobileUserRepository

logger = logging.getLogger(__name__)


async def ensure_customer_web_mobile_shadow(
    *,
    db: AsyncSession,
    user: AdminUserModel,
    current_realm: RealmResolution,
) -> MobileUserModel | None:
    """Mirror customer web accounts into mobile_users for B2C resource APIs."""

    if current_realm.realm_type != "customer" or not user.email or not user.password_hash:
        return None

    repo = MobileUserRepository(db)
    existing = await repo.get_by_id(user.id)
    if existing is not None:
        changed = False
        if existing.auth_realm_id != current_realm.auth_realm.id:
            existing.auth_realm_id = current_realm.auth_realm.id
            changed = True
        if existing.email != user.email:
            email_owner = await repo.get_by_email(user.email)
            if email_owner is not None and email_owner.id != user.id:
                logger.warning(
                    "customer_shadow_email_conflict",
                    extra={"admin_user_id": str(user.id), "mobile_user_id": str(email_owner.id)},
                )
            else:
                existing.email = user.email
                changed = True
        if existing.username is None:
            existing.username = user.login[:50]
            changed = True
        if existing.password_hash != (user.password_hash or existing.password_hash):
            existing.password_hash = user.password_hash or existing.password_hash
            changed = True
        if existing.is_active != user.is_active:
            existing.is_active = user.is_active
            changed = True
        if user.is_active and existing.status == "deleted":
            existing.status = user.status or "active"
            changed = True
        if changed:
            return await repo.update(existing)
        return existing

    email_owner = await repo.get_by_email(user.email)
    if email_owner is not None and email_owner.id != user.id:
        logger.warning(
            "customer_shadow_email_conflict",
            extra={"admin_user_id": str(user.id), "mobile_user_id": str(email_owner.id)},
        )
        return None

    username = user.login[:50]
    username_owner = await repo.get_by_username(username)
    if username_owner is not None and username_owner.id != user.id:
        username = f"web_{str(user.id).replace('-', '')[:12]}"

    mobile_user = MobileUserModel(
        id=user.id,
        public_uid=await allocate_public_uid(repo),
        auth_realm_id=current_realm.auth_realm.id,
        email=user.email,
        password_hash=user.password_hash,
        username=username,
        is_active=user.is_active,
        status=user.status or ("active" if user.is_active else "pending"),
    )
    return await repo.create(mobile_user)
