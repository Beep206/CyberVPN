"""Security tests for WebSocket topic authorization (HIGH-2).

Tests that:
1. Role-based topic authorization works correctly
2. Unauthorized subscription attempts are denied
3. Unknown topics are restricted to SUPER_ADMIN only
"""

from src.application.services.ws_topic_authorization import WSTopicAuthorizationService
from src.domain.enums.enums import AdminRole


class TestTopicPermissions:
    """Test topic permission matrix."""

    def setup_method(self):
        """Create authorization service for each test."""
        self.auth_service = WSTopicAuthorizationService()

    def test_super_admin_can_access_all_topics(self):
        """SUPER_ADMIN can subscribe to any defined topic."""
        topics = ["servers", "users", "system", "payments", "general"]

        for topic in topics:
            assert self.auth_service.can_subscribe(topic, AdminRole.SUPER_ADMIN), f"SUPER_ADMIN should access {topic}"

    def test_admin_can_access_admin_topics(self):
        """ADMIN can access servers, payments, general but not users or system."""
        # Can access
        assert self.auth_service.can_subscribe("servers", AdminRole.ADMIN)
        assert self.auth_service.can_subscribe("payments", AdminRole.ADMIN)
        assert self.auth_service.can_subscribe("general", AdminRole.ADMIN)

        # Cannot access
        assert not self.auth_service.can_subscribe("users", AdminRole.ADMIN)
        assert not self.auth_service.can_subscribe("system", AdminRole.ADMIN)

    def test_operator_limited_access(self):
        """OPERATOR can access servers and general only."""
        assert self.auth_service.can_subscribe("servers", AdminRole.OPERATOR)
        assert self.auth_service.can_subscribe("general", AdminRole.OPERATOR)

        # Cannot access sensitive topics
        assert not self.auth_service.can_subscribe("users", AdminRole.OPERATOR)
        assert not self.auth_service.can_subscribe("system", AdminRole.OPERATOR)
        assert not self.auth_service.can_subscribe("payments", AdminRole.OPERATOR)

    def test_viewer_minimal_access(self):
        """VIEWER can only access general topic."""
        assert self.auth_service.can_subscribe("general", AdminRole.VIEWER)

        # Cannot access any other topics
        assert not self.auth_service.can_subscribe("servers", AdminRole.VIEWER)
        assert not self.auth_service.can_subscribe("users", AdminRole.VIEWER)
        assert not self.auth_service.can_subscribe("system", AdminRole.VIEWER)
        assert not self.auth_service.can_subscribe("payments", AdminRole.VIEWER)

    def test_unknown_topic_restricted_to_super_admin(self):
        """Unknown topics should only be accessible by SUPER_ADMIN (fail secure)."""
        unknown_topic = "secret_admin_backdoor"

        # SUPER_ADMIN can access unknown topics
        assert self.auth_service.can_subscribe(unknown_topic, AdminRole.SUPER_ADMIN)

        # All other roles cannot
        assert not self.auth_service.can_subscribe(unknown_topic, AdminRole.ADMIN)
        assert not self.auth_service.can_subscribe(unknown_topic, AdminRole.OPERATOR)
        assert not self.auth_service.can_subscribe(unknown_topic, AdminRole.SUPPORT)
        assert not self.auth_service.can_subscribe(unknown_topic, AdminRole.VIEWER)


class TestAuthorizeSubscription:
    """Test subscription authorization with logging."""

    def setup_method(self):
        """Create authorization service for each test."""
        self.auth_service = WSTopicAuthorizationService()

    def test_authorized_returns_true_no_error(self):
        """Authorized subscription returns (True, None)."""
        authorized, error = self.auth_service.authorize_subscription(
            user_id="user-123",
            role=AdminRole.SUPER_ADMIN,
            topic="users",
        )

        assert authorized is True
        assert error is None

    def test_unauthorized_returns_false_with_error(self):
        """Unauthorized subscription returns (False, error_message)."""
        authorized, error = self.auth_service.authorize_subscription(
            user_id="user-456",
            role=AdminRole.VIEWER,
            topic="users",
        )

        assert authorized is False
        assert error is not None
        assert "users" in error


class TestGetAllowedTopics:
    """Test getting allowed topics for a role."""

    def setup_method(self):
        """Create authorization service for each test."""
        self.auth_service = WSTopicAuthorizationService()

    def test_super_admin_gets_all_topics(self):
        """SUPER_ADMIN gets all defined topics."""
        allowed = self.auth_service.get_allowed_topics(AdminRole.SUPER_ADMIN)

        assert "servers" in allowed
        assert "users" in allowed
        assert "system" in allowed
        assert "payments" in allowed
        assert "general" in allowed

    def test_viewer_gets_only_general(self):
        """VIEWER only gets general topic."""
        allowed = self.auth_service.get_allowed_topics(AdminRole.VIEWER)

        assert "general" in allowed
        assert len([t for t in allowed if t != "general"]) == 0 or all(t == "general" for t in allowed)
