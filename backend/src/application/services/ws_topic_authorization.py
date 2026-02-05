"""WebSocket topic authorization service (HIGH-2).

Implements role-based access control for WebSocket topics:
- monitoring:servers - ADMIN, SUPER_ADMIN
- monitoring:users - SUPER_ADMIN only
- monitoring:system - SUPER_ADMIN only
- monitoring:general - All authenticated users
"""

import logging
from dataclasses import dataclass
from typing import ClassVar

from src.domain.enums.enums import AdminRole

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TopicPermission:
    """Topic permission definition."""

    topic: str
    allowed_roles: frozenset[AdminRole]
    description: str


class WSTopicAuthorizationService:
    """Service for WebSocket topic authorization.

    Controls which roles can subscribe to which topics.
    """

    # Topic permission matrix - defines which roles can access each topic
    TOPIC_PERMISSIONS: ClassVar[dict[str, TopicPermission]] = {
        "servers": TopicPermission(
            topic="servers",
            allowed_roles=frozenset({AdminRole.ADMIN, AdminRole.SUPER_ADMIN, AdminRole.OPERATOR}),
            description="Server status and metrics",
        ),
        "users": TopicPermission(
            topic="users",
            allowed_roles=frozenset({AdminRole.SUPER_ADMIN}),
            description="User activity and session data",
        ),
        "system": TopicPermission(
            topic="system",
            allowed_roles=frozenset({AdminRole.SUPER_ADMIN}),
            description="System metrics and alerts",
        ),
        "payments": TopicPermission(
            topic="payments",
            allowed_roles=frozenset({AdminRole.ADMIN, AdminRole.SUPER_ADMIN}),
            description="Payment notifications",
        ),
        "general": TopicPermission(
            topic="general",
            allowed_roles=frozenset(AdminRole),  # All roles
            description="General notifications",
        ),
    }

    # Default permission for unknown topics (deny by default)
    DEFAULT_ALLOWED_ROLES: ClassVar[frozenset[AdminRole]] = frozenset({AdminRole.SUPER_ADMIN})

    def can_subscribe(self, topic: str, role: AdminRole) -> bool:
        """Check if a role can subscribe to a topic.

        Args:
            topic: The topic name (without 'monitoring:' prefix)
            role: The user's role

        Returns:
            True if the role can subscribe, False otherwise
        """
        permission = self.TOPIC_PERMISSIONS.get(topic)

        if permission:
            return role in permission.allowed_roles

        # Unknown topic - only SUPER_ADMIN can subscribe (fail secure)
        logger.warning(
            "Subscription attempt to unknown topic",
            extra={"topic": topic, "role": role},
        )
        return role in self.DEFAULT_ALLOWED_ROLES

    def get_allowed_topics(self, role: AdminRole) -> list[str]:
        """Get list of topics a role can subscribe to.

        Args:
            role: The user's role

        Returns:
            List of topic names the role can access
        """
        allowed = []
        for topic_name, permission in self.TOPIC_PERMISSIONS.items():
            if role in permission.allowed_roles:
                allowed.append(topic_name)
        return allowed

    def authorize_subscription(
        self,
        user_id: str,
        role: AdminRole,
        topic: str,
    ) -> tuple[bool, str | None]:
        """Authorize a subscription request.

        Args:
            user_id: The user's ID (for logging)
            role: The user's role
            topic: The topic to subscribe to

        Returns:
            Tuple of (authorized: bool, error_message: str | None)
        """
        if self.can_subscribe(topic, role):
            logger.info(
                "WebSocket subscription authorized",
                extra={"user_id": user_id, "role": role, "topic": topic},
            )
            return True, None

        logger.warning(
            "WebSocket subscription denied - insufficient permissions",
            extra={"user_id": user_id, "role": role, "topic": topic},
        )
        return False, f"Insufficient permissions to subscribe to topic: {topic}"
