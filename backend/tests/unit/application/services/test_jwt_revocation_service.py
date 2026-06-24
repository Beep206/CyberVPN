"""JWT revocation service scope-isolation tests."""

from datetime import UTC, datetime, timedelta

import pytest

from src.application.services.jwt_revocation_service import JWTRevocationService
from tests.helpers.realm_auth import FakeRedis


@pytest.mark.asyncio
async def test_revoke_principal_tokens_preserves_other_realm_for_same_subject() -> None:
    redis = FakeRedis()
    service = JWTRevocationService(redis)  # type: ignore[arg-type]
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    same_subject = "00000000-0000-0000-0000-000000000001"

    await service.register_token(
        "admin-jti",
        same_subject,
        expires_at,
        auth_realm_id="admin-realm",
        principal_class="admin",
        principal_subject=same_subject,
    )
    await service.register_token(
        "customer-jti",
        same_subject,
        expires_at,
        auth_realm_id="customer-realm",
        principal_class="customer",
        principal_subject=same_subject,
    )

    revoked = await service.revoke_principal_tokens(
        user_id=same_subject,
        auth_realm_id="admin-realm",
        principal_class="admin",
        principal_subject=same_subject,
    )

    assert revoked == 1
    assert await service.is_revoked("admin-jti")
    assert not await service.is_revoked("customer-jti")
    assert await service.get_user_active_sessions(same_subject) == 1
