#!/usr/bin/env python3
"""Render and validate the P3.9 production drills and conformance bundle."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


GATE_ID = "D"
PHASE_ID = "P3"
WORKLOAD_CLUSTER_NAME = "prod-hetzner-fsn1-core"
MANAGEMENT_CLUSTER_NAME = "prod-mgmt"

REQUIRED_ANCHORS: dict[str, tuple[str, ...]] = {
    "docs/testing/platform-foundation-conformance-scorecard.md": (
        "`C01`",
        "`C15`",
        "`Gate D`",
    ),
    "docs/evidence/platform-foundation/platform-foundation-phase-evidence-template.md": (
        "Gate D",
        "Node Fleet Controller",
        "PostHog",
    ),
    "infra/scripts/control_plane_recovery.py": (
        "OpenBao",
        "NATS",
        "PostHog",
    ),
    "infra/scripts/cluster_backup_bootstrap.py": (
        "CloudNativePG",
        "ScheduledBackup",
        "Velero",
    ),
    "infra/scripts/prod_control_plane_cutover.py": (
        "Flagger",
        "CloudNativePG",
        "ScheduledBackup",
    ),
    "services/node-fleet-controller/src/application/services/failover_policy_service.py": (
        "confidence_score_threshold",
        "cooldown_seconds",
        "blocked_reasons",
    ),
    "services/node-fleet-controller/src/application/services/request_service.py": (
        "request_blocked_policy",
        "request_awaiting_approval",
    ),
    "backend/src/application/services/posthog_bridge.py": (
        "checkout_payment_captured",
        "subscription_activated",
    ),
    "partner/src/lib/product-intelligence/dashboard-contracts.ts": (
        "checkout_payment_captured",
        "subscription_activated",
    ),
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, mode: int = 0o640) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def render_root_readme() -> str:
    return f"""# P3.9 production drills and conformance bundle

This bundle freezes the repo-side drill order and Gate `{GATE_ID}` conformance package for
CyberVPN.

Frozen production scope:

- management cluster: `{MANAGEMENT_CLUSTER_NAME}`
- production workload cluster: `{WORKLOAD_CLUSTER_NAME}`
- conformance gate: `Gate {GATE_ID}`
- phase: `{PHASE_ID}`

The bundle is intentionally evidence-first:

- it does not claim drills already ran;
- it does not claim `Gate {GATE_ID}` passed;
- it freezes the order, ownership, and expected evidence shape for the final production
  conformance wave.

Frozen drill domains:

- `OpenBao`
- `NATS`
- `CloudNativePG`
- `GitOps / Flux recovery`
- `PostHog`
- `Node Fleet Controller / fleet reprovisioning`

Important boundaries:

- the scorecard remains authoritative for conformance scoring;
- this bundle only prepares the production drill and evidence surface;
- no undocumented manual fallback may be used to “pass” a drill.
"""


def render_versions_env() -> str:
    return f"""GATE_ID={GATE_ID}
PHASE_ID={PHASE_ID}
MANAGEMENT_CLUSTER_NAME={MANAGEMENT_CLUSTER_NAME}
WORKLOAD_CLUSTER_NAME={WORKLOAD_CLUSTER_NAME}
DRILL_DOMAINS=openbao,nats,cnpg,gitops,posthog,fleet
SCORECARD_SOURCE=docs/testing/platform-foundation-conformance-scorecard.md
EVIDENCE_TEMPLATE_SOURCE=docs/evidence/platform-foundation/platform-foundation-phase-evidence-template.md
"""


def render_spec_manifest() -> str:
    return f"""gate: {GATE_ID}
phase: {PHASE_ID}
managementCluster: {MANAGEMENT_CLUSTER_NAME}
workloadCluster: {WORKLOAD_CLUSTER_NAME}
scorecard:
  source: docs/testing/platform-foundation-conformance-scorecard.md
  requiredMinimum: 3
evidenceTemplate:
  source: docs/evidence/platform-foundation/platform-foundation-phase-evidence-template.md
domains:
  - openbao
  - nats
  - cnpg
  - gitops
  - posthog
  - fleet
predecessorPackets:
  - P1.8
  - P2.4
  - P3.5
  - P3.6
  - P3.7
  - P3.8
"""


def render_check_script() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-REPLACE_ME_REPO_ROOT}"

python "${REPO_ROOT}/infra/scripts/production_conformance_bundle.py" validate --repo-root "${REPO_ROOT}"
echo "Scaffold root: ${OUTPUT_DIR}"
"""


def render_run_order() -> str:
    return f"""# Production drill run order

Gate target:

- `Gate {GATE_ID}`

Cluster scope:

- management cluster: `{MANAGEMENT_CLUSTER_NAME}`
- workload cluster: `{WORKLOAD_CLUSTER_NAME}`

Frozen run order:

1. `OpenBao` snapshot and restore rehearsal
2. `NATS` outage, replay, and recovery rehearsal
3. `CloudNativePG` backup, recovery, and alerting rehearsal
4. `GitOps / Flux` reconciliation rollback and recovery rehearsal
5. `PostHog` privacy, authoritative capture, and flag fallback validation
6. `Node Fleet Controller` reprovisioning, quarantine, and guarded failover validation
7. final scorecard snapshot and `Gate {GATE_ID}` evidence pack assembly

Rules:

- no later drill may claim success if an earlier blocking drill failed and remained
  unmitigated;
- every drill must attach run transcript, outcome summary, and residuals;
- every scorecard row must link to at least one evidence artifact.
"""


def render_gate_d_outline() -> str:
    return """# Gate D evidence outline

Required sections:

1. header and gate result
2. blocking exceptions and non-blocking residuals
3. drill evidence by domain
4. scorecard snapshot
5. sign-off block

Mandatory evidence classes:

- automated validation
- configuration evidence
- drill evidence
- governance evidence
- boundary evidence
- exception evidence

Mandatory drill domains:

- OpenBao
- NATS
- CloudNativePG
- GitOps / Flux recovery
- PostHog
- Node Fleet Controller / fleet reprovisioning
"""


def render_scorecard_snapshot() -> str:
    rows = "\n".join(
        [
            f"| `C{index:02d}` | `3` | `TBD` | `TBD` | fill in |"
            for index in range(1, 16)
        ]
    )
    return f"""## Conformance Scorecard Snapshot

**Assessment date:** YYYY-MM-DD
**Gate:** Gate {GATE_ID}
**Assessed by:** <names or owner lanes>

| Id | Minimum for gate | Current score | Result | Evidence |
|---|---|---|---|---|
{rows}
"""


def render_drill_to_criteria_map() -> str:
    return """domains:
  openbao:
    criteria:
      - C15
    evidence:
      - raft_snapshot_save
      - raft_snapshot_restore
      - peer_health_check
  nats:
    criteria:
      - C02
      - C03
      - C05
      - C06
      - C15
    evidence:
      - account_backup
      - outage_backlog
      - replay_validation
      - consumer_owner_registry
  cnpg:
    criteria:
      - C15
    evidence:
      - scheduled_backup
      - recovery_bootstrap
      - alert_validation
  gitops:
    criteria:
      - C14
      - C15
    evidence:
      - source_of_truth_boundary
      - suspend_resume_or_rollback
      - reconciliation_recovery
  posthog:
    criteria:
      - C11
      - C12
      - C13
      - C14
      - C15
    evidence:
      - authoritative_capture
      - privacy_review
      - flag_fallback
      - restore_validation
  fleet:
    criteria:
      - C07
      - C08
      - C09
      - C10
      - C15
    evidence:
      - node_add
      - node_replace
      - node_quarantine
      - guarded_failover
      - reprovisioning_drill
"""


def render_domain_readme(*, title: str, purpose: str, expected_evidence: list[str], criteria: list[str]) -> str:
    rendered_evidence = "\n".join(f"- {item}" for item in expected_evidence)
    rendered_criteria = "\n".join(f"- `{item}`" for item in criteria)
    return f"""# {title}

Purpose:

{purpose}

Expected evidence:

{rendered_evidence}

Linked conformance criteria:

{rendered_criteria}

Rules:

- attach command transcript or controller record
- attach outcome summary
- attach residuals if the drill is partial or blocked
"""


def command_render_bundle(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()

    write_text(output_dir / "README.md", render_root_readme())
    write_text(output_dir / "versions.env", render_versions_env())
    write_text(output_dir / "spec-manifest.yaml", render_spec_manifest())
    write_text(output_dir / "scripts" / "check-production-conformance-bundle.sh", render_check_script(), mode=0o750)
    write_text(output_dir / "run-order.md", render_run_order())
    write_text(output_dir / "gate-d-evidence-outline.md", render_gate_d_outline())
    write_text(output_dir / "scorecard" / "gate-d-scorecard-snapshot.md", render_scorecard_snapshot())
    write_text(output_dir / "scorecard" / "drill-to-criteria-map.yaml", render_drill_to_criteria_map())

    write_text(
        output_dir / "domains" / "openbao.md",
        render_domain_readme(
            title="OpenBao",
            purpose="Prove production raft snapshot, restore, and cluster-health recovery behavior.",
            expected_evidence=[
                "raft snapshot save transcript",
                "snapshot restore rehearsal transcript",
                "peer set and health evidence",
            ],
            criteria=["C15"],
        ),
    )
    write_text(
        output_dir / "domains" / "nats.md",
        render_domain_readme(
            title="NATS",
            purpose="Prove outage handling, replay safety, and durable consumer governance.",
            expected_evidence=[
                "account backup transcript",
                "outage drill showing backlog not silent loss",
                "replay validation transcript",
                "consumer ownership and runbook evidence",
            ],
            criteria=["C02", "C03", "C05", "C06", "C15"],
        ),
    )
    write_text(
        output_dir / "domains" / "cnpg.md",
        render_domain_readme(
            title="CloudNativePG",
            purpose="Prove backup, recovery bootstrap, and production alerting for the control-plane database.",
            expected_evidence=[
                "scheduled backup evidence",
                "recovery bootstrap evidence",
                "manual PodMonitor alert validation",
            ],
            criteria=["C15"],
        ),
    )
    write_text(
        output_dir / "domains" / "gitops.md",
        render_domain_readme(
            title="GitOps / Flux Recovery",
            purpose="Prove the production workload source-of-truth boundary and reconciliation recovery behavior.",
            expected_evidence=[
                "desired-state commit or PR evidence",
                "controlled suspend/resume or rollback evidence",
                "reconciliation recovery transcript",
            ],
            criteria=["C14", "C15"],
        ),
    )
    write_text(
        output_dir / "domains" / "posthog.md",
        render_domain_readme(
            title="PostHog",
            purpose="Prove authoritative commercial capture, privacy boundaries, and deterministic flag fallback behavior.",
            expected_evidence=[
                "authoritative event capture evidence",
                "privacy validation showing prohibited telemetry absent",
                "flag fallback and restore validation",
            ],
            criteria=["C11", "C12", "C13", "C14", "C15"],
        ),
    )
    write_text(
        output_dir / "domains" / "fleet.md",
        render_domain_readme(
            title="Node Fleet Controller",
            purpose="Prove fleet reprovisioning, quarantine, and guarded failover under controller ownership.",
            expected_evidence=[
                "node-add transcript",
                "node-replace or reprovisioning transcript",
                "node-quarantine evidence",
                "guarded failover evaluation and outcome",
            ],
            criteria=["C07", "C08", "C09", "C10", "C15"],
        ),
    )

    return 0


def command_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    failures: list[str] = []

    for relative_path, anchors in REQUIRED_ANCHORS.items():
        path = repo_root / relative_path
        if not path.exists():
            failures.append(f"missing required file: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in content:
                failures.append(f"missing anchor in {relative_path}: {anchor}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        "validated production conformance prerequisites: "
        f"gate={GATE_ID} phase={PHASE_ID} "
        "domains=openbao,nats,cnpg,gitops,posthog,fleet"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_bundle = subparsers.add_parser("render-bundle", help="Render the P3.9 conformance bundle")
    render_bundle.add_argument("--output-dir", required=True)
    render_bundle.set_defaults(func=command_render_bundle)

    validate = subparsers.add_parser("validate", help="Validate repo-side prerequisites for the P3.9 bundle")
    validate.add_argument("--repo-root", default=".")
    validate.set_defaults(func=command_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
