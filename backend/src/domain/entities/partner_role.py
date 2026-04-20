"""Canonical partner workspace role definitions."""

from dataclasses import dataclass

from src.domain.entities.partner_permission import PartnerPermission


@dataclass(frozen=True)
class PartnerRoleDefinition:
    role_key: str
    display_name: str
    description: str
    permissions: tuple[PartnerPermission, ...]


BUILTIN_PARTNER_ROLE_DEFINITIONS: tuple[PartnerRoleDefinition, ...] = (
    PartnerRoleDefinition(
        role_key="owner",
        display_name="Owner",
        description="Full workspace access including membership and revenue controls.",
        permissions=tuple(PartnerPermission),
    ),
    PartnerRoleDefinition(
        role_key="manager",
        display_name="Manager",
        description="Operational workspace manager with member and code management rights.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.OPERATIONS_WRITE,
            PartnerPermission.MEMBERSHIP_READ,
            PartnerPermission.MEMBERSHIP_WRITE,
            PartnerPermission.CODES_READ,
            PartnerPermission.CODES_WRITE,
            PartnerPermission.EARNINGS_READ,
            PartnerPermission.TRAFFIC_READ,
            PartnerPermission.TRAFFIC_WRITE,
            PartnerPermission.INTEGRATIONS_READ,
        ),
    ),
    PartnerRoleDefinition(
        role_key="finance",
        display_name="Finance",
        description="Finance operator with visibility into earnings and payout surfaces.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.OPERATIONS_WRITE,
            PartnerPermission.MEMBERSHIP_READ,
            PartnerPermission.EARNINGS_READ,
            PartnerPermission.PAYOUTS_READ,
            PartnerPermission.PAYOUTS_WRITE,
        ),
    ),
    PartnerRoleDefinition(
        role_key="analyst",
        display_name="Analyst",
        description="Read-only operator for partner performance and code analytics.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.CODES_READ,
            PartnerPermission.EARNINGS_READ,
            PartnerPermission.TRAFFIC_READ,
            PartnerPermission.INTEGRATIONS_READ,
        ),
    ),
    PartnerRoleDefinition(
        role_key="traffic_manager",
        display_name="Traffic Manager",
        description="Operator responsible for codes and traffic declarations.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.OPERATIONS_WRITE,
            PartnerPermission.CODES_READ,
            PartnerPermission.CODES_WRITE,
            PartnerPermission.TRAFFIC_READ,
            PartnerPermission.TRAFFIC_WRITE,
            PartnerPermission.INTEGRATIONS_READ,
            PartnerPermission.INTEGRATIONS_WRITE,
        ),
    ),
    PartnerRoleDefinition(
        role_key="technical_manager",
        display_name="Technical Manager",
        description="Operator responsible for partner API, reporting token, and postback readiness.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.TRAFFIC_READ,
            PartnerPermission.TRAFFIC_WRITE,
            PartnerPermission.INTEGRATIONS_READ,
            PartnerPermission.INTEGRATIONS_WRITE,
        ),
    ),
    PartnerRoleDefinition(
        role_key="support_manager",
        display_name="Support Manager",
        description="Operator with membership visibility and workspace read access.",
        permissions=(
            PartnerPermission.WORKSPACE_READ,
            PartnerPermission.OPERATIONS_WRITE,
            PartnerPermission.MEMBERSHIP_READ,
        ),
    ),
)


BUILTIN_PARTNER_ROLE_MAP = {definition.role_key: definition for definition in BUILTIN_PARTNER_ROLE_DEFINITIONS}
