"""Create user use case."""
from uuid import UUID

from src.application.dto.user_dto import CreateUserDTO
from src.domain.entities.user import User
from src.infrastructure.remnawave.user_gateway import RemnawaveUserGateway


class CreateUserUseCase:
    """Use case for creating a new user."""

    def __init__(self, gateway: RemnawaveUserGateway):
        """Initialize the use case with a user gateway.

        Args:
            gateway: The user gateway for interacting with Remnawave API
        """
        self.gateway = gateway

    async def execute(self, dto: CreateUserDTO) -> User:
        """Execute the create user use case.

        Args:
            dto: The data transfer object containing user creation data

        Returns:
            The created User entity

        Raises:
            Exception: If user creation fails
        """
        return await self.gateway.create(
            username=dto.username,
            password=dto.password,
            email=dto.email,
            data_limit=dto.data_limit,
            expire_at=dto.expire_at,
        )
