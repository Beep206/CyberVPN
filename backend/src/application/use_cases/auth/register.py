"""
Registration use case for creating new admin users.
"""

from src.application.services.auth_service import AuthService
from src.domain.exceptions import DuplicateUsernameError
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.repositories.admin_user_repo import AdminUserRepository


class RegisterUseCase:
    """
    Handles admin user registration.

    Creates new admin user with hashed password after validating
    login and email uniqueness.
    """

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
    ) -> None:
        self._user_repo = user_repo
        self._auth_service = auth_service

    async def execute(
        self,
        login: str,
        email: str,
        password: str,
        role: str = "viewer",
    ) -> AdminUserModel:
        """
        Register new admin user.

        Args:
            login: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)
            role: User role (default: "viewer")

        Returns:
            Created AdminUserModel instance

        Raises:
            DuplicateUsernameError: If login or email already exists
        """
        # Check login uniqueness
        existing_user = await self._user_repo.get_by_login(login)
        if existing_user:
            raise DuplicateUsernameError(username=login)

        # Check email uniqueness
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user:
            raise DuplicateUsernameError(username=email)

        # Hash password
        password_hash = await self._auth_service.hash_password(password)

        # Create AdminUserModel model
        user = AdminUserModel(
            login=login,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )

        # Persist to database
        created_user = await self._user_repo.create(user)

        return created_user
