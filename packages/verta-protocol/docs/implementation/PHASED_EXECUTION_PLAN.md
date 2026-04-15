# Verta Phased Execution Plan

This document replaces the original bootstrap-only phase outline with a full plan from the current milestone-56 baseline to a production-ready Verta v0.1 release.
It is intentionally execution-oriented: the specs under `docs/spec/` remain normative, while this file defines the delivery phases, stop rules, and exit criteria we will use to finish the project without endless scope drift.

Naming note:

- `Verta` is the canonical public protocol name.
- Package paths, workflow filenames, env vars, and artifact roots now use `Verta`.
- Internal crate and binary identifiers such as `ns-*` remain stable technical IDs.

## Governing Inputs

- `docs/spec/adaptive_proxy_vpn_protocol_master_plan.md`
- `docs/spec/verta_blueprint_v0.md`
- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_remnawave_bridge_spec_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_implementation_spec_rust_workspace_plan_v0_1.md`
- `docs/spec/verta_protocol_rfc_draft_v0_1.md`

## Current Baseline

As of milestone 56, Verta now has:

- a working Rust workspace and crate graph
- frozen wire/auth/manifest/session baselines
- a non-fork Remnawave bridge path with realistic HTTP adapter coverage
- a live QUIC/H3 control and relay path
- a hardened datagram slice with fallback rules, rollout controls, and machine-readable operator verdict surfaces
- compatible-host Linux/macOS/Windows evidence lanes
- opt-in fuzz, perf, interop, rollout, and release-shaped workflow lanes

That means the project is no longer blocked on core feature invention or release-critical closure work.
The remaining work is post-v0.1 maintenance rather than a missing production phase.

## Phase Count

Under the current specs and the current implementation baseline, `Phase I`, `Phase J`, `Phase K`, `Phase L`, `Phase M`, and `Phase N` are now closed by real supported-upstream, WAN/chaos, sustained-verification, operator-readiness, bounded soak/canary evidence, and final release closure, and there are **0 remaining delivery phases** before we should call Verta `production-ready`.

Important planning rule:

- these are **delivery phases**, not micro-milestones
- each phase may require multiple narrow implementation milestones
- we do **not** add new phases casually just because a phase takes several milestones
- we only add a new phase if a governing spec changes materially or real upstream/WAN evidence exposes a previously hidden workstream that cannot fit inside the current phase structure

## What Production-Ready Means

Verta is only production-ready when all of the following are true:

- the non-fork Remnawave integration works against a real supported upstream environment, not only a realistic local test path
- datagram behavior is supported by real deployment-grade evidence, not only deterministic lab and compatible-host evidence
- release gates are sustained and enforced, not just opt-in
- operators have runbooks, rollback discipline, recovery drills, and explicit failure handling
- soak and canary validation have run long enough to expose stability regressions
- release artifacts, manifests, and supported-environment claims are attributable, inspectable, and reproducible
- docs, ADRs, and implementation status are aligned with actual behavior

## Strict Movement Rules

We will move through the remaining phases under the following rules:

1. A phase is not complete until every exit criterion in that phase is satisfied.
2. We do not start the next phase as “the main track” while the previous phase still has open blockers.
3. New feature work that is not on the critical path to production-ready is frozen unless it removes a current phase blocker.
4. If implementation reveals a spec gap or ambiguity that changes behavior, we stop, record the gap, and resolve it through the spec or ADR process before calling the phase complete.
5. Every phase must leave behind updated docs, verification commands, and status tracking, not just code.
6. Every phase must preserve the existing guardrails:
   - Remnawave stays external and non-fork
   - bridge deployment topology stays explicit
   - session core stays transport-agnostic
   - `0-RTT` stays disabled unless an explicit normative decision changes that

## Phase Map

| Phase | Status | Purpose | Typical micro-milestones | Exit Shape |
| --- | --- | --- | --- | --- |
| Phase A | complete | Workspace foundation | done | repo/build baseline exists |
| Phase B | complete | Protocol core and wire layer | done | frozen codec/session baseline exists |
| Phase C | complete | Auth, manifest, trust material | done | manifest/auth/policy baseline exists |
| Phase D | complete | Bridge contract and Remnawave boundary | done | non-fork bridge baseline exists |
| Phase E | complete | First carrier and datagram slice | done | QUIC/H3 plus rollout/fallback baseline exists |
| Phase F | complete enough for current scope | Runtime and CLI surfaces | done | maintained binaries and validation surfaces exist |
| Phase G | complete enough for current scope | Fixtures, fuzz, perf, interop scaffolding | done | release-facing verification scaffold exists |
| Phase H | complete enough for current scope | ADR/doc/status discipline | done | implementation notes and status discipline exist |
| Phase I | complete | Real upstream and deployment-grade truth pass | done | supported upstream plus deployment-reality path is proven |
| Phase J | complete | WAN-grade interop and network-chaos expansion | 2-3 | interop is broader than deterministic lab |
| Phase K | complete | Sustained verification discipline | 1-2 | required release evidence is automated and durable |
| Phase L | complete | Operator runbooks, rollback, recovery, and observability discipline | 1-2 | operators can safely run and recover the system |
| Phase M | complete | Soak, canary, and regression burn-down | done | stability is demonstrated over time, not inferred |
| Phase N | complete | Final production-ready closure | done | release integrity, docs, and support claims are closed |

Under current assumptions, the remaining production-ready work is therefore **0 delivery phases** and **0 release-critical milestones**.
Any new work from this point forward is maintenance, follow-on hardening, or a new roadmap item rather than unfinished `v0.1` closure.

## Completed Foundations

The completed phases still matter because the remaining phases depend on them:

- `Phase A` gave us the workspace, tooling, and reviewable crate layout.
- `Phase B` gave us the frozen wire/session baseline and strict malformed-input handling.
- `Phase C` gave us signed manifests, token verification, and policy derivation.
- `Phase D` gave us the non-fork Remnawave bridge boundary and public/private bridge split.
- `Phase E` gave us the first live carrier, the datagram path, and fallback discipline.
- `Phase F` gave us CLI and runtime validation surfaces.
- `Phase G` gave us fixtures, corpora, perf hooks, and machine-readable release-shaped evidence.
- `Phase H` gave us implementation notes, ADR discipline, and status synchronization.

The completed phases now form one attributable release story: prove, harden, operate, soak, and close what exists without widening the protocol or bridge boundary.

## Phase I — Upstream Truth And Deployment Reality

### Status Note

As of `2026-04-14`, the maintained supported-upstream chain (`47 -> 48 -> 49 -> 50`) has passed against the deployment label `remnawave-local-docker`; the maintained `Phase J` evidence chain reports `udp_wan_staging_interop = ready`, `udp_net_chaos_campaign = ready`, and `udp_phase_j_signoff.phase_j_state = "honestly_complete"`; the sustained `Phase K` workflow and ruleset surface is active; the maintained `Phase L` signoff reports `phase_l_state = "honestly_complete"`; the maintained `Phase M` signoff reports `phase_m_state = "honestly_complete"` with `observed_duration_seconds = 52` against the agreed `20` second floor; and the maintained `Phase N` signoff now closes the release from one clean git-attributed repository state. There is no later production phase after this one.

### Objective

Prove that Verta works against a real supported Remnawave environment and a real deployment-shaped bridge topology, not only a realistic local simulation.

### Why This Phase Exists

The project originally had strong local and realistic-test-path evidence, but not a real supported-upstream deployment pass.
That gap is now closed; this section remains here as the historical rationale for why `Phase I` existed and why later phases are allowed to treat upstream and deployment truth as established baseline evidence.

### In Scope

- supported Remnawave version matrix for the non-fork path
- real bridge import, manifest refresh, token exchange, and webhook reconciliation against upstream
- explicit handling of upstream auth failures, timeouts, drift, and partial unavailability
- real remote/shared store deployment shape validation
- operator-visible failure modes when the upstream contract changes incompatibly

### Out Of Scope

- widening bridge `/v0/*` contracts
- making the gateway or session core depend directly on Remnawave internals
- forking Remnawave panel or node logic

### Deliverables

- a documented supported-upstream matrix
- a repeatable real-upstream verification recipe
- explicit upstream failure taxonomy and runbook-visible failure signals
- evidence artifacts for real import, refresh, token, revoke, disable, and webhook flows
- implementation notes for any integration quirks that are operationally relevant

### Exit Criteria

- at least one real supported upstream environment passes end-to-end Bridge flows
- revoke/disable/entitlement changes propagate correctly and fail safely
- upstream auth/timeout/outage behavior is explicit and operator-visible
- bridge deployment topology remains unchanged and non-fork
- no hidden contract widening is needed to make the integration pass

### Main Risks

- upstream API behavior drifts from the realistic local path
- deployment auth and secret handling expose hidden operational gaps
- webhook timing, retries, or metadata shape differ from assumed behavior

## Phase J — WAN-Grade Interop And Chaos Expansion

### Status Note

As of `2026-04-13`, `Phase J` is honestly complete. The maintained WAN/staging lane passed, the full local `net_chaos` matrix passed with retained packet-capture artifacts, and the maintained signoff surface now reports `phase_j_state = "honestly_complete"`.

### Objective

Move the datagram story from deterministic lab plus compatible-host evidence toward real WAN-like deployment evidence with scheduled interoperability and chaos coverage.

### Why This Phase Exists

The current datagram stack is deep, but most of the evidence is still deterministic lab and compatible-host verification.
The security and interop spec explicitly requires interop to be proven, explicit, scheduled, and exercised under bad network conditions, not only under clean localhost assumptions.

### In Scope

- broader cross-network datagram validation beyond the current deterministic profile set
- explicit release-candidate interop permutations across revisions and roles
- network-chaos profiles for loss, reordering, delay, black-hole windows, fallback forcing, and rollback paths
- artifact retention and comparability for failed release-gating runs
- verification of required-no-silent-fallback behavior outside the current tight lab loop

### Out Of Scope

- inventing new transport personas just to have more test coverage
- widening protocol semantics without a spec-backed reason

### Deliverables

- one or more WAN-like or staging-backed datagram evidence lanes
- scheduled or repeatable interop matrix permutations for release candidates
- explicit chaos profiles aligned with the security/interop plan
- operator-readable summaries that distinguish lab evidence from broader deployment evidence

### Exit Criteria

- release-candidate validation includes interop permutations broader than same-build compatible-host runs
- WAN-like or staging-backed datagram evidence exists for the critical fallback and degradation paths
- failed runs retain enough artifacts for diagnosis
- release-facing consumers can separate deterministic-lab evidence from broader deployment evidence

### Main Risks

- flaky infrastructure creates false negatives
- environment drift obscures whether failures are product bugs or lab issues
- WAN evidence reveals transport behaviors that deterministic lab did not expose

## Phase K — Sustained Verification Discipline

### Status Note

As of `2026-04-13`, `Phase K` is honestly complete. The repository now has real root-level sustained verification workflows for bounded protected-branch evidence, nightly staged-rollout plus net-chaos evidence, and fail-closed release-evidence certification; active GitHub rulesets now enforce the bounded gate on `main` and the full release-evidence gate on `release/**` and `rc/**`; the maintained bounded, staged, and net-chaos local recipes pass; and the release-evidence chain fails closed when required multi-host artifacts are absent instead of silently degrading.

### Objective

Turn the current release-facing verification stack from mostly opt-in discipline into sustained, enforced, and attributable release evidence.

### Why This Phase Exists

The current stack is strong but still optional in too many places.
Production-ready claims require durable verification posture, not only a collection of runnable tools.

### In Scope

- bounded smoke fuzz on protected branches or required pre-release paths
- longer fuzz campaigns on nightly or dedicated runners
- required perf, interop, and release-shaped gates for release branches or release-candidate promotion
- artifact retention, baseline comparison, and non-cherry-picked reporting discipline
- clear separation between PR-time bounded gates and longer scheduled gates

### Out Of Scope

- making every heavy lane mandatory on every ordinary pull request
- replacing deterministic fixture coverage with pure fuzzing

### Deliverables

- a required gate map by branch or release phase
- CI enforcement for the minimum sustained gate set
- nightly or scheduled longer-running fuzz/interop/perf campaigns
- published baseline comparison rules against prior release candidates

### Exit Criteria

- minimum smoke fuzz runs in sustained automation, not only manually
- longer fuzz and interop campaigns run on a defined schedule
- perf numbers are published with environment metadata
- release promotion is automatically blocked when required evidence is missing or failing

### Main Risks

- CI cost and runtime overhead
- flaky gates erode trust
- pressure to disable required checks during schedule crunch

## Phase L — Operator Readiness, Runbooks, And Recovery

### Status Note

As of `2026-04-14`, `Phase L` is honestly complete. The repository now carries a maintained operator runbook set plus a machine-readable recovery matrix, a dedicated operator rollback drill over the explicit `udp-blocked` fallback path, and a fail-closed `phase_l_operator_readiness_signoff` surface that consumes real supported-upstream lifecycle evidence plus rollback-drill evidence. The maintained local signoff now reports `phase_l_state = "honestly_complete"`.

### Objective

Make Verta operable by people under stress, not only correct in code and tests.

### Why This Phase Exists

The threat model explicitly treats operator mistakes, incident response, rollback, secret handling, replay recovery, and profile burn/fingerprinting events as first-class concerns.
Production-ready software needs recovery discipline, not just implementation correctness.

### In Scope

- operator runbooks for upstream outage, bridge auth drift, replay/cache issues, webhook problems, secret rotation, profile disable, and rollback
- rollout discipline for safe enable/disable and canary rollback
- observability and alerting expectations tied to operator decisions
- recovery guidance for recoverable versus non-recoverable state
- explicit operator-visible errors and escalation paths

### Out Of Scope

- building a giant admin platform
- broad new product features that are not needed for safe operation

### Deliverables

- operator runbook set
- rollback and disable drills
- deployment and secret-handling guidance
- incident playbooks tied to current observability hooks
- documented support boundaries and recovery expectations

### Exit Criteria

- operators can restore a safe state within documented runbooks
- rollback and profile-disable drills succeed
- runbooks state what artifacts are recoverable and what requires re-registration or rotation
- observability is sufficient for the runbooks to be actionable

### Main Risks

- documentation exists but is not actually exercised
- operators bypass safety controls during incidents
- observability is too shallow for real diagnosis

## Phase M — Soak, Canary, And Regression Burn-Down

### Status Note

As of `2026-04-14`, `Phase M` is honestly complete. The maintained `phase-m-soak-canary` lane passed on the agreed `remnawave-local-docker` environment, all three canary stages (`canary_5`, `canary_25`, `canary_100`) produced ready lifecycle, rollback, and stage-local `Phase L` artifacts, and the final signoff reports `phase_m_state = "honestly_complete"` with `rollback_proven = true`, `p0_open_count = 0`, `p1_open_count = 0`, and `observed_duration_seconds = 52`.

### Objective

Demonstrate sustained stability over time and under controlled rollout, then burn down the remaining serious regression risk.

### Why This Phase Exists

Correctness under short deterministic tests does not prove operational stability.
The security and interop plan explicitly calls for extended soak and canary validation for release candidates and production-like staging.

### In Scope

- extended soak runs on representative staging or controlled production-like environments
- canary rollout validation with rollback drills
- regression ledger and bug-bar discipline
- performance budget checks under longer sustained load, not just point benchmarks

### Out Of Scope

- indefinite open-ended soak with no exit bar
- “wait longer” as a substitute for fixing real defects

### Deliverables

- agreed soak duration and environment
- canary procedure and rollback verification
- regression triage board with severity rules
- comparison against prior release candidates or baselines

### Exit Criteria

- soak completes for the agreed duration without P0/P1 failures
- no catastrophic regression relative to the previous release-candidate baseline
- rollback under canary failure is proven
- unresolved bugs are reduced to an agreed, explicitly accepted tail

### Main Risks

- long-running resource leaks or state drift
- intermittent upstream or network problems that expose hidden assumptions
- schedule pressure to declare stability before burn-down is complete

## Phase N — Production-Ready Closure

### Status Note

As of `2026-04-14`, `Phase N` is honestly complete. The repository now carries an explicit release checklist, an attributable artifact story, a supported environment matrix, an accepted known-limitations list, and a fail-closed `phase_n_production_ready_signoff` surface. The final signoff reports `phase_n_state = "honestly_complete"` only when the accepted phase summaries are ready, the release docs are present, and the git branch plus commit plus clean-state facts are unambiguous.

### Objective

Close the project with an attributable, supportable, and reviewable production-ready release decision.

### Why This Phase Exists

Even after the engineering work is done, there is still a final closure problem:
supported environments, release integrity, documentation, and known limitations must be frozen and reviewable.

### In Scope

- final release checklist
- supported-environment matrix
- supply-chain and release-integrity checks
- final doc and ADR sync
- explicit known-limitations list
- go/no-go review using the exit criteria from all earlier phases

### Out Of Scope

- speculative post-v0.1 roadmap work
- new major transport or product scope

### Deliverables

- release checklist
- attributable build and artifact story
- final support matrix
- known limitations and deferred work list
- production-ready signoff record

### Exit Criteria

- release artifacts are attributable, inspectable, and built from unambiguous state
- supported deployment and upstream environments are explicitly documented
- no blocking spec drift, security blockers, operator blockers, or release-integrity blockers remain
- the project can honestly state why it is production-ready and what is still intentionally out of scope

### Main Risks

- documentation lags behind reality
- release-integrity expectations are weaker than the protocol/security posture requires
- unresolved operational limitations are hidden instead of declared

## Phase-by-Phase Decision Gates

We will use the following strict promotion gates:

- `Phase I -> J`: only after real upstream and deployment-shaped validation is green
- `Phase J -> K`: only after broader WAN/chaos evidence exists, not just compatible-host lab evidence
- `Phase K -> L`: only after required release evidence is sustained in automation
- `Phase L -> M`: only after operators have tested runbooks and rollback drills
- `Phase M -> N`: only after soak/canary stability is demonstrated and serious regressions are burned down
- `Phase N -> done`: only after release integrity, support matrix, and final docs are complete

## How To Count Remaining Work

The planning number we should use from now on is:

- **0 remaining production phases**
- **0 release-critical milestones**

If a later bug or operational issue appears, that is post-closure maintenance work rather than unfinished `v0.1` release gating.

## What We Should Not Do

To avoid dragging the project forever, we should not:

- invent new protocol features that are not required for the current release target
- widen bridge-domain or Remnawave contracts to shortcut validation
- treat local deterministic evidence as a substitute for deployment-grade evidence
- keep release-critical gates optional forever
- postpone runbooks, rollback drills, and operator recovery until after release
- call the project production-ready before the phase exit criteria are satisfied

## Working Agreement

From this point forward, the execution model is:

- one active production phase at a time
- each milestone must name which phase it advances
- each milestone must move a current phase toward its explicit exit criteria
- if a task does not advance the current phase or close a blocker discovered in the current phase, it is not on the critical path

That gave the project a bounded finish line:

- not “endless milestones”
- but a production-ready closure with explicit stop conditions and an attributable final signoff
## Historical Backlog Snapshot For Phase I

The section below is kept only as historical context for how the release closure sequence started.

Planning assumption:

- `Phase I` should take about **3 narrow milestones**
- the current working target is **milestones 47-49**
- if real upstream behavior exposes a spec or contract blocker, we stop and record it instead of pretending the phase is still on schedule

### Milestone 47 — Real Upstream Verification Harness

#### Goal

Create the first real supported-upstream verification lane for the non-fork Remnawave path without widening bridge or session contracts.

#### Expected Output

- a repeatable real-upstream verification recipe
- one machine-readable verification surface for supported upstream resolution/import or manifest/token paths
- explicit fail-closed handling for upstream auth failure, timeout, drift, and unavailable-state cases
- implementation notes documenting the supported environment assumptions

#### Milestone 47 Status

- implemented in `crates/ns-testkit/examples/remnawave_supported_upstream_verification.rs`
- operator wrappers exist in `scripts/remnawave-supported-upstream-verify.ps1` and `scripts/remnawave-supported-upstream-verify.sh`
- the harness emits a fail-closed supported-upstream summary with explicit missing-environment, unsupported-version, auth-failure, timeout, response-shape-drift, webhook-signature, unavailable, stale, and incompatible-contract states
- the maintained adapter now has a reviewed schema-drift regression fixture for upstream account normalization
- `Phase I` is materially closer to exit, but milestone 47 does **not** close real lifecycle/reconciliation evidence or the deployment-grade remote/shared-store reality gate

#### Exit Signal

- a real upstream environment can be contacted through the maintained bridge path
- the verification lane distinguishes supported upstream success from missing-environment or incompatible-upstream failure
- no bridge `/v0/*` contract widening is needed

### Milestone 48 — Real Lifecycle And Reconciliation Pass

#### Goal

Prove that lifecycle and reconciliation behavior works correctly against the supported upstream path, not only in local realistic tests.

#### Expected Output

- real import or refresh or token-exchange coverage against the supported upstream path
- real revoke or disable or entitlement-change propagation evidence
- webhook and reconciliation handling under partial failure or retry conditions
- operator-visible failure taxonomy for upstream drift and inconsistent state

#### Milestone 48 Status

- implemented in `crates/ns-testkit/examples/remnawave_supported_upstream_lifecycle_verification.rs`
- operator wrappers exist in `scripts/remnawave-supported-upstream-lifecycle-verify.ps1` and `scripts/remnawave-supported-upstream-lifecycle-verify.sh`
- the lifecycle harness primes an active bridge path first, then waits for a real operator-driven upstream lifecycle change and verifies stable denial behavior for manifest bootstrap, refresh manifest fetch, and token exchange on that same bridge runtime path
- the lifecycle summary fails closed on missing environment, unsupported upstream version, auth failure, timeout, response-shape drift, webhook-signature failure, lifecycle drift, reconcile lag, stale snapshot state, replay-sensitive inconsistency, and incompatible-contract conditions
- `Phase I` is materially closer to exit after milestone 48, but milestone 49 is still required for the deployment-grade bridge reality gate

#### Exit Signal

- revoke or disable and entitlement updates propagate safely
- replay-sensitive and reconciliation-sensitive paths remain fail-closed
- upstream inconsistency results in explicit operator-visible errors rather than silent divergence

### Milestone 49 — Deployment-Grade Bridge Reality Gate

#### Goal

Run the `Phase I` decision gate by validating the deployment-shaped bridge reality path under a supported upstream environment and then making the explicit `Phase I complete` vs `Phase I blocked` call.

#### Expected Output

- remote/shared store plus supported-upstream deployment validation
- explicit startup, auth, timeout, failover, and degraded-upstream evidence for the real path
- phase-level doc sync that states exactly what upstream versions and deployment assumptions are supported
- a clear promotion decision: `Phase I complete` or `Phase I blocked`

#### Milestone 49 Status

- implemented in `crates/ns-testkit/examples/remnawave_supported_upstream_deployment_reality_verification.rs`
- operator wrappers exist in `scripts/remnawave-supported-upstream-deployment-reality-verify.ps1` and `scripts/remnawave-supported-upstream-deployment-reality-verify.sh`
- the deployment-reality harness consumes milestone-47 and milestone-48 summaries as required inputs, then validates the maintained deployment-shaped bridge runtime over the shared-durable service-backed store path and emits a fail-closed operator summary
- the deployment-reality summary is explicitly control-plane issuance only; it does not claim transport or datagram readiness
- the harness now fails closed on missing environment, unsupported upstream version, upstream auth failure, timeout, response-shape drift, webhook-signature failure, lifecycle drift, reconcile lag, stale snapshot state, replay-sensitive inconsistency, remote-store auth mismatch, remote backend unavailability, health-check drift, startup ordering failure, partial failover, and incompatible-contract conditions
- milestone 49 adds the `Phase I` decision gate, but `Phase I` is still only complete after a real supported deployment actually passes this lane; until then `Phase I` remains honestly blocked on missing operator-run evidence

#### Exit Signal

- at least one supported upstream environment passes the full bridge reality path
- outage, timeout, auth-drift, and partial-failure modes are explicit and safe
- supported-upstream matrix and deployment assumptions are documented
- `Phase I` exit criteria in this document can be honestly marked complete

### Milestone 50 — Operator-Run Supported Deployment Pass And Honest Phase I Closure

#### Goal

Run the maintained milestone-47, milestone-48, and milestone-49 chain through one operator-facing signoff surface and make the honest `Phase I complete` vs `Phase I blocked` call based on real supported deployment evidence rather than local optimism.

#### Expected Output

- one machine-readable `Phase I` operator signoff summary
- one Windows-first plus Bash wrapper that runs the supported-upstream verification chain in order
- fail-closed blocker reporting when the supported deployment environment, deployment identity, or prior-lane evidence is missing or incompatible
- explicit confirmation that the deployment-reality lane remains control-plane issuance only

#### Milestone 50 Status

- implemented in `crates/ns-testkit/examples/remnawave_supported_upstream_phase_i_signoff.rs`
- operator wrappers exist in `scripts/remnawave-supported-upstream-phase-i-signoff.ps1` and `scripts/remnawave-supported-upstream-phase-i-signoff.sh`
- the signoff lane consumes milestone-47, milestone-48, and milestone-49 summaries as required inputs, checks deployment-label presence, prior-lane pass state, base-URL consistency, expected-account consistency, upstream-version consistency, and explicit `control_plane_issuance_only` scope, then emits one fail-closed signoff summary
- milestone 50 does **not** simulate closure when no supported deployment environment is available; it records exact blockers instead
- the local repository run still leaves `Phase I` blocked because the required supported deployment environment was not available during the milestone-50 pass

#### Exit Signal

- milestones 47, 48, 49, and 50 all pass together against at least one real supported deployment
- the final signoff summary reports an honest completion state instead of inferred readiness
- the same signoff output clearly records which exact deployment passed and what still remains out of scope
