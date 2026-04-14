# Phase M Soak, Canary, And Regression Burn-Down Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `Phase M` with a repeatable bounded soak/canary loop, explicit regression bug-bar discipline, and a fail-closed signoff summary.

**Architecture:** Reuse the maintained live lanes that already exist instead of inventing a new verification stack. A local helper derives the supported-upstream env from the running Remnawave Docker stack, a bounded soak wrapper executes three staged canary checkpoints over the live lifecycle and rollback drills, and a Rust signoff example consumes those stage artifacts plus the documented canary plan and regression ledger.

**Tech Stack:** Bash, PowerShell, Rust examples in `ns-testkit`, JSON evidence artifacts, implementation/runbook docs.

---

### Task 1: Restore repeatable local supported-upstream env derivation

**Files:**
- Create: `packages/northstar-protocol/scripts/with-local-remnawave-supported-upstream-env.sh`
- Create: `packages/northstar-protocol/scripts/with-local-remnawave-supported-upstream-env.ps1`
- Modify: `packages/northstar-protocol/scripts/operator-profile-disable-drill.sh`
- Modify: `packages/northstar-protocol/scripts/operator-profile-disable-drill.ps1`
- Modify: `packages/northstar-protocol/scripts/remnawave-supported-upstream-phase-i-signoff.sh`
- Modify: `packages/northstar-protocol/scripts/remnawave-supported-upstream-phase-i-signoff.ps1`

**Step 1:** Derive local Phase I env from `infra/.env`, `docker inspect remnawave`, and `docker exec remnawave-db`.

**Step 2:** Wire the helper into the operator and Phase I wrappers so local runs no longer depend on a manually prepared shell session.

**Step 3:** Smoke the helper-backed wrappers against the local Docker stack.

### Task 2: Document the Phase M contract

**Files:**
- Create: `packages/northstar-protocol/docs/runbooks/PHASE_M_SOAK_AND_CANARY.md`
- Create: `packages/northstar-protocol/docs/runbooks/phase-m-canary-plan.json`
- Create: `packages/northstar-protocol/docs/development/REGRESSION_BUG_BAR.md`
- Create: `packages/northstar-protocol/docs/development/phase-m-regression-ledger.json`

**Step 1:** Fix the agreed local soak environment, canary stages, rollback triggers, and minimum duration in a runbook and JSON plan.

**Step 2:** Fix the regression severity rules and accepted-tail discipline in a human doc plus machine-readable ledger.

**Step 3:** Keep the phase contract narrow: three canary stages, no open `P0`/`P1`, explicit rollback requirement, and baseline references to the maintained ready summaries.

### Task 3: Implement the bounded soak/canary signoff lane

**Files:**
- Create: `packages/northstar-protocol/crates/ns-testkit/examples/phase_m_soak_canary_signoff.rs`
- Create: `packages/northstar-protocol/scripts/phase-m-soak-canary.sh`
- Create: `packages/northstar-protocol/scripts/phase-m-soak-canary.ps1`

**Step 1:** Write the fail-closed signoff example that loads the canary plan, regression ledger, Phase I baseline, WAN baseline, and per-stage lifecycle/rollback/Phase L summaries from `target/northstar/phase-m-soak/`.

**Step 2:** Require exact stage coverage (`canary_5`, `canary_25`, `canary_100`), minimum duration compliance, rollback proof, `Phase I`/WAN baselines ready, and zero open `P0`/`P1`.

**Step 3:** Add focused unit tests for `ready`, missing stage coverage, and regression-ledger violations.

**Step 4:** Build bash and PowerShell wrappers that execute the three live stages and then run the signoff example.

### Task 4: Sync docs and verify the phase

**Files:**
- Modify: `packages/northstar-protocol/docs/runbooks/INDEX.md`
- Modify: `packages/northstar-protocol/docs/development/VERIFICATION_COMMANDS.md`
- Create: `packages/northstar-protocol/docs/implementation/MILESTONE_55_IMPLEMENTATION_NOTES.md`
- Modify: `packages/northstar-protocol/docs/implementation/PHASED_EXECUTION_PLAN.md`
- Modify: `packages/northstar-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`

**Step 1:** Add the new commands and docs to the maintained reference surfaces.

**Step 2:** Run the helper-backed Phase I wrapper, the bounded Phase M wrapper, and the Phase M example test.

**Step 3:** Run a small security pass over the new files and note any residual risks.
