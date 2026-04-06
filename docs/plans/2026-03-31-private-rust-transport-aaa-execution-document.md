# Private Rust Transport Platform AAA+ Execution Document

> Companion to `docs/plans/2026-03-31-private-rust-transport-aaa-implementation-plan.md`.
> This file is the execution contract for the first implementation wave.

## Purpose

This document turns the Helix strategy into a strict execution package with:

- phase-by-phase `SLO` and `SLA` values;
- a hard role matrix for `admin / ops / sre`;
- exact file lists and acceptance criteria for `Phase 0` and `Phase 1`;
- explicit escalation rules so the team can start implementation without reopening the same decisions.

---

## Definitions

- `SLO`: target engineering or runtime outcome the phase must achieve to be considered healthy.
- `SLA`: maximum tolerated bound before the phase must be escalated, paused, or considered failed.
- `Blocked`: a phase cannot progress without a decision, artifact, or green gate that is explicitly marked mandatory.
- `Promotion`: moving the transport from `lab` to `canary`, or from `canary` to `stable`.

---

## Execution Rules

1. No service code starts before `Phase 0` and `Phase 1` are formally complete.
2. No hidden scope is allowed in `Phase 0` and `Phase 1`; every artifact must exist as a tracked file.
3. No phase is “mostly done”. Every phase closes only when all mandatory artifacts and gates are green.
4. No rollout authority exists outside the role matrix in this document.
5. No sensitive anti-blocking mechanics are documented outside restricted internal governance docs.
6. No desktop exposure happens before benchmark instrumentation and rollback drills exist.
7. Config-first protocol adaptation is preferred over binary-first adaptation whenever the required change fits inside already-supported capability families.

---

## Hard Role Matrix

### Role Intent

- `admin`: product and release authority, approves channel promotion and business-facing enablement.
- `ops`: day-to-day operational control for node grouping, rollout handling, pause/resume, and visibility.
- `sre`: emergency authority, reliability owner, secret/key rotation owner, incident commander.

### Permissions Matrix

| Action | Admin | Ops | SRE |
|---|---|---|---|
| Approve architecture freeze | Approve | Consulted | Approve |
| Approve SLO/SLA thresholds | Approve | Consulted | Approve |
| Create/edit restricted resilience governance doc | No | No | Yes |
| View rollout state | Yes | Yes | Yes |
| View benchmark dashboards | Yes | Yes | Yes |
| Enable node for Helix | No | Yes | Yes |
| Disable node for Helix | No | Yes | Yes |
| Assign node group | No | Yes | Yes |
| Publish rollout batch to `lab` | No | Yes | Yes |
| Publish rollout batch to `canary` | Approve | Execute | Execute |
| Publish rollout batch to `stable` | Approve | No | Execute |
| Pause rollout | No | Yes | Yes |
| Resume rollout | Approve | Execute | Execute |
| Revoke manifest version | Approve | No | Yes |
| Force rollback | No | No | Yes |
| Quarantine node | No | Yes | Yes |
| Rotate adapter internal token | No | No | Yes |
| Rotate manifest signing key | No | No | Yes |
| Declare incident | No | Yes | Yes |
| Close incident | Approve | Consulted | Approve |
| Approve external beta | Approve | Consulted | Approve |

### RACI Summary

| Deliverable | Admin | Ops | SRE |
|---|---|---|---|
| Product quality bar | A | C | R |
| Node readiness and rollout hygiene | I | R | A |
| Incident response and rollback authority | I | C | A/R |
| Secret and key custody | I | I | A/R |
| Channel promotion decisions | A | C | R |

Legend:

- `R`: responsible
- `A`: accountable
- `C`: consulted
- `I`: informed

---

## Phase-by-Phase SLO / SLA Contract

### Phase 0: Product Guardrails, Benchmark Model, Restricted Governance

**SLO**

- `100%` of mandatory Phase 0 artifacts exist in git.
- `100%` of blocking architectural decisions are closed and recorded.
- `0` unresolved `P0` architecture blockers remain at phase exit.
- Review turnaround for Phase 0 documents: `<= 1 business day`.

**SLA**

- Any blocking decision older than `24 hours` triggers escalation to `admin + sre`.
- Any missing Phase 0 artifact by the planned phase end automatically blocks `Phase 1`.

### Phase 1: Contracts and Architecture Source of Truth

**SLO**

- `100%` of schemas are versioned.
- `100%` of example fixtures validate successfully.
- Contract validation runtime stays `<= 30 seconds` in local execution.
- `0` ambiguous required fields remain in manifest, node, and capability contracts.
- `0` undefined adaptability semantics remain for future profile-driven contract evolution.

**SLA**

- Any breaking contract dispute unresolved after `24 hours` escalates to `admin + sre`.
- Any validation failure in the mandatory fixture set must be fixed the same business day.

### Phase 2: Adapter Service Skeleton

**SLO**

- `/healthz`, `/readyz`, and `/metrics` available with lab uptime target `>= 99.9%`.
- Cold start to ready target `<= 15 seconds`.
- `cargo fmt`, `clippy -D warnings`, and tests green at `100%`.

**SLA**

- Crash-looping skeleton service is a `P1` issue and must be fixed within `4 hours`.
- Unresolved build or lint failures longer than `1 business day` block Phase 3.

### Phase 3: Adapter Persistence, Signing, Registry, Rollout Policy

**SLO**

- Manifest resolve latency intra-region: `p95 <= 200 ms`.
- Manifest sign/verify success: `100%`.
- Revoke propagation target: `<= 60 seconds`.
- Node heartbeat freshness accuracy: `>= 99.9%`.
- Adapter design preserves profile-driven adaptation paths so config-level transport changes do not automatically require coordinated binary rollouts.

**SLA**

- Any signing or revoke defect is `P0` and blocks backend/Desktop integration until fixed.
- Any registry drift above `0.5%` from expected node inventory must be investigated within `4 hours`.

### Phase 4: Node Daemon and Host Integration

**SLO**

- Bundle apply success in lab: `>= 99.5%`.
- Rollback recovery target: `p95 <= 90 seconds`.
- Health failure detection target: `<= 15 seconds`.
- Baseline transport disruption caused by daemon rollout: `0`.

**SLA**

- Any failed rollback is `P0` and blocks the next rollout wave.
- Any baseline transport disruption must be mitigated within `5 minutes`.

### Phase 5: Backend Integration and Entitlement Mediation

**SLO**

- Unauthorized access rate to Helix admin routes: `0`.
- Entitlement evaluation latency in backend: `p95 <= 75 ms` excluding adapter/network time.
- Adapter call success in integration tests: `>= 99.9%`.

**SLA**

- Any auth boundary defect is `P0` and must be fixed within `4 hours`.
- Any backend-to-adapter contract break blocks Desktop integration the same day.

### Phase 6: Lab Harness, Benchmark Framework, Observability Baseline

**SLO**

- Metrics scrape success: `>= 99.0%`.
- Dashboard freshness target: `<= 60 seconds`.
- Benchmark job success rate: `>= 95%`.
- Critical alert delivery time: `<= 120 seconds`.

**SLA**

- Any blind spot in critical metrics must be fixed within `1 business day`.
- Missing stale-heartbeat or rollback alerts block canary immediately.

### Phase 7: Desktop Runtime Integration and Fallback Hardening

**SLO**

- Desktop connect success in lab: `>= 99.5%`.
- Unhealthy runtime detection target: `<= 10 seconds`.
- Restore to stable core target: `p95 <= 20 seconds`.
- Sidecar signature verification success: `100%`.
- Desktop runtime accepts profile-driven manifest evolution within the supported capability window.

**SLA**

- Any crash loop or broken fallback path blocks canary.
- Emergency desktop kill-switch activation path must be executable within `10 minutes`.

### Phase 8: Worker Automation, Audits, Rollout Controls

**SLO**

- Scheduled audit job success: `>= 99.0%`.
- Stale-heartbeat alert detection target: `<= 120 seconds`.
- Stuck-rollout detection target: `<= 300 seconds`.

**SLA**

- A degraded audit pipeline must be restored within `4 hours`.
- Stable promotion is blocked while audit coverage is degraded.

### Phase 9: Multi-Channel Canary, Rollback Drills, Go/No-Go

**SLO**

- Canary desktop connect success: `>= 98.0%`.
- Canary throughput ratio vs baseline: `>= 0.95`.
- Canary fallback rate in clean networks: `< 1.0%`.
- Canary fallback rate in challenged networks: `< 3.0%`.
- Rollout pause command to effective halt: `<= 60 seconds`.
- Full rollback initiation to channel-safe state: `<= 5 minutes`.

**SLA**

- Any sustained canary breach over `15 minutes` triggers immediate pause.
- Any rollback decision after confirmed severe breach must happen within `30 minutes`.

### Phase 10: Hardening, Threat Model, Production Decision Gate

**SLO**

- Manifest resolve latency under target load: `p95 <= 250 ms`.
- Rollback drill pass rate: `100%`.
- Open critical gaps in threat model at production gate: `0`.
- Signing key rotation drill success: `100%`.

**SLA**

- Any critical unresolved threat-model gap blocks stable channel with no override.
- Any failed rotation or rollback verification must be remediated before release approval.

---

## Phase 0 Execution Package

**Objective:** Freeze decisions, benchmarking discipline, compatibility boundaries, and restricted governance before code begins.

### Exact File List

Create:

- `docs/helix/benchmarking.md`
- `docs/helix/compatibility-matrix.md`
- `docs/helix/decision-log.md`
- `docs/helix/release-gates.md`
- `docs/helix/slo-sla.md`
- `docs/testing/helix-benchmark-plan.md`
- `docs/security/helix-restricted-governance.md`

Modify:

- `docs/helix/README.md`
- `docs/plans/2026-03-31-private-rust-transport-aaa-implementation-plan.md`

### Mandatory Content Per File

`docs/helix/benchmarking.md`

- benchmark topology;
- baseline transports under comparison;
- node and region selection rules;
- connect-time, throughput, disconnect, and fallback measurement definitions;
- pass/fail thresholds.

`docs/helix/compatibility-matrix.md`

- desktop OS/version support matrix;
- node class matrix;
- rollout channel compatibility rules;
- unsupported combinations and explicit exclusions.

`docs/helix/decision-log.md`

- separate schema vs separate DB decision;
- bundled sidecar decision;
- hybrid manifest delivery decision;
- rollout channel topology decision;
- node grouping decision;
- exact approvers and approval date.

`docs/helix/release-gates.md`

- lab entry/exit gates;
- canary entry/exit gates;
- stable entry/exit gates;
- pause, revoke, rollback triggers.

`docs/helix/slo-sla.md`

- all per-phase SLO/SLA values from this execution doc;
- metric owners;
- escalation paths.

`docs/testing/helix-benchmark-plan.md`

- benchmark scenarios;
- clean-network and challenged-network definitions;
- sample sizes;
- run frequency;
- reporting format.

`docs/security/helix-restricted-governance.md`

- storage rules for restricted internals;
- access policy;
- review policy;
- incident disclosure rules.

### Phase 0 Step Order

1. Update `README.md` to align with final AAA+ bar and reference benchmark/release-gate docs.
2. Write `decision-log.md` and close every blocking architecture choice.
3. Write `slo-sla.md` and `release-gates.md`.
4. Write `benchmarking.md` and the matching benchmark-plan doc.
5. Write `compatibility-matrix.md`.
6. Write restricted governance doc last, after all public-safe language is settled.
7. Update the implementation plan with links and frozen decisions.

### Exit Criteria

- All files exist and are linked from `docs/helix/README.md`.
- All blocking decisions have named approvers.
- All SLO/SLA values have a metric owner.
- `admin` and `sre` approve the phase in writing.

### Hard Stop Conditions

- Any unresolved decision on storage, runtime packaging, or delivery model.
- Any undefined benchmark threshold for “not slower than baseline”.
- Any missing restricted-governance owner.

---

## Phase 1 Execution Package

**Objective:** Create the shared contract surface and architecture source of truth so implementation can begin without guessing.

### Exact File List

Create:

- `docs/helix/architecture.md`
- `docs/helix/contracts.md`
- `packages/helix-contract/package.json`
- `packages/helix-contract/README.md`
- `packages/helix-contract/schema/manifest.schema.json`
- `packages/helix-contract/schema/node-assignment.schema.json`
- `packages/helix-contract/schema/node-heartbeat.schema.json`
- `packages/helix-contract/schema/client-capabilities.schema.json`
- `packages/helix-contract/schema/benchmark-report.schema.json`
- `packages/helix-contract/schema/rollout-state.schema.json`
- `packages/helix-contract/examples/manifest.example.json`
- `packages/helix-contract/examples/node-assignment.example.json`
- `packages/helix-contract/examples/node-heartbeat.example.json`
- `packages/helix-contract/examples/client-capabilities.example.json`
- `packages/helix-contract/examples/benchmark-report.example.json`
- `packages/helix-contract/examples/rollout-state.example.json`
- `packages/helix-contract/scripts/validate-contracts.mjs`

Modify:

- `docs/helix/README.md`
- `docs/helix/slo-sla.md`

### Mandatory Content Per File Group

Architecture docs must define:

- component boundaries;
- trust boundaries;
- manifest flow;
- node assignment flow;
- backend mediation path;
- rollout channel ownership.

Schemas must define:

- version field;
- rollout ID linkage where relevant;
- signature metadata where relevant;
- compatibility or capability declaration where relevant;
- strict required fields and `additionalProperties` policy.

Examples must be:

- realistic;
- internally consistent;
- versioned;
- validatable by script without manual edits.

Validation script must:

- validate every example against its schema;
- exit non-zero on any failure;
- print a concise PASS/FAIL summary;
- be runnable from repo root.

### Phase 1 Step Order

1. Write `architecture.md` first.
2. Write `contracts.md` second, derived from the architecture.
3. Create schemas in this order:
   - `manifest`
   - `node-assignment`
   - `node-heartbeat`
   - `client-capabilities`
   - `benchmark-report`
   - `rollout-state`
4. Create matching example fixtures.
5. Implement `validate-contracts.mjs`.
6. Run validation and fix all drift.
7. Update `README.md` and `slo-sla.md` with the contract package reference.

### Required Commands

Run from repo root:

```bash
node packages/helix-contract/scripts/validate-contracts.mjs
```

Expected result:

- All contract fixtures print `PASS`.
- Exit code `0`.

### Exit Criteria

- Every listed file exists.
- Validation passes for `100%` of fixtures.
- Contract versioning rules are documented.
- `admin` signs off on business-surface semantics.
- `sre` signs off on trust-boundary and signature-field semantics.

### Hard Stop Conditions

- Any contract field remains semantically undefined.
- Any example fixture requires undocumented assumptions.
- Any schema allows unbounded payload ambiguity.
- Any contract direction that hard-codes the transport into a single non-adaptable runtime behavior without a profile-evolution path.

---

## Immediate Start Checklist

Use this order on day one:

1. Complete `Phase 0` file creation and sign-off.
2. Create `packages/helix-contract/` skeleton immediately after `Phase 0` approval.
3. Finish `Phase 1` validation script before opening any adapter or backend PR.
4. Open `Phase 2` only after both `admin` and `sre` confirm `Phase 1` is closed.

---

## Final Rule

If there is a conflict between speed and transport-quality evidence, evidence wins.

This project is allowed to move deliberately. It is not allowed to move blindly.
