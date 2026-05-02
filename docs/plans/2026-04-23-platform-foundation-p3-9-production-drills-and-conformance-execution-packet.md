# CyberVPN Platform Foundation P3.9 Production Drills And Conformance Execution Packet

**Date:** 2026-04-23  
**Status:** implementation in progress; repo foundation slice complete, live production drill evidence pending  
**Packet:** `P3.9`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `backend-platform`, `data-platform`, `growth-platform`, `fleet-platform`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.9` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../testing/platform-foundation-conformance-scorecard.md](../testing/platform-foundation-conformance-scorecard.md)
- [../evidence/platform-foundation/platform-foundation-phase-evidence-template.md](../evidence/platform-foundation/platform-foundation-phase-evidence-template.md)
- [../testing/platform-foundation-production-drills-and-conformance-spec.md](../testing/platform-foundation-production-drills-and-conformance-spec.md)
- [2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md](2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md)

`P3.9` exists to freeze the final production drill bundle and Gate `D` assembly contract
for CyberVPN:

- `OpenBao`
- `NATS`
- `CloudNativePG`
- `GitOps / Flux recovery`
- `PostHog`
- `Node Fleet Controller / fleet reprovisioning`

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because no live
  production drills, no final Gate `D` evidence pack, and no production sign-off evidence
  exist in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is real production drill execution, scorecard completion, and
  final `Gate D` sign-off.

---

## 2. Current Baseline

Before this packet:

- `P1.8` froze the first operator-facing non-prod control-plane recovery bundle;
- `P2.4` froze the workload-cluster data-protection contract around `CloudNativePG`,
  `Barman Cloud Plugin`, and `Velero`;
- `P3.5` froze guarded failover policy semantics for the fleet controller;
- `P3.6` and `P3.7` froze the authoritative `PostHog` bridge and dashboard contracts;
- `P3.8` froze the production control-plane cutover contract for the first workload set.

Observed strengths:

- the canonical scorecard and gate evidence template already exist;
- the repo now contains frozen contracts for every major production domain that `P3.9`
  must validate;
- the remaining gap is not design ambiguity, but drill bundling and final evidence shape.

Observed implementation risks:

- `Gate D` could devolve into ad hoc prose without a frozen drill bundle and scorecard
  assembly surface;
- later live drills could execute in inconsistent order or attach mismatched evidence;
- different teams could treat partial drill success as phase closure unless the final
  evidence shape is frozen now.

---

## 3. Canonical Decisions For P3.9

`P3.9` fixes the following decisions:

1. `Gate D` evidence must be assembled from one canonical drill bundle and one canonical
   scorecard snapshot.
2. The mandatory production drill domains are:
   - `OpenBao`
   - `NATS`
   - `CloudNativePG`
   - `GitOps / Flux recovery`
   - `PostHog`
   - `Node Fleet Controller / fleet reprovisioning`
3. The final production drill order is frozen and may not be improvised per operator.
4. Every scorecard row used for `Gate D` must link to concrete drill or validation
   evidence.
5. No screenshot-only or verbal-only proof may substitute for production conformance
   evidence.

---

## 4. Scope

In scope for `P3.9`:

- add a canonical helper under [infra/scripts/production_conformance_bundle.py](../../infra/scripts/production_conformance_bundle.py);
- add unit coverage for the helper;
- add a canonical production drill and conformance spec under
  [../testing/platform-foundation-production-drills-and-conformance-spec.md](../testing/platform-foundation-production-drills-and-conformance-spec.md);
- render one operator-facing production conformance bundle containing:
  - drill order
  - domain drill briefs
  - Gate `D` scorecard snapshot template
  - Gate `D` evidence outline
  - drill-to-criteria mapping
- update operator docs so the helper is discoverable from `infra/README.md`;
- record packet evidence and formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live production drill execution;
- live `Gate D` evidence pack completion;
- human sign-off for `Gate D`;
- removal of earlier `EX-03x` residuals through real runtime proof.

---

## 5. Official Constraints

The execution of `P3.9` follows current primary-source guidance:

- OpenBao raft operations remain the canonical snapshot save and restore path for integrated
  storage;
- NATS disaster recovery is based on account backup, restore, and JetStream recovery
  procedures;
- CloudNativePG production recovery is based on recovery bootstrap and PITR-capable backup
  material;
- Flux reconciliation recovery and suspension are explicit control-plane operations, not
  hidden controller behavior.

Primary sources:

- OpenBao operator raft:
  https://openbao.org/docs/next/commands/operator/raft/
- NATS disaster recovery:
  https://docs.nats.io/running-a-nats-service/nats_admin/jetstream_admin/disaster_recovery
- CloudNativePG recovery:
  https://cloudnative-pg.io/docs/1.29/recovery
- CloudNativePG backup:
  https://cloudnative-pg.io/docs/1.29/backup
- Flux suspend kustomization:
  https://fluxcd.io/flux/cmd/flux_suspend_kustomization/
- Flux Kustomizations:
  https://fluxcd.io/flux/components/kustomize/kustomizations/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P3.9`:

### 6.1 Helper And Tests

- [infra/scripts/production_conformance_bundle.py](../../infra/scripts/production_conformance_bundle.py)
- [infra/tests/test_production_conformance_bundle.py](../../infra/tests/test_production_conformance_bundle.py)

### 6.2 Canonical Spec

- [../testing/platform-foundation-production-drills-and-conformance-spec.md](../testing/platform-foundation-production-drills-and-conformance-spec.md)

### 6.3 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.4 Packet Evidence

- [../evidence/platform-foundation/2026-04-23/p3-9-production-drills-and-conformance/evidence-pack.md](../evidence/platform-foundation/2026-04-23/p3-9-production-drills-and-conformance/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T3.9.1` Freeze The Final Production Drill Bundle

**Goal:** stop final production conformance from relying on ad hoc drill order or missing
domain ownership.

Deliverables:

- one canonical production drill bundle
- one canonical drill order
- one domain-to-criteria mapping surface

Acceptance criteria:

- every required production drill domain is present;
- the run order is explicit;
- every domain maps to the conformance criteria it is expected to prove.

### 7.2 `T3.9.2` Freeze Gate D Scorecard And Evidence Assembly

**Goal:** make final conformance evidence reproducible and comparable across reviewers.

Deliverables:

- Gate `D` scorecard snapshot template
- Gate `D` evidence outline
- explicit required evidence classes

Acceptance criteria:

- the final gate evidence shape is frozen in one place;
- scorecard rows are not left to operator invention;
- partial drill success cannot be silently presented as final conformance.

### 7.3 `T3.9.3` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live production conformance evidence.

Deliverables:

- helper unit tests
- local render smoke
- local validation command
- packet evidence pack
- formal carry-forward residual for missing live production drill execution and sign-off

Acceptance criteria:

- repository slice is locally validated;
- live closure requirements are explicit;
- no one can honestly claim `Gate D` passed from repo-only work.

---

## 8. State-Boundary Rules

`P3.9` must keep the following invariants:

1. the conformance scorecard remains authoritative for scoring;
2. the gate evidence template remains authoritative for evidence-pack structure;
3. no drill domain may be omitted from the final production gate bundle without an explicit
   superseding architecture decision;
4. `P3.9` must not claim any live production conformance success from repository-only work.

---

## 9. Exit Conditions

`P3.9` may move from repo-slice complete to packet complete only when:

- all mandatory production drill domains have real evidence attached;
- the final Gate `D` scorecard snapshot is fully populated with evidence-backed scores;
- the final Gate `D` evidence pack is assembled and signed off;
- `EX-038` is removed from the temporary exceptions register.
