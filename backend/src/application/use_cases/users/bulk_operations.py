"""Fail-closed boundary for unsafe at-least-once bulk user mutations."""

from src.domain.entities.user import User
from src.domain.value_objects.remnawave_user_ref import RemnawaveUserRef
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class BulkUserMutationsSafetyDisabledError(RuntimeError):
    """Bulk mutation requires durable per-user receipts before it can run."""

    def __init__(self) -> None:
        super().__init__("Bulk Remnawave user mutations are safety-disabled for this release")


class BulkUserOperationsUseCase:
    """Use case for performing bulk operations on users."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def disable_users(self, user_refs: list[RemnawaveUserRef]) -> list[User]:
        """Reject the operation before provider I/O until receipts exist."""
        for user_ref in user_refs:
            user_ref.require_numeric_id()
        raise BulkUserMutationsSafetyDisabledError

    async def enable_users(self, user_refs: list[RemnawaveUserRef]) -> list[User]:
        """Reject the operation before provider I/O until receipts exist."""
        for user_ref in user_refs:
            user_ref.require_numeric_id()
        raise BulkUserMutationsSafetyDisabledError
