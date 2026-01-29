from enum import StrEnum

from src.domain.enums import AdminRole


class Permission(StrEnum):
    # User permissions
    USER_READ = "user_read"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    # Server permissions
    SERVER_READ = "server_read"
    SERVER_CREATE = "server_create"
    SERVER_UPDATE = "server_update"
    SERVER_DELETE = "server_delete"
    # Payment permissions
    PAYMENT_READ = "payment_read"
    PAYMENT_CREATE = "payment_create"
    # Monitoring
    MONITORING_READ = "monitoring_read"
    # Admin
    AUDIT_READ = "audit_read"
    WEBHOOK_READ = "webhook_read"
    MANAGE_ADMINS = "manage_admins"
    MANAGE_PLANS = "manage_plans"
    # Subscriptions
    SUBSCRIPTION_CREATE = "subscription_create"
    # Analytics
    VIEW_ANALYTICS = "view_analytics"


ROLE_PERMISSIONS: dict[AdminRole, set[Permission]] = {
    AdminRole.SUPER_ADMIN: set(Permission),
    AdminRole.ADMIN: {
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.SERVER_READ,
        Permission.SERVER_CREATE,
        Permission.SERVER_UPDATE,
        Permission.SERVER_DELETE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.MONITORING_READ,
        Permission.AUDIT_READ,
        Permission.WEBHOOK_READ,
        Permission.MANAGE_PLANS,
        Permission.SUBSCRIPTION_CREATE,
        Permission.VIEW_ANALYTICS,
    },
    AdminRole.OPERATOR: {
        Permission.USER_READ,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.SERVER_READ,
        Permission.SERVER_CREATE,
        Permission.SERVER_UPDATE,
        Permission.PAYMENT_READ,
        Permission.PAYMENT_CREATE,
        Permission.MONITORING_READ,
        Permission.SUBSCRIPTION_CREATE,
        Permission.VIEW_ANALYTICS,
    },
    AdminRole.SUPPORT: {
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.SERVER_READ,
        Permission.MONITORING_READ,
    },
    AdminRole.VIEWER: {
        Permission.USER_READ,
        Permission.SERVER_READ,
        Permission.MONITORING_READ,
        Permission.VIEW_ANALYTICS,
    },
}


def has_permission(role: AdminRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def check_minimum_role(user_role: AdminRole, required_role: AdminRole) -> bool:
    role_hierarchy = [AdminRole.VIEWER, AdminRole.SUPPORT, AdminRole.OPERATOR, AdminRole.ADMIN, AdminRole.SUPER_ADMIN]
    return role_hierarchy.index(user_role) >= role_hierarchy.index(required_role)
