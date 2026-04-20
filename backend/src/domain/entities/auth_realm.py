"""Auth realm domain entities and deterministic defaults."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid5

AUTH_REALM_NAMESPACE = UUID("1fd3f622-9a94-4d1d-9a6f-d1d2fb88c0b6")

DEFAULT_AUTH_REALMS: dict[str, dict[str, str | bool]] = {
    "customer": {
        "realm_key": "customer",
        "realm_type": "customer",
        "display_name": "Customer Realm",
        "audience": "cybervpn:customer",
        "cookie_namespace": "customer",
        "is_default": True,
    },
    "partner": {
        "realm_key": "partner",
        "realm_type": "partner",
        "display_name": "Partner Realm",
        "audience": "cybervpn:partner",
        "cookie_namespace": "partner",
        "is_default": True,
    },
    "admin": {
        "realm_key": "admin",
        "realm_type": "admin",
        "display_name": "Admin Realm",
        "audience": "cybervpn:admin",
        "cookie_namespace": "admin",
        "is_default": True,
    },
    "service": {
        "realm_key": "service",
        "realm_type": "service",
        "display_name": "Service Realm",
        "audience": "cybervpn:service",
        "cookie_namespace": "service",
        "is_default": True,
    },
}


def stable_auth_realm_id(realm_key: str) -> UUID:
    """Create a deterministic UUID for well-known auth realms."""
    return uuid5(AUTH_REALM_NAMESPACE, f"cybervpn:{realm_key}")


@dataclass(frozen=True)
class AuthRealm:
    id: UUID
    realm_key: str
    realm_type: str
    display_name: str
    audience: str
    cookie_namespace: str
    status: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
