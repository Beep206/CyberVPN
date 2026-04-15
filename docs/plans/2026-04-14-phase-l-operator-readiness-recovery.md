# Phase L Operator Readiness Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `Phase L` with operator runbooks, recovery boundaries, rollback and profile-disable drill surfaces, and one fail-closed machine-readable signoff.

**Architecture:** Reuse existing maintained evidence instead of inventing a new control plane. `Phase L` adds a runbook set plus one machine-readable recovery matrix in docs, a cheap local rollback drill wrapper over the maintained `udp-blocked` net-chaos profile, and a `Phase L` signoff example that consumes the runbook matrix, real supported-upstream lifecycle evidence, and rollback-drill evidence.

**Tech Stack:** Markdown, JSON, Bash, PowerShell, Rust `ns-testkit` examples, existing Verta summary schemas.

---

### Task 1: Add operator-facing docs and recovery matrix

**Files:**
- Create: `packages/verta-protocol/docs/runbooks/INDEX.md`
- Create: `packages/verta-protocol/docs/runbooks/REMNAWAVE_UPSTREAM_OUTAGE.md`
- Create: `packages/verta-protocol/docs/runbooks/BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md`
- Create: `packages/verta-protocol/docs/runbooks/REPLAY_CACHE_AND_WEBHOOK_RECOVERY.md`
- Create: `packages/verta-protocol/docs/runbooks/PROFILE_DISABLE_AND_ROLLBACK.md`
- Create: `packages/verta-protocol/docs/runbooks/RECOVERY_BOUNDARIES.md`
- Create: `packages/verta-protocol/docs/runbooks/operator-recovery-matrix.json`

**Step 1:** Write the runbook set around the exact `Phase L` scope from `docs/implementation/PHASED_EXECUTION_PLAN.md`.

**Step 2:** Encode the same incident coverage into `operator-recovery-matrix.json` so the signoff surface can verify operator coverage mechanically.

**Step 3:** Make each incident include runbook path, safe-state actions, operator-visible signals, escalation triggers, recoverable artifacts, and rotation or re-registration expectations.

### Task 2: Add rollback drill wrappers

**Files:**
- Create: `packages/verta-protocol/scripts/operator-rollout-rollback-drill.sh`
- Create: `packages/verta-protocol/scripts/operator-rollout-rollback-drill.ps1`
- Create: `packages/verta-protocol/scripts/operator-profile-disable-drill.sh`
- Create: `packages/verta-protocol/scripts/operator-profile-disable-drill.ps1`

**Step 1:** Make the rollback drill run the maintained `udp-blocked` net-chaos profile only, with default artifact and summary paths under `target/verta/`.

**Step 2:** Make the profile-disable drill delegate to the maintained supported-upstream lifecycle wrapper so operators use one clear command name.

**Step 3:** Keep both wrappers fail-closed and mirror Bash/PowerShell behavior.

### Task 3: Add Phase L machine-readable signoff

**Files:**
- Create: `packages/verta-protocol/crates/ns-testkit/examples/phase_l_operator_readiness_signoff.rs`
- Create: `packages/verta-protocol/scripts/phase-l-operator-readiness.sh`
- Create: `packages/verta-protocol/scripts/phase-l-operator-readiness.ps1`

**Step 1:** Build a fail-closed `ns-testkit` example that consumes:
- `docs/runbooks/operator-recovery-matrix.json`
- `target/verta/remnawave-supported-upstream-lifecycle-summary.json`
- `target/verta/operator-rollout-rollback-drill-summary.json`

**Step 2:** Require exact incident coverage, shared runbook docs, observability mapping, recoverable-vs-rotation boundaries, a passed profile-disable drill, and a passed rollback drill.

**Step 3:** Make the Bash wrapper run the rollback drill first, then emit `target/verta/phase-l-operator-readiness-signoff-summary.json`.

### Task 4: Verification and doc sync

**Files:**
- Modify: `packages/verta-protocol/docs/development/VERIFICATION_COMMANDS.md`
- Modify: `packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`
- Modify: `packages/verta-protocol/docs/implementation/PHASED_EXECUTION_PLAN.md`
- Create: `packages/verta-protocol/docs/implementation/MILESTONE_54_IMPLEMENTATION_NOTES.md`

**Step 1:** Run `cargo test -p ns-testkit --example phase_l_operator_readiness_signoff -- --nocapture`.

**Step 2:** Run `bash scripts/operator-rollout-rollback-drill.sh`.

**Step 3:** Run `bash scripts/phase-l-operator-readiness.sh`.

**Step 4:** Update verification docs and phase/status docs only after the local drill and signoff are green.
