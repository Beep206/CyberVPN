from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.server import Server
from src.domain.entities.user import User
from src.domain.enums import (
    AdminRole,
    PaymentStatus,
    ServerStatus,
    UserStatus,
)
from src.domain.exceptions import (
    DomainError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from src.domain.value_objects.email import Email
from src.domain.value_objects.geolocation import Geolocation
from src.domain.value_objects.money import Money
from src.domain.value_objects.traffic import Traffic


class TestUser:
    def test_create_user(self):
        user = User(
            uuid=uuid4(),
            username="testuser",
            status=UserStatus.ACTIVE,
            short_uuid="abc123",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert user.username == "testuser"
        assert user.status == UserStatus.ACTIVE

    def test_optional_fields_default_none(self):
        user = User(
            uuid=uuid4(),
            username="test",
            status=UserStatus.ACTIVE,
            short_uuid="abc",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert user.telegram_id is None
        assert user.email is None


class TestServer:
    def test_status_online(self):
        server = Server(
            uuid=uuid4(),
            name="test",
            address="1.2.3.4",
            port=443,
            is_connected=True,
            is_disabled=False,
            is_connecting=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert server.status == ServerStatus.ONLINE

    def test_status_maintenance(self):
        server = Server(
            uuid=uuid4(),
            name="test",
            address="1.2.3.4",
            port=443,
            is_connected=False,
            is_disabled=True,
            is_connecting=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert server.status == ServerStatus.MAINTENANCE

    def test_status_warning(self):
        server = Server(
            uuid=uuid4(),
            name="test",
            address="1.2.3.4",
            port=443,
            is_connected=False,
            is_disabled=False,
            is_connecting=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert server.status == ServerStatus.WARNING

    def test_status_offline(self):
        server = Server(
            uuid=uuid4(),
            name="test",
            address="1.2.3.4",
            port=443,
            is_connected=False,
            is_disabled=False,
            is_connecting=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert server.status == ServerStatus.OFFLINE


class TestValueObjects:
    def test_email_valid(self):
        email = Email("test@example.com")
        assert str(email) == "test@example.com"

    def test_email_invalid(self):
        with pytest.raises(ValueError):
            Email("invalid")

    def test_money(self):
        money = Money(amount=Decimal("9.99"), currency="USD")
        assert str(money) == "9.99 USD"

    def test_money_negative(self):
        with pytest.raises(ValueError):
            Money(amount=Decimal("-1"), currency="USD")

    def test_traffic_conversions(self):
        traffic = Traffic(bytes=1073741824)  # 1 GB
        assert abs(traffic.gb - 1.0) < 0.01

    def test_geolocation_valid(self):
        geo = Geolocation(latitude=55.75, longitude=37.62)
        assert geo.latitude == 55.75

    def test_geolocation_invalid_lat(self):
        with pytest.raises(ValueError):
            Geolocation(latitude=91, longitude=0)


class TestEnums:
    def test_user_status_values(self):
        assert UserStatus.ACTIVE == "active"
        assert UserStatus.DISABLED == "disabled"

    def test_admin_role_values(self):
        assert AdminRole.SUPER_ADMIN == "super_admin"
        assert AdminRole.VIEWER == "viewer"

    def test_payment_status(self):
        assert PaymentStatus.COMPLETED == "completed"


class TestExceptions:
    def test_domain_error(self):
        err = DomainError("test", {"key": "value"})
        assert err.message == "test"
        assert err.details["key"] == "value"

    def test_user_not_found(self):
        err = UserNotFoundError("abc")
        assert "abc" in str(err)

    def test_invalid_credentials(self):
        err = InvalidCredentialsError()
        assert "Invalid credentials" in str(err)
