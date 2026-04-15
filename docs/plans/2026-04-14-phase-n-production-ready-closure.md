# Phase N Production-Ready Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `Phase N` with explicit release docs, a machine-readable production-ready signoff, and one attributable final verdict.

**Architecture:** Reuse the accepted phase summaries from `Phase I`, `Phase J`, `Phase L`, and `Phase M` instead of inventing a new evidence stack. Add a narrow `docs/release/` surface for checklist, support matrix, artifact story, and known limitations, then add a fail-closed `phase_n_production_ready_signoff` example plus wrappers that combine those docs with git attribution facts from the current repository state.

**Tech Stack:** Markdown, JSON, Rust examples in `ns-testkit`, Bash, PowerShell, git metadata.

---

### Task 1: Add the release-closure document set

**Files:**
- Create: `packages/verta-protocol/docs/release/INDEX.md`
- Create: `packages/verta-protocol/docs/release/PRODUCTION_READY_CHECKLIST.md`
- Create: `packages/verta-protocol/docs/release/ARTIFACT_ATTRIBUTION.md`
- Create: `packages/verta-protocol/docs/release/SUPPORTED_ENVIRONMENT_MATRIX.md`
- Create: `packages/verta-protocol/docs/release/KNOWN_LIMITATIONS.md`
- Create: `packages/verta-protocol/docs/release/production-ready-checklist.json`
- Create: `packages/verta-protocol/docs/release/supported-environment-matrix.json`
- Create: `packages/verta-protocol/docs/release/known-limitations.json`

**Step 1:** Write the final release checklist and artifact-attribution docs with exact evidence refs.

**Step 2:** Fix the supported environment matrix to the environments we can honestly support or document today.

**Step 3:** Record accepted non-blocking limitations explicitly instead of hiding them in scattered notes.

### Task 2: Add the machine-readable Phase N signoff

**Files:**
- Create: `packages/verta-protocol/crates/ns-testkit/examples/phase_n_production_ready_signoff.rs`
- Create: `packages/verta-protocol/scripts/phase-n-production-ready.sh`
- Create: `packages/verta-protocol/scripts/phase-n-production-ready.ps1`

**Step 1:** Load the `Phase I`, `Phase J`, `Phase L`, and `Phase M` summaries plus the new release JSON docs.

**Step 2:** Require ready and honest closure across prior phases, complete release docs, explicit supported environments, zero blocking limitations, present sustained-verification workflow files, and valid git attribution inputs.

**Step 3:** Add focused unit tests for `ready`, dirty-worktree `hold`, and blocking-limitation `hold`.

### Task 3: Verify the closure path honestly

**Files:**
- Modify: `packages/verta-protocol/docs/development/VERIFICATION_COMMANDS.md`
- Modify: `packages/verta-protocol/docs/implementation/PHASED_EXECUTION_PLAN.md`
- Modify: `packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`
- Create: `packages/verta-protocol/docs/implementation/MILESTONE_56_IMPLEMENTATION_NOTES.md`

**Step 1:** Run the focused example tests and the final wrapper.

**Step 2:** If the final signoff is blocked, record the exact blocker instead of hand-waving.

**Step 3:** If the blocker is only ambiguous git attribution, create one intentional local commit and rerun the final wrapper against the clean state.

**Step 4:** Sync all status docs to the actual outcome and note residual risks.
