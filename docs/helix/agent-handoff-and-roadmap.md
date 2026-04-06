# Helix Agent Handoff And Roadmap

> Detailed handoff and execution roadmap for CyberVPN `Helix`.
> Audience: project owner, future AI agents, and human engineers continuing the implementation.
> This document is the practical continuation guide, not a marketing summary.

## 1. Purpose

This document answers four questions:

1. What `Helix` is and what has already been built.
2. Where the project currently stands.
3. What must be done before `Internal Beta`.
4. What must still be done after `Internal Beta` to reach `Release`.

Use this document when:

- a new AI agent takes over the project;
- the team needs a concrete next-step list;
- we need one place to understand current readiness, blockers, and the remaining path.

---

## 2. Snapshot Of Current State

### 2.1 Short Summary

`Helix` is no longer a concept or a control-plane-only experiment.

It already includes:

- a real Rust data-plane runtime;
- desktop-side local ingress and supervision;
- node-side relay/runtime process;
- control-plane manifest and rollout system;
- backend facade;
- worker-driven operational loops;
- diagnostics, benchmarking, evidence collection, and beta-hardening scaffolding.

The current phase is:

- no longer "build the first protocol";
- not yet "ship to everyone";
- currently "production hardening, live evidence, and controlled rollout maturity".

### 2.2 Implementation Snapshot

Base implementation checkpoint before this handoff document:

- branch: `codex/helix-internal-beta`
- baseline commit: `9e575856`
- message: `Add Helix transport stack and beta hardening`

Future agents should treat this as the known-good starting point for the next cycle.

### 2.3 Readiness Estimate

These are engineering estimates, not release promises.

| Area | Current Status | Rough Readiness |
| --- | --- | --- |
| Data-plane core | Strong | `85-90%` |
| Desktop-first runtime | Strong | `80-85%` |
| Control-plane rollout logic | Strong | `80-85%` |
| Diagnostics and evidence tooling | Strong | `75-80%` |
| Internal beta readiness | In progress | `70-80%` |
| Production readiness | In progress | `60-70%` |

### 2.4 Current Reality

What this means in practice:

- `Helix` is already a real system.
- The next work is mostly about hardening, evidence, and operational confidence.
- The remaining risk is less about missing architecture and more about behavior under live conditions.

---

## 3. What Helix Is

## 3.1 Product Role

`Helix` is CyberVPN's desktop-first premium transport platform intended to become a first-class alternative to current baseline transports.

It must be:

- stable;
- adaptable;
- measurable;
- recoverable;
- operable under controlled rollout;
- capable of fast profile/policy evolution without forcing repo-wide rewrites.

## 3.2 System Components

### Shared contracts

- [packages/helix-contract/README.md](/C:/project/CyberVPN/packages/helix-contract/README.md)
- JSON schemas and examples for manifests, assignments, benchmark reports, capabilities, heartbeats, rollout state, and transport profiles.

### Data-plane runtime

- [packages/helix-runtime/src/lib.rs](/C:/project/CyberVPN/packages/helix-runtime/src/lib.rs)
- [packages/helix-runtime/src/client.rs](/C:/project/CyberVPN/packages/helix-runtime/src/client.rs)
- [packages/helix-runtime/src/server.rs](/C:/project/CyberVPN/packages/helix-runtime/src/server.rs)
- Multiplexed secure session runtime with fairness and continuity logic.

### Control-plane adapter

- [services/helix-adapter/src/lib.rs](/C:/project/CyberVPN/services/helix-adapter/src/lib.rs)
- Owns manifests, assignments, rollout policy, profile scoring, suppression, actuation state, and canary evidence.

### Node daemon

- [services/helix-node/src/lib.rs](/C:/project/CyberVPN/services/helix-node/src/lib.rs)
- Pulls assignments, applies bundles, health-gates them, and rolls back to last-known-good.

### Backend facade

- [backend/src/presentation/api/v1/helix/routes.py](/C:/project/CyberVPN/backend/src/presentation/api/v1/helix/routes.py)
- Public and admin-facing Helix facade for desktop and operations.

### Desktop runtime

- [apps/desktop-client/src-tauri/src/engine/helix/mod.rs](/C:/project/CyberVPN/apps/desktop-client/src-tauri/src/engine/helix/mod.rs)
- [apps/desktop-client/src/pages/Settings/index.tsx](/C:/project/CyberVPN/apps/desktop-client/src/pages/Settings/index.tsx)
- Includes runtime prep, sidecar, failover, recovery benches, diagnostics, support bundle export, and perf lab UI.

### Worker operational loops

- [services/task-worker/src/tasks/monitoring/helix_health.py](/C:/project/CyberVPN/services/task-worker/src/tasks/monitoring/helix_health.py)
- [services/task-worker/src/tasks/monitoring/helix_actuations.py](/C:/project/CyberVPN/services/task-worker/src/tasks/monitoring/helix_actuations.py)
- [services/task-worker/src/tasks/monitoring/helix_canary_gates.py](/C:/project/CyberVPN/services/task-worker/src/tasks/monitoring/helix_canary_gates.py)
- [services/task-worker/src/tasks/monitoring/helix_canary_control.py](/C:/project/CyberVPN/services/task-worker/src/tasks/monitoring/helix_canary_control.py)

### Infra and observability

- [infra/docker-compose.yml](/C:/project/CyberVPN/infra/docker-compose.yml)
- [infra/prometheus/rules/helix_alerts.yml](/C:/project/CyberVPN/infra/prometheus/rules/helix_alerts.yml)
- [infra/grafana/dashboards/helix-dashboard.json](/C:/project/CyberVPN/infra/grafana/dashboards/helix-dashboard.json)

---

## 4. What Is Already Implemented

## 4.1 Protocol Core

Already implemented:

- secure session setup;
- multiplexed stream model;
- flow control and stream scheduling upgrades;
- interactive-vs-bulk fairness improvements;
- backpressure behavior;
- queue pressure telemetry;
- same-session continuity and resume behavior;
- route scoring;
- continuity-aware failover;
- warm standby logic;
- route quarantine, re-admit, and hysteresis behavior.

## 4.2 Desktop

Already implemented:

- Helix runtime inside desktop client;
- local proxy ingress path;
- Helix diagnostics panel;
- support bundle export;
- recovery drill;
- target matrix comparison;
- Helix benchmark and telemetry collection;
- typed runtime event reporting;
- Helix policy visibility in settings.

## 4.3 Control Plane

Already implemented:

- manifest resolution;
- node assignment generation;
- profile compatibility selection;
- profile scoring;
- suppression windows;
- actuation states;
- semi-automatic control-plane reactions;
- canary evidence snapshot generation;
- backend admin surface for canary evidence.

## 4.4 Worker And Ops Loop

Already implemented:

- health monitoring;
- rollout audits;
- actuation lifecycle alerts;
- canary gate decisions;
- semi-automatic canary control suggestions and follow-up actions.

## 4.5 Beta-Hardening Foundation

Already implemented:

- rollback verification script;
- internal beta evidence pack collector;
- deterministic canary-evidence budget test;
- load-test scaffolding;
- release gates and internal beta checklist;
- threat model and incident/rotation docs.

---

## 5. Where We Stopped

The project is currently stopped at this boundary:

- the `Helix` platform is implemented strongly enough to justify `Internal Beta` preparation;
- the next major work is not new architecture, but evidence-driven hardening and rollout validation.

The immediate strategic focus is:

1. finish the remaining `Internal Beta` blockers;
2. open a disciplined internal beta window;
3. collect real evidence;
4. continue hardening toward `Release`.

---

## 6. Source Of Truth Documents

Future agents should read these first:

1. [docs/helix/README.md](/C:/project/CyberVPN/docs/helix/README.md)
2. [docs/helix/architecture.md](/C:/project/CyberVPN/docs/helix/architecture.md)
3. [docs/helix/contracts.md](/C:/project/CyberVPN/docs/helix/contracts.md)
4. [docs/helix/release-gates.md](/C:/project/CyberVPN/docs/helix/release-gates.md)
5. [docs/helix/internal-beta-checklist.md](/C:/project/CyberVPN/docs/helix/internal-beta-checklist.md)
6. [docs/testing/helix-internal-beta-evidence-pack.md](/C:/project/CyberVPN/docs/testing/helix-internal-beta-evidence-pack.md)
7. [docs/security/helix-threat-model.md](/C:/project/CyberVPN/docs/security/helix-threat-model.md)
8. [docs/testing/helix-benchmark-plan.md](/C:/project/CyberVPN/docs/testing/helix-benchmark-plan.md)

This document is the practical execution bridge across those source-of-truth files.

---

## 7. Remaining Work Before Internal Beta

These are the active remaining blocks before we can confidently call the project `Internal Beta` ready.

## 7.1 Block A: Live Evidence On Real Networks

Why it matters:

- current evidence is strong but still too lab-heavy;
- `Internal Beta` must be justified by live behavior, not just local and synthetic runs.

What remains:

- run long desktop sessions on real networks;
- run live target matrix against realistic targets;
- collect multiple support bundles from real usage;
- verify actual canary evidence under live event ingest and real admin access.

### Required Outputs

- at least one live benchmark report;
- at least one live recovery report;
- one live target matrix report;
- one live formal canary evidence snapshot;
- one desktop support bundle from the candidate build.

## 7.2 Block B: Rollback And Failure Drills Under More Realistic Conditions

Why it matters:

- we already have rollback verification, but we still need stronger live confidence;
- release gates require proof, not only scripts.

What remains:

- destructive rollback drill with live stack;
- forced failure drill for node runtime;
- desktop fallback drill from Helix to stable core;
- pause-channel behavior verification under active rollout state.

### Required Outputs

- destructive drill log;
- rollback-verification pass output;
- evidence that desktop fallback still works cleanly;
- operator note that last-known-good restore remains trustworthy.

## 7.3 Block C: Reconnect Continuity Hardening In Worse Real Conditions

Why it matters:

- same-session continuity exists;
- live route churn, reconnect storms, and user-hostile network changes are still risk areas.

What remains:

- more evidence under real reconnect churn;
- validate continuity behavior during route instability;
- confirm continuity metrics match actual user behavior;
- verify no silent data-path corruption after resume/failover.

### Required Outputs

- recovery reports from hostile conditions;
- support bundle with continuity telemetry;
- updated continuity notes if edge cases are found.

## 7.4 Block D: Internal Beta Operational Pack

Why it matters:

- internal beta must be runnable by the team, not only by the original implementing agent.

What remains:

- confirm all runbooks are current;
- confirm the evidence pack flow is reproducible;
- confirm admin, ops, and sre can each understand the outputs;
- confirm beta gate language is final enough for execution.

### Required Outputs

- one assembled internal beta evidence pack;
- final reviewed checklist for the candidate build;
- named rollout owners or temporary role mapping for the beta window.

---

## 8. Internal Beta Plan

This is the recommended execution sequence to open `Internal Beta`.

## 8.1 Beta Phase 0: Candidate Freeze

Goal:

- freeze the candidate build and stop uncontrolled feature drift.

Actions:

1. keep the current branch as the candidate base or cut a dedicated beta-prep branch;
2. avoid large new feature work unrelated to evidence or hardening;
3. restrict changes to:
   - bug fixes;
   - evidence collection;
   - rollout hardening;
   - diagnostics;
   - rollback safety.

Exit criteria:

- candidate branch builds cleanly;
- no known `P0/P1` issue in startup, fallback, manifest resolution, or rollback path.

## 8.2 Beta Phase 1: Evidence Collection

Goal:

- collect the minimum evidence required by beta gates.

Actions:

1. run deterministic backend canary-evidence budget test;
2. run rollback verification;
3. run worker Helix monitoring tests;
4. run at least one desktop benchmark scenario;
5. run at least one recovery drill;
6. run at least one target matrix scenario;
7. export one desktop support bundle;
8. collect formal canary evidence snapshot;
9. assemble the internal beta evidence pack.

Suggested command set:

```bash
pytest backend/tests/load/test_helix_canary_evidence_budget.py -q
bash infra/tests/verify_helix_rollback.sh
python -m pytest services/task-worker/tests/unit/tasks/test_helix_canary_gates.py services/task-worker/tests/unit/tasks/test_helix_canary_control.py services/task-worker/tests/unit/tasks/test_helix_actuations.py -q --no-cov
bash infra/tests/collect_helix_internal_beta_evidence.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_lab_bench.ps1 -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_recovery_lab.ps1 -Mode reconnect -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_target_matrix.ps1 -Preset mixed -UseSyntheticLabTarget
```

Exit criteria:

- evidence pack exists and is readable;
- current formal canary decision is not `no-go`;
- no unresolved critical actuation state requiring a held channel.

## 8.3 Beta Phase 2: Live Beta-Like Validation

Goal:

- prove that the candidate behaves acceptably outside pure lab mode.

Actions:

1. run live backend load scenario:
   - [backend/tests/load/test_helix_load.py](/C:/project/CyberVPN/backend/tests/load/test_helix_load.py)
2. run destructive rollback drill if the environment permits it;
3. capture live canary evidence snapshot through admin surface;
4. collect at least one beta-like desktop support bundle from real use;
5. confirm dashboards and alerts reflect the candidate correctly.

Exit criteria:

- live admin evidence remains readable under load;
- rollback behavior remains acceptable;
- metrics remain interpretable and not obviously degraded;
- the team can explain current canary posture and next operational action.

## 8.4 Beta Phase 3: Internal Beta Go/No-Go

Goal:

- make the actual `Internal Beta` decision.

Required decision inputs:

- evidence pack;
- latest rollback verification;
- latest recovery reports;
- latest target matrix;
- latest canary evidence snapshot;
- one desktop support bundle;
- active worker alert state.

Go if:

- no current `no-go` canary state;
- no unresolved critical rollback concern;
- no unacceptable fallback spike;
- no obvious admin or ops blind spot;
- desktop runtime is stable enough for controlled internal users.

No-go if:

- control-plane reaction remains unstable;
- rollback confidence is still weak;
- live canary evidence becomes unreadable under load;
- continuity or failover behavior shows user-visible instability with no clear mitigation.

---

## 9. Work After Internal Beta, Before Release

Passing `Internal Beta` does not mean release-ready. It means the project is ready for a disciplined live learning phase.

## 9.1 Release Block 1: Wider Canary Evidence

Goal:

- accumulate real usage evidence across a broader but still controlled set of users and nodes.

Actions:

1. expand from internal cohort to limited canary cohort;
2. track connect success, fallback rate, continuity success, cross-route recovery, throughput ratio, and queue pressure trends;
3. validate profile and actuation decisions against real behavior;
4. verify suppressed profile handling and profile rotation logic under real rollout pressure.

Required outputs:

- one full canary observation window;
- trend snapshots over time, not only point-in-time reports;
- incident notes for any unexpected transport behavior.

## 9.2 Release Block 2: Production Hardening

Goal:

- close operational and security maturity gaps.

Actions:

1. re-run threat review against the final rollout posture;
2. confirm secret rotation procedures;
3. confirm manifest signing operational path;
4. confirm incident runbooks are good enough for real use;
5. validate alert fatigue and escalation quality;
6. validate admin and worker loops do not fight each other;
7. verify rollback under realistic operational stress.

Required outputs:

- updated threat model if needed;
- final runbook revisions;
- recorded successful rotation rehearsal;
- updated release-gate evidence.

## 9.3 Release Block 3: Performance And Stability Tuning Under Live Traffic

Goal:

- move from "works strongly" to "competitive with confidence".

Actions:

1. tune based on real support bundles and target matrix reports;
2. compare `Helix` against baseline transports on the same target sets;
3. reduce remaining latency tail issues;
4. reduce remaining throughput variability;
5. confirm route policy remains beneficial under real churn.

Required outputs:

- comparative trend reports;
- updated benchmark notes;
- final performance decision evidence for release.

## 9.4 Release Block 4: Release Candidate

Goal:

- produce a candidate build and rollout posture suitable for release approval.

Actions:

1. freeze release candidate;
2. require all stable-channel entry gates from [release-gates.md](/C:/project/CyberVPN/docs/helix/release-gates.md);
3. confirm no unresolved critical actuation state;
4. confirm stable promotion authority is aligned;
5. make final release go/no-go decision.

Exit criteria:

- canary evidence holds over a full window;
- rollback is trusted;
- no unresolved critical security or auth boundary concern;
- ops can run it without heroics.

---

## 10. Detailed Plan For The Next AI Agent

This section is intentionally operational. A future agent should be able to continue from here without guessing.

## 10.1 First Files To Read

In this order:

1. [docs/helix/agent-handoff-and-roadmap.md](/C:/project/CyberVPN/docs/helix/agent-handoff-and-roadmap.md)
2. [docs/helix/README.md](/C:/project/CyberVPN/docs/helix/README.md)
3. [docs/helix/internal-beta-checklist.md](/C:/project/CyberVPN/docs/helix/internal-beta-checklist.md)
4. [docs/helix/release-gates.md](/C:/project/CyberVPN/docs/helix/release-gates.md)
5. [docs/testing/helix-internal-beta-evidence-pack.md](/C:/project/CyberVPN/docs/testing/helix-internal-beta-evidence-pack.md)

Then inspect the implementation surfaces:

1. [packages/helix-runtime/src/client.rs](/C:/project/CyberVPN/packages/helix-runtime/src/client.rs)
2. [packages/helix-runtime/src/server.rs](/C:/project/CyberVPN/packages/helix-runtime/src/server.rs)
3. [services/helix-adapter/src/node_registry/service.rs](/C:/project/CyberVPN/services/helix-adapter/src/node_registry/service.rs)
4. [services/helix-adapter/src/transport_profiles/service.rs](/C:/project/CyberVPN/services/helix-adapter/src/transport_profiles/service.rs)
5. [apps/desktop-client/src-tauri/src/engine/helix/sidecar.rs](/C:/project/CyberVPN/apps/desktop-client/src-tauri/src/engine/helix/sidecar.rs)
6. [apps/desktop-client/src/components/settings/diagnostics-support-panel.tsx](/C:/project/CyberVPN/apps/desktop-client/src/components/settings/diagnostics-support-panel.tsx)

## 10.2 What The Next Agent Must Not Assume

Do not assume:

- lab success equals release readiness;
- canary evidence is complete enough without live runs;
- control-plane safety means desktop UX is fully proven;
- current continuity logic covers every hostile real network case;
- `Helix` is "done" just because the core exists.

## 10.3 What The Next Agent Should Do First

Preferred execution order:

1. verify working tree and branch state;
2. verify `Internal Beta` blockers against this document;
3. collect or improve missing evidence;
4. only after that add new hardening code if evidence exposes a real gap.

## 10.4 Immediate Next Actions

If the environment allows live work, do this:

1. run [infra/tests/collect_helix_internal_beta_evidence.sh](/C:/project/CyberVPN/infra/tests/collect_helix_internal_beta_evidence.sh)
2. run live [backend/tests/load/test_helix_load.py](/C:/project/CyberVPN/backend/tests/load/test_helix_load.py)
3. run destructive rollback drill
4. collect live canary evidence snapshot
5. collect one real desktop support bundle
6. update this roadmap document with actual findings

If the environment does not allow live work, do this:

1. improve evidence tooling;
2. improve canary visibility or diagnostics if a blind spot is found;
3. improve failure drills and scripts;
4. avoid large new protocol features unless they directly unblock beta readiness.

## 10.5 Definition Of A Good Future Agent Cycle

A good future cycle should end with all of the following:

- code or docs changed for a specific reason;
- evidence or tests collected;
- a short status update added to the roadmap or adjacent docs;
- a clear statement of what remains blocked.

The future agent should not end a cycle with only "I changed code". It should end with:

- what changed;
- why it changed;
- what evidence exists now;
- what remains before the next gate.

---

## 11. Exact Beta Checklist For A Future Agent

Before claiming `Internal Beta` readiness, the agent should explicitly confirm each line:

- [ ] `Helix` build candidate is identified
- [ ] desktop runtime builds and installs
- [ ] deterministic backend canary-evidence budget test passes
- [ ] rollback verification passes
- [ ] worker Helix monitoring tests pass
- [ ] at least one benchmark report exists
- [ ] at least one recovery report exists
- [ ] at least one target matrix report exists
- [ ] one support bundle exists
- [ ] one formal canary evidence snapshot exists
- [ ] evidence pack exists
- [ ] no current `no-go` decision
- [ ] no current critical actuation requiring held exposure
- [ ] rollback path is still trusted

---

## 12. Exact Release Checklist For A Future Agent

Before claiming release readiness, the agent should explicitly confirm each line:

- [ ] `Internal Beta` completed successfully
- [ ] canary evidence accumulated over a real window
- [ ] release gates for stable are satisfied
- [ ] live load behavior is acceptable
- [ ] rollback behavior is acceptable
- [ ] threat model is current
- [ ] secret rotation procedure is validated
- [ ] support and incident runbooks are current
- [ ] no unresolved critical security or auth boundary issue
- [ ] no unresolved critical continuity or fallback issue
- [ ] final comparative performance evidence is acceptable
- [ ] admin, ops, and sre ownership is clear

---

## 13. Recommended Next Milestone Sequence

The clean milestone order from here is:

1. `Internal Beta Prep`
2. `Internal Beta`
3. `Limited Canary`
4. `Expanded Canary`
5. `Release Candidate`
6. `Release`

The team should not skip directly from current state to broad release.

---

## 14. Final Guidance

The most important truth for the next agent is this:

`Helix` already has a strong architectural and implementation base.
The remaining work is mainly about proving, hardening, and operating it correctly.

The most valuable next agent is not the one that adds the biggest new subsystem.
It is the one that:

- closes evidence gaps;
- protects rollback confidence;
- improves live observability;
- and moves the project from "strong implementation" to "trusted deployment".
