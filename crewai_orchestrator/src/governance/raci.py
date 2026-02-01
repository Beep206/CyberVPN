"""RACI matrix definitions for cross-department governance."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RACIRole(str, Enum):
    RESPONSIBLE = "R"  # Does the work
    ACCOUNTABLE = "A"  # Final approver
    CONSULTED = "C"  # Must be consulted before decision
    INFORMED = "I"  # Must be notified after decision


class RACIEntry(BaseModel):
    """A single RACI matrix entry for a decision type."""

    decision_type: str
    display_name: str
    assignments: dict[str, RACIRole]  # agent_name -> RACI role


# =============================================================================
# RACI Matrices — 9 decision types from CyberVPN governance
# =============================================================================

RACI_MATRICES: dict[str, RACIEntry] = {
    "pricing_change": RACIEntry(
        decision_type="pricing_change",
        display_name="Pricing Changes",
        assignments={
            "marketing-lead": RACIRole.CONSULTED,
            "finance-strategist": RACIRole.RESPONSIBLE,
            "product-manager": RACIRole.INFORMED,
            "security-engineer": RACIRole.INFORMED,
            "compliance-officer": RACIRole.CONSULTED,
            "devops-lead": RACIRole.INFORMED,
            "ceo-orchestrator": RACIRole.ACCOUNTABLE,
        },
    ),
    "public_release": RACIEntry(
        decision_type="public_release",
        display_name="Public Releases",
        assignments={
            "marketing-lead": RACIRole.CONSULTED,
            "finance-strategist": RACIRole.INFORMED,
            "product-manager": RACIRole.RESPONSIBLE,
            "security-engineer": RACIRole.CONSULTED,
            "compliance-officer": RACIRole.CONSULTED,
            "devops-lead": RACIRole.CONSULTED,
            "ceo-orchestrator": RACIRole.ACCOUNTABLE,
        },
    ),
    "marketing_campaign": RACIEntry(
        decision_type="marketing_campaign",
        display_name="Marketing Campaigns",
        assignments={
            "marketing-lead": RACIRole.RESPONSIBLE,
            "finance-strategist": RACIRole.CONSULTED,
            "product-manager": RACIRole.INFORMED,
            "compliance-officer": RACIRole.CONSULTED,
            "ceo-orchestrator": RACIRole.ACCOUNTABLE,
        },
    ),
    "security_change": RACIEntry(
        decision_type="security_change",
        display_name="Security Changes",
        assignments={
            "security-engineer": RACIRole.RESPONSIBLE,
            "cto-architect": RACIRole.ACCOUNTABLE,
            "dpo-officer": RACIRole.CONSULTED,
            "backend-lead": RACIRole.CONSULTED,
            "devops-lead": RACIRole.CONSULTED,
        },
    ),
    "new_server_region": RACIEntry(
        decision_type="new_server_region",
        display_name="New Servers/Regions",
        assignments={
            "infrastructure-engineer": RACIRole.RESPONSIBLE,
            "cto-architect": RACIRole.ACCOUNTABLE,
            "compliance-officer": RACIRole.CONSULTED,
            "abuse-handler": RACIRole.CONSULTED,
            "noc-agent": RACIRole.CONSULTED,
            "finance-strategist": RACIRole.INFORMED,
        },
    ),
    "payment_integration": RACIEntry(
        decision_type="payment_integration",
        display_name="Payment Integrations",
        assignments={
            "payments-specialist": RACIRole.RESPONSIBLE,
            "finance-strategist": RACIRole.ACCOUNTABLE,
            "backend-lead": RACIRole.CONSULTED,
            "security-engineer": RACIRole.CONSULTED,
            "compliance-officer": RACIRole.INFORMED,
        },
    ),
    "protocol_change": RACIEntry(
        decision_type="protocol_change",
        display_name="VPN Protocol Changes",
        assignments={
            "protocol-engineer": RACIRole.RESPONSIBLE,
            "cto-architect": RACIRole.ACCOUNTABLE,
            "security-engineer": RACIRole.CONSULTED,
            "noc-agent": RACIRole.CONSULTED,
            "mobile-lead": RACIRole.INFORMED,
        },
    ),
    "localization": RACIEntry(
        decision_type="localization",
        display_name="Localization",
        assignments={
            "i18n-manager": RACIRole.RESPONSIBLE,
            "product-manager": RACIRole.ACCOUNTABLE,
            "marketing-lead": RACIRole.CONSULTED,
            "frontend-lead": RACIRole.INFORMED,
            "mobile-lead": RACIRole.INFORMED,
        },
    ),
    "abuse_dmca": RACIEntry(
        decision_type="abuse_dmca",
        display_name="Abuse/DMCA Handling",
        assignments={
            "abuse-handler": RACIRole.RESPONSIBLE,
            "ceo-orchestrator": RACIRole.ACCOUNTABLE,
            "dpo-officer": RACIRole.CONSULTED,
            "compliance-officer": RACIRole.CONSULTED,
            "infrastructure-engineer": RACIRole.INFORMED,
        },
    ),
}


def get_required_approvers(decision_type: str) -> list[str]:
    """Return agents with R or A roles for a decision type."""
    entry = RACI_MATRICES.get(decision_type)
    if not entry:
        return []
    return [agent for agent, role in entry.assignments.items() if role in (RACIRole.RESPONSIBLE, RACIRole.ACCOUNTABLE)]


def get_consulted_agents(decision_type: str) -> list[str]:
    """Return agents that must be consulted before a decision."""
    entry = RACI_MATRICES.get(decision_type)
    if not entry:
        return []
    return [agent for agent, role in entry.assignments.items() if role == RACIRole.CONSULTED]


def get_informed_agents(decision_type: str) -> list[str]:
    """Return agents that must be informed after a decision."""
    entry = RACI_MATRICES.get(decision_type)
    if not entry:
        return []
    return [agent for agent, role in entry.assignments.items() if role == RACIRole.INFORMED]


def get_all_decision_types() -> list[str]:
    """Return all available decision types."""
    return list(RACI_MATRICES.keys())
