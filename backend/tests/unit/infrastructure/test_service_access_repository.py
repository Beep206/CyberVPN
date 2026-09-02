from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.service_access_repo import ServiceAccessRepository


class _ScalarCollection:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


class _Result:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _ScalarCollection:
        return _ScalarCollection(self._values)


class _Session:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    async def execute(self, _statement) -> _Result:
        return _Result(self._values)


@pytest.mark.asyncio
async def test_numeric_identity_lookup_rejects_account_and_subscription_ambiguity() -> None:
    numeric_id = 4207
    session = _Session(
        [
            SimpleNamespace(identity_scope="account", provider_numeric_subject_id=numeric_id),
            SimpleNamespace(identity_scope="subscription", provider_numeric_subject_id=numeric_id),
        ]
    )
    repository = ServiceAccessRepository(cast(AsyncSession, session))

    with pytest.raises(ValueError, match="maps to multiple local service identities"):
        await repository.get_service_identity_by_customer_realm_provider_numeric_subject(
            customer_account_id=uuid4(),
            auth_realm_id=uuid4(),
            provider_name="remnawave",
            provider_numeric_subject_id=numeric_id,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("numeric_id", [None, 0, -1, True, "4207"])
async def test_numeric_identity_lookup_rejects_non_positive_or_untyped_id(numeric_id: object) -> None:
    repository = ServiceAccessRepository(cast(AsyncSession, _Session([])))

    with pytest.raises(ValueError, match="positive integer"):
        await repository.get_service_identity_by_customer_realm_provider_numeric_subject(
            customer_account_id=uuid4(),
            auth_realm_id=uuid4(),
            provider_name="remnawave",
            provider_numeric_subject_id=cast(int, numeric_id),
        )
