"""Test data factories using factory-boy (QUAL-01c)."""

import uuid
from datetime import UTC, datetime

import factory


class AdminUserFactory(factory.Factory):
    """Factory for AdminUser-like dicts (no ORM dependency for unit tests)."""

    class Meta:
        model = dict

    id = factory.LazyFunction(uuid.uuid4)
    login = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda o: f"{o.login}@example.com")
    password_hash = "$argon2id$v=19$m=65536,t=3,p=4$fake_hash"
    role = "viewer"
    is_active = True
    is_email_verified = True
    telegram_id = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
    # BF2-3: Profile fields
    display_name = None
    language = "en"
    timezone = "UTC"
    # BF2-5: Notification preferences
    notification_prefs = None
