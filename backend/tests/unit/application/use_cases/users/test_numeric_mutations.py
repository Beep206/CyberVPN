from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.use_cases.users.bulk_operations import (
    BulkUserMutationsSafetyDisabledError,
    BulkUserOperationsUseCase,
)
from src.application.use_cases.users.delete_user import DeleteUserUseCase
from src.application.use_cases.users.update_user import UpdateUserUseCase
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["update", "delete", "disable", "enable"])
async def test_user_mutations_reject_legacy_only_reference_before_gateway_call(operation: str) -> None:
    gateway = AsyncMock()
    legacy_ref = RemnawaveUserRef(legacy_uuid=uuid4())

    with pytest.raises(ValueError, match="has not been reconciled"):
        if operation == "update":
            await UpdateUserUseCase(gateway).execute(legacy_ref, status="disabled")
        elif operation == "delete":
            await DeleteUserUseCase(gateway).execute(legacy_ref)
        elif operation == "disable":
            await BulkUserOperationsUseCase(gateway).disable_users([legacy_ref])
        else:
            await BulkUserOperationsUseCase(gateway).enable_users([legacy_ref])

    gateway.update.assert_not_awaited()
    gateway.delete.assert_not_awaited()


@pytest.mark.unit
async def test_user_mutations_forward_reconciled_numeric_reference() -> None:
    gateway = AsyncMock()
    user_ref = RemnawaveUserRef(id=42, legacy_uuid=uuid4())
    gateway.update.return_value = object()

    await UpdateUserUseCase(gateway).execute(user_ref, email="updated@example.com")
    await DeleteUserUseCase(gateway).execute(user_ref)

    gateway.update.assert_awaited_once_with(user_ref, email="updated@example.com")
    gateway.delete.assert_awaited_once_with(user_ref)


@pytest.mark.unit
@pytest.mark.parametrize("operation", ["disable", "enable"])
async def test_bulk_mutations_are_rejected_before_any_provider_io(operation: str) -> None:
    gateway = AsyncMock()
    user_refs = [RemnawaveUserRef(id=41), RemnawaveUserRef(id=42)]
    use_case = BulkUserOperationsUseCase(gateway)

    with pytest.raises(BulkUserMutationsSafetyDisabledError, match="safety-disabled"):
        if operation == "disable":
            await use_case.disable_users(user_refs)
        else:
            await use_case.enable_users(user_refs)

    gateway.update.assert_not_awaited()
