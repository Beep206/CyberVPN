# CyberVPN Platform Foundation Phase Gate Evidence Template

**Date:** 2026-04-22  
**Status:** canonical template  
**Purpose:** define the required evidence pack shape for `Gate A` through `Gate D`, so no phase can claim closure through ad-hoc prose or undocumented operator judgment.

---

## 1. Gate Role

This template is the canonical evidence shape for platform-foundation gate closure.

It is the evidence companion to:

- [../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md](../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [../../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md](../../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [../../plans/2026-04-21-platform-foundation-target-state-architecture.md](../../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [../../plans/2026-04-21-platform-foundation-temporary-exceptions-register.md](../../plans/2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../../testing/platform-foundation-conformance-scorecard.md](../../testing/platform-foundation-conformance-scorecard.md)

Every gate-closure claim must use this template or a document that preserves the same sections and evidence classes.

Recommended archive location:

```text
docs/evidence/platform-foundation/<YYYY-MM-DD>/gate-<gate-id>/
```

---

## 2. Evidence Pack Header

Copy this header into each concrete gate pack:

```md
# CyberVPN Platform Foundation Gate <A|B|C|D> Evidence Pack

**Date:** YYYY-MM-DD
**Status:** draft | in review | approved | blocked
**Gate:** Gate <A|B|C|D>
**Phase:** P0 | P1 | P2 | P3
**Closure window:** YYYY-MM-DD to YYYY-MM-DD
**Primary owners:** <owner lanes>
**Supporting owners:** <owner lanes>
**Purpose:** prove the minimum evidence required to declare Gate <X> passed.
```

Mandatory front-matter fields inside the gate pack:

| Field | Required content |
|---|---|
| `gate_result` | `passed` or `blocked`; never implied |
| `blocking_exceptions` | linked `EX-*` ids from the temporary exceptions register |
| `non_blocking_residuals` | linked residuals that do not block the gate |
| `scorecard_snapshot_date` | date of the attached conformance scorecard assessment |
| `evidence_archive_location` | exact path or artifact bundle location |
| `sign_off_status` | named approvers and current review state |

---

## 3. Gate Catalog

| Gate | Phase | What it proves | Minimum closure posture |
|---|---|---|---|
| `Gate A` | `P0` | contracts, taxonomy, naming, privacy, fleet model, inventory, exceptions, and scoring model are frozen | document and approval based |
| `Gate B` | `P1` | non-prod control-plane foundations exist and can be operated safely | non-prod readiness evidence |
| `Gate C` | `P2` | non-prod workload substrate, GitOps, secret delivery, event path, and observability work end to end | non-prod readiness evidence plus partial conformance |
| `Gate D` | `P3` | external fleet automation, product intelligence, drills, and full target-state conformance are proven | production-conformance evidence |

Important distinction:

- `Gate B` and `Gate C` may close with verified non-prod readiness for in-scope systems.
- `Gate D` cannot close without production-conformance evidence against the canonical scorecard.

---

## 4. Common Mandatory Evidence Classes

Every gate pack must contain all applicable evidence classes below.

| Evidence class | Required shape |
|---|---|
| automated validation | command transcript, CI link, or generated report with date and result |
| configuration evidence | committed manifests, Terraform/OpenTofu plan artifacts, chart revisions, or config exports |
| drill evidence | run transcript, outcome summary, residuals, and linked runbook |
| governance evidence | sign-off block, owner table, or approved policy document |
| boundary evidence | proof that source-of-truth boundaries were preserved and no unofficial path was introduced |
| exception evidence | exact `EX-*` ids, allowed scope, and removal phase if any exception remains |

Screenshot-only proof is not sufficient for control-plane, eventing, secrets, or DR claims.

---

## 5. Gate-Specific Minimum Evidence

### 5.1 Gate A Minimum Evidence

`Gate A` proves that `Phase 0` is frozen and reviewable.

Required linked artifacts:

- [../../plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md](../../plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [../../api/platform-foundation-event-taxonomy.md](../../api/platform-foundation-event-taxonomy.md)
- [../../api/platform-foundation-consumer-contract.md](../../api/platform-foundation-consumer-contract.md)
- [../../api/platform-foundation-outbox-contract.md](../../api/platform-foundation-outbox-contract.md)
- [../../security/platform-foundation-openbao-and-pki-registry.md](../../security/platform-foundation-openbao-and-pki-registry.md)
- [../../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md](../../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
- [../../growth-platform/posthog-feature-flag-governance.md](../../growth-platform/posthog-feature-flag-governance.md)
- [../../api/node-fleet-controller-domain-model.md](../../api/node-fleet-controller-domain-model.md)
- [../../api/node-fleet-controller-operator-command-model.md](../../api/node-fleet-controller-operator-command-model.md)
- [../../runbooks/platform-foundation-node-lifecycle-state-machine.md](../../runbooks/platform-foundation-node-lifecycle-state-machine.md)
- [../../plans/2026-04-21-platform-foundation-monorepo-inventory.md](../../plans/2026-04-21-platform-foundation-monorepo-inventory.md)
- [../../plans/2026-04-21-platform-foundation-temporary-exceptions-register.md](../../plans/2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [platform-foundation-phase-evidence-template.md](platform-foundation-phase-evidence-template.md)
- [../../testing/platform-foundation-conformance-scorecard.md](../../testing/platform-foundation-conformance-scorecard.md)

Required proof:

- all `T0.1` through `T0.8` artifacts exist in git;
- owner lanes and sign-off lanes are named;
- every temporary exception has a removal phase;
- the scorecard exists and is linked from the canonical architecture and roadmap.

### 5.2 Gate B Minimum Evidence

`Gate B` proves that non-prod control-plane foundations exist and can be operated safely.

Mandatory scope:

- `OpenBao non-prod` foundation;
- `NATS non-prod` foundation;
- `PostHog non-prod` foundation;
- `nonprod-mgmt` cluster;
- `Flux` bootstrap baseline;
- initial backup and restore smoke validation for foundational systems.

Required proof classes:

- topology and placement evidence for foundational services;
- auth, TLS, and separation evidence;
- bootstrap transcripts or CI evidence for non-prod management plane;
- initial operator runbooks;
- non-prod backup and restore smoke results;
- linked blocking exceptions if any legacy path remains temporarily tolerated.

### 5.3 Gate C Minimum Evidence

`Gate C` proves that non-prod workload delivery and platform substrate work end to end.

Mandatory scope:

- workload clusters on the new substrate;
- `OpenBao -> VSO -> Kubernetes Secret` delivery path;
- transactional outbox to `NATS` event path for in-scope business flows;
- `Alloy` as the canonical collector across Kubernetes and external node paths in the migrated scope;
- GitOps promotion and rollback baseline;
- realtime dashboard or notification path through durable eventing rather than primary polling.

Required proof classes:

- Helm/Flux reconciliation evidence;
- workload secret delivery validation;
- outbox publish, consumer, and replay validation;
- non-prod latency measurements for the critical event path;
- collector migration proof showing migrated scope and remaining exceptions;
- non-prod drill evidence for rollback, replay, and service recovery.

### 5.4 Gate D Minimum Evidence

`Gate D` proves production conformance for the target-state platform.

Mandatory scope:

- `Node Fleet Controller` owns controller-driven `node-add`, `node-replace`, and quarantine paths;
- guarded failover works through policy controls, not ad-hoc automation;
- `PostHog` receives authoritative commercial events and enforces privacy boundaries;
- backup and restore drills cover the canonical target-state systems;
- the production conformance scorecard reaches the required thresholds with no blocking gaps.

Required proof classes:

- controller workflow transcripts and operation-run records;
- traffic eligibility and quarantine evidence;
- failover drill evidence with budget/rate-limit/cooldown controls visible;
- PostHog server-side bridge and privacy-validation evidence;
- production-grade drill bundle for `OpenBao`, `NATS`, `PostgreSQL`, GitOps state, `PostHog`, and fleet reprovisioning;
- final scorecard snapshot and explicit `Gate D passed` statement.

---

## 6. Mandatory Proof Shape By Domain

The following proof shapes are mandatory when the named domain becomes in scope for a gate.

### 6.1 OpenBao

| Proof area | Minimum expected evidence |
|---|---|
| topology and separation | committed infra definition or inventory proving `prod` and `nonprod` separation |
| auth model | auth mounts, namespace names, and role mappings aligned to the frozen registry |
| trust and PKI | issuance or validation transcript for in-scope `pki-k8s` or `pki-infra` paths |
| backup and restore | snapshot procedure, restore transcript, and residuals |
| boundary protection | proof that runtime workloads do not fall back to host-local `.env` or ad-hoc secret copies inside the migrated scope |

### 6.2 NATS JetStream

| Proof area | Minimum expected evidence |
|---|---|
| cluster baseline | topology, TLS, account separation, and placement evidence |
| governance | declarative stream and consumer definitions in git |
| publish boundary | proof that business-critical publication uses transactional outbox |
| delivery semantics | idempotent durable consumer evidence, replay procedure, and lag monitoring |
| failure handling | node-loss or outage drill evidence showing backlog or replay, not silent loss |

### 6.3 GitOps And Flux

| Proof area | Minimum expected evidence |
|---|---|
| bootstrap | management-cluster bootstrap transcript and Flux installation evidence |
| desired state | git commit or PR evidence for the desired-state change |
| reconciliation | HelmRelease/Kustomization outcome or drift reconciliation evidence |
| rollback | rollback or failed-promotion recovery drill |
| boundary protection | proof that production changes do not depend on manual host mutation inside the migrated scope |

### 6.4 Alloy Migration

| Proof area | Minimum expected evidence |
|---|---|
| inventory coverage | explicit list of migrated and still-excepted collector paths |
| Kubernetes collection | `Alloy DaemonSet` evidence for node and pod collection in migrated clusters |
| gateway role | `Alloy Deployment` or equivalent OTLP gateway evidence for app traces and telemetry |
| external nodes | proof that migrated VPN or edge nodes send telemetry through the target collector family |
| retirement posture | proof that `promtail` and standalone collector remnants are either retired or recorded as temporary exceptions |

### 6.5 Node Fleet Controller

| Proof area | Minimum expected evidence |
|---|---|
| durable control state | control DB entities and operation-run records for the exercised workflow |
| workflow execution | controller-driven provisioning, replacement, drain, or quarantine evidence |
| infra execution boundary | OpenTofu plan/apply artifacts tied to controller requests |
| bootstrap and identity | wrapped bootstrap evidence and steady-state node identity evidence |
| traffic eligibility | synthetic, health, enrollment, and runtime-adapter gate proof before traffic enablement |

### 6.6 PostHog

| Proof area | Minimum expected evidence |
|---|---|
| placement and access | VM deployment, DNS/TLS, and access-control evidence |
| privacy baseline | blocked-property validation and proof that prohibited VPN activity telemetry is absent |
| event source model | clear separation between `frontend_sdk`, `server_side`, and `nats_bridge` sources |
| commercial events | authoritative or server-side capture evidence for critical product events |
| flag governance | deterministic fallback tests and proof that infra or security kill switches do not depend on PostHog flags |

### 6.7 Backup And Recovery

| Proof area | Minimum expected evidence |
|---|---|
| OpenBao | raft snapshot save and restore transcript |
| NATS | replay, rebuild, or outage recovery transcript |
| PostgreSQL | PITR or restore transcript for the in-scope platform database |
| GitOps and cluster state | git recovery, etcd, or bootstrap recovery evidence as applicable |
| PostHog | backup and restore transcript or validated restore rehearsal |
| fleet reprovisioning | proof that an external node can be recreated without manual secret copy |

---

## 7. Non-Prod Readiness Versus Production Conformance

Use the following interpretation across all gate packs:

| Readiness level | Meaning |
|---|---|
| documented | the contract exists but runtime behavior is not yet proven |
| non-prod ready | behavior is implemented and validated in non-prod or controlled lab scope |
| production conformant | behavior is proven under the production target-state criteria with drills, rollback posture, and sign-off |

Rules:

- `Gate B` and `Gate C` may close on `non-prod ready` evidence for in-scope domains.
- `Gate D` requires `production conformant` evidence for all in-scope target-state domains.
- a temporary exception may explain a non-gating gap in `Gate B` or `Gate C`, but it must never silently replace the target path.
- no exception can override a `Gate D` production-conformance requirement unless the architecture itself is formally superseded.

---

## 8. Residuals, Exceptions, And Sign-Off Template

Every concrete gate pack must include these tables.

### 8.1 Residuals

| Residual id | Description | Blocking | Owner | Target removal phase | Linked evidence |
|---|---|---|---|---|---|
| `RES-*` | fill in | `yes` or `no` | fill in | fill in | fill in |

### 8.2 Linked Exceptions

| Exception id | Scope | Allowed through | Blocks gate | Removal verification |
|---|---|---|---|---|
| `EX-*` | fill in | `P1`, `P2`, or `P3` | `yes` or `no` | fill in |

### 8.3 Sign-Off

| Owner lane | Required for this gate | Name | Status | Notes |
|---|---|---|---|---|
| platform architecture | yes | fill in | pending | fill in |
| SRE or program | yes | fill in | pending | fill in |
| backend platform | if applicable | fill in | pending | fill in |
| infra or platform | if applicable | fill in | pending | fill in |
| security | if applicable | fill in | pending | fill in |
| product or growth | if applicable | fill in | pending | fill in |

No gate pack is complete until it ends with an explicit closure statement:

```text
Gate <A|B|C|D> is PASSED.
```

or

```text
Gate <A|B|C|D> is BLOCKED by <residual or exception ids>.
```
