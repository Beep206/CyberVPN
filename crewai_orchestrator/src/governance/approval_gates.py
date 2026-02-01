"""Approval gates for multi-department decision enforcement."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .raci import get_consulted_agents, get_required_approvers


class ApprovalRecord(BaseModel):
    """A single approval/rejection from an agent."""

    agent_name: str
    decision: str  # "approved", "rejected", "needs_revision"
    reasoning: str
    conditions: list[str] = Field(default_factory=list)


class ApprovalGate(BaseModel):
    """Multi-department approval gate for a decision type."""

    decision_type: str
    approvals: list[ApprovalRecord] = Field(default_factory=list)

    @property
    def is_approved(self) -> bool:
        """Check if all required approvers have approved."""
        required = get_required_approvers(self.decision_type)
        approved_agents = {a.agent_name for a in self.approvals if a.decision == "approved"}
        return all(r in approved_agents for r in required)

    @property
    def is_rejected(self) -> bool:
        """Check if any required approver has rejected."""
        required = set(get_required_approvers(self.decision_type))
        return any(a.agent_name in required and a.decision == "rejected" for a in self.approvals)

    @property
    def consulted_complete(self) -> bool:
        """Check if all consulted agents have responded."""
        consulted = get_consulted_agents(self.decision_type)
        responded = {a.agent_name for a in self.approvals}
        return all(c in responded for c in consulted)

    @property
    def pending_approvers(self) -> list[str]:
        """Return agents who haven't responded yet."""
        required = get_required_approvers(self.decision_type)
        responded = {a.agent_name for a in self.approvals}
        return [r for r in required if r not in responded]

    def add_approval(self, record: ApprovalRecord) -> None:
        """Add an approval record."""
        # Remove existing record from same agent (update)
        self.approvals = [a for a in self.approvals if a.agent_name != record.agent_name]
        self.approvals.append(record)

    def summary(self) -> str:
        """Human-readable summary of gate status."""
        lines = [f"Approval Gate: {self.decision_type}"]
        lines.append(f"  Status: {'APPROVED' if self.is_approved else 'REJECTED' if self.is_rejected else 'PENDING'}")
        lines.append(f"  Pending: {', '.join(self.pending_approvers) or 'none'}")
        for a in self.approvals:
            lines.append(f"  {a.agent_name}: {a.decision} — {a.reasoning[:80]}")
        return "\n".join(lines)
