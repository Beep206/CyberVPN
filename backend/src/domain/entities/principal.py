"""Principal identity abstractions for realm-aware auth."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    principal_id: str
    principal_class: str
    auth_realm_id: str
    audience: str
    scope_family: str
