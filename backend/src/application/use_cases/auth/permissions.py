from enum import StrEnum

from src.domain.enums import AdminRole


class Permission(StrEnum):
    # User permissions
    USER_READ = "user_read"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    SUPPORT_TICKET_READ = "support_ticket_read"
    PRIVACY_REQUEST_READ = "privacy_request_read"
    PRIVACY_REQUEST_REVIEW = "privacy_request_review"
    PRIVACY_REQUEST_FULFILL = "privacy_request_fulfill"
    PRIVACY_REQUEST_AUDIT_READ = "privacy_request_audit_read"
    # Messaging and site notifications
    MESSAGING_CONVERSATION_READ = "messaging:conversation:read"
    MESSAGING_CONVERSATION_CREATE = "messaging:conversation:create"
    MESSAGING_MESSAGE_WRITE = "messaging:message:write"
    MESSAGING_INTERNAL_NOTE_WRITE = "messaging:internal_note:write"
    MESSAGING_CONVERSATION_ASSIGN = "messaging:conversation:assign"
    MESSAGING_CONVERSATION_CLOSE = "messaging:conversation:close"
    MESSAGING_CONVERSATION_MANAGE = "messaging:conversation:manage"
    NOTIFICATION_BROADCAST_CREATE = "notification:broadcast:create"
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
    # Growth Codes v6
    GROWTH_CAMPAIGNS_READ = "growth.campaigns.read"
    GROWTH_CAMPAIGNS_WRITE = "growth.campaigns.write"
    GROWTH_CAMPAIGNS_PUBLISH = "growth.campaigns.publish"
    GROWTH_CAMPAIGNS_PAUSE = "growth.campaigns.pause"
    GROWTH_CAMPAIGNS_REVOKE = "growth.campaigns.revoke"
    GROWTH_RULES_VIEW = "growth.rules.view"
    GROWTH_RULES_EDIT = "growth.rules.edit"
    GROWTH_RULES_VALIDATE = "growth.rules.validate"
    GROWTH_RULES_PUBLISH = "growth.rules.publish"
    GROWTH_RULES_APPROVE = "growth.rules.approve"
    GROWTH_RISK_DECISIONS_VIEW = "growth.risk.decisions.view"
    GROWTH_RISK_REVIEWS_MANAGE = "growth.risk.reviews.manage"
    GROWTH_RISK_MODELS_MANAGE = "growth.risk.models.manage"
    GROWTH_RISK_MODELS_APPROVE = "growth.risk.models.approve"
    GROWTH_RISK_THRESHOLDS_MANAGE = "growth.risk.thresholds.manage"
    GROWTH_PRIVATE_CATALOG_VIEW = "growth.private_catalog.view"
    GROWTH_PRIVATE_CATALOG_MANAGE = "growth.private_catalog.manage"
    GROWTH_PRIVATE_GRANTS_VIEW = "growth.private_grants.view"
    GROWTH_PRIVATE_GRANTS_REVOKE = "growth.private_grants.revoke"
    GROWTH_FX_VIEW = "growth.fx.view"
    GROWTH_FX_MANAGE = "growth.fx.manage"
    GROWTH_FX_OVERRIDE = "growth.fx.override"
    GROWTH_FX_APPROVE = "growth.fx.approve"
    GROWTH_CODE_SETS_INSPECT = "growth.code_sets.inspect"
    GROWTH_CODE_SETS_EXPORT = "growth.code_sets.export"
    GROWTH_ONBOARDING_VIEW = "growth.onboarding.view"
    GROWTH_ONBOARDING_MANAGE = "growth.onboarding.manage"
    GROWTH_ONBOARDING_RESET = "growth.onboarding.reset"
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
        Permission.SUPPORT_TICKET_READ,
        Permission.PRIVACY_REQUEST_READ,
        Permission.PRIVACY_REQUEST_REVIEW,
        Permission.PRIVACY_REQUEST_FULFILL,
        Permission.PRIVACY_REQUEST_AUDIT_READ,
        Permission.MESSAGING_CONVERSATION_READ,
        Permission.MESSAGING_CONVERSATION_CREATE,
        Permission.MESSAGING_MESSAGE_WRITE,
        Permission.MESSAGING_INTERNAL_NOTE_WRITE,
        Permission.MESSAGING_CONVERSATION_ASSIGN,
        Permission.MESSAGING_CONVERSATION_CLOSE,
        Permission.MESSAGING_CONVERSATION_MANAGE,
        Permission.NOTIFICATION_BROADCAST_CREATE,
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
        Permission.GROWTH_CAMPAIGNS_READ,
        Permission.GROWTH_CAMPAIGNS_WRITE,
        Permission.GROWTH_CAMPAIGNS_PUBLISH,
        Permission.GROWTH_CAMPAIGNS_PAUSE,
        Permission.GROWTH_CAMPAIGNS_REVOKE,
        Permission.GROWTH_RULES_VIEW,
        Permission.GROWTH_RULES_EDIT,
        Permission.GROWTH_RULES_VALIDATE,
        Permission.GROWTH_RULES_PUBLISH,
        Permission.GROWTH_RULES_APPROVE,
        Permission.GROWTH_RISK_DECISIONS_VIEW,
        Permission.GROWTH_RISK_REVIEWS_MANAGE,
        Permission.GROWTH_RISK_MODELS_MANAGE,
        Permission.GROWTH_RISK_MODELS_APPROVE,
        Permission.GROWTH_RISK_THRESHOLDS_MANAGE,
        Permission.GROWTH_PRIVATE_CATALOG_VIEW,
        Permission.GROWTH_PRIVATE_CATALOG_MANAGE,
        Permission.GROWTH_PRIVATE_GRANTS_VIEW,
        Permission.GROWTH_PRIVATE_GRANTS_REVOKE,
        Permission.GROWTH_FX_VIEW,
        Permission.GROWTH_FX_MANAGE,
        Permission.GROWTH_FX_OVERRIDE,
        Permission.GROWTH_FX_APPROVE,
        Permission.GROWTH_CODE_SETS_INSPECT,
        Permission.GROWTH_CODE_SETS_EXPORT,
        Permission.GROWTH_ONBOARDING_VIEW,
        Permission.GROWTH_ONBOARDING_MANAGE,
        Permission.GROWTH_ONBOARDING_RESET,
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
        Permission.SUPPORT_TICKET_READ,
        Permission.PRIVACY_REQUEST_READ,
        Permission.PRIVACY_REQUEST_REVIEW,
        Permission.PRIVACY_REQUEST_AUDIT_READ,
        Permission.MESSAGING_CONVERSATION_READ,
        Permission.MESSAGING_CONVERSATION_CREATE,
        Permission.MESSAGING_MESSAGE_WRITE,
        Permission.MESSAGING_INTERNAL_NOTE_WRITE,
        Permission.MESSAGING_CONVERSATION_ASSIGN,
        Permission.MESSAGING_CONVERSATION_CLOSE,
        Permission.MESSAGING_CONVERSATION_MANAGE,
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
