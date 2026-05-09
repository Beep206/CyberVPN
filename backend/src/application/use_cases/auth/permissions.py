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
    MANAGE_INVITES = "manage_invites"  # CRIT-1: Invite token management
    # Subscriptions
    SUBSCRIPTION_CREATE = "subscription_create"
    VPN_CREDENTIAL_REGENERATE = "vpn_credential_regenerate"
    # Analytics
    VIEW_ANALYTICS = "view_analytics"


ROLE_MINIMUM_ACCESS: dict[AdminRole, set[AdminRole]] = {
    AdminRole.VIEWER: set(AdminRole),
    AdminRole.SUPPORT: {
        AdminRole.SUPPORT,
        AdminRole.OPERATOR,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    },
    AdminRole.FINANCE: {
        AdminRole.FINANCE,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    },
    AdminRole.OPERATOR: {
        AdminRole.OPERATOR,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    },
    AdminRole.ADMIN: {
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    },
    AdminRole.SUPER_ADMIN: {
        AdminRole.SUPER_ADMIN,
        AdminRole.OWNER_SUPER_ADMIN,
    },
    AdminRole.OWNER_SUPER_ADMIN: {
        AdminRole.OWNER_SUPER_ADMIN,
    },
}

ROLE_ASSIGNMENT_TARGETS: dict[AdminRole, set[AdminRole]] = {
    AdminRole.VIEWER: {AdminRole.VIEWER},
    AdminRole.SUPPORT: {AdminRole.VIEWER, AdminRole.SUPPORT},
    AdminRole.FINANCE: {AdminRole.VIEWER, AdminRole.FINANCE},
    AdminRole.OPERATOR: {AdminRole.VIEWER, AdminRole.SUPPORT, AdminRole.OPERATOR},
    AdminRole.ADMIN: {
        AdminRole.VIEWER,
        AdminRole.SUPPORT,
        AdminRole.FINANCE,
        AdminRole.OPERATOR,
        AdminRole.ADMIN,
    },
    AdminRole.SUPER_ADMIN: {
        AdminRole.VIEWER,
        AdminRole.SUPPORT,
        AdminRole.FINANCE,
        AdminRole.OPERATOR,
        AdminRole.ADMIN,
        AdminRole.SUPER_ADMIN,
    },
    AdminRole.OWNER_SUPER_ADMIN: set(AdminRole),
}

ROLE_PERMISSIONS: dict[AdminRole, set[Permission]] = {
    AdminRole.OWNER_SUPER_ADMIN: set(Permission),
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
        Permission.MANAGE_INVITES,  # CRIT-1: Allow admins to create invites
        Permission.SUBSCRIPTION_CREATE,
        Permission.VPN_CREDENTIAL_REGENERATE,
        Permission.VIEW_ANALYTICS,
    },
    AdminRole.OPERATOR: {
        Permission.USER_READ,
        Permission.SERVER_READ,
        Permission.SERVER_CREATE,
        Permission.SERVER_UPDATE,
        Permission.MONITORING_READ,
        Permission.SUBSCRIPTION_CREATE,
        Permission.VIEW_ANALYTICS,
    },
    AdminRole.FINANCE: {
        Permission.USER_READ,
        Permission.PAYMENT_READ,
        Permission.AUDIT_READ,
        Permission.WEBHOOK_READ,
    },
    AdminRole.SUPPORT: {
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.SERVER_READ,
        Permission.MONITORING_READ,
        Permission.VPN_CREDENTIAL_REGENERATE,
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
    return user_role in ROLE_MINIMUM_ACCESS[required_role]


def can_assign_role(assigner_role: AdminRole, target_role: AdminRole) -> bool:
    return target_role in ROLE_ASSIGNMENT_TARGETS[assigner_role]
