"""Helpers for mapping auth realm resolution to token/session context."""

from src.application.use_cases.auth_realms import RealmResolution
from src.domain.enums import PrincipalClass


def get_principal_type_for_realm(current_realm: RealmResolution) -> str:
    if current_realm.realm_type == "partner":
        return PrincipalClass.PARTNER_OPERATOR.value
    if current_realm.realm_type == "customer":
        return PrincipalClass.CUSTOMER.value
    return PrincipalClass.ADMIN.value


def get_scope_family_for_realm(current_realm: RealmResolution) -> str:
    if current_realm.realm_type == "partner":
        return "partner"
    if current_realm.realm_type == "customer":
        return "customer"
    return "admin"
