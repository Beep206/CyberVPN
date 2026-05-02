# CyberVPN Platform Foundation Phase 0 Execution Packet

**Date:** 2026-04-21  
**Status:** Execution packet for implementation start  
**Purpose:** translate `Phase 0` from the platform foundation phased implementation plan into executable backlog tickets with clear ownership, repository touchpoints, dependencies, acceptance criteria, and evidence requirements.

---

## 1. Document Role

This document is the execution bridge between:

- the canonical platform foundation target-state architecture;
- the phased implementation plan;
- the current repository baseline;
- the first implementation wave that prepares the program for real infrastructure and code changes.

It exists so `Phase 0` can begin without teams inventing their own ticket boundaries, taxonomies, or hidden prerequisites.

This document does not reopen:

- target-state decisions;
- technology choices already fixed in the canonical documents;
- trust-boundary decisions between Kubernetes, external fleet, secrets, eventing, and analytics;
- rollout-phase ordering already fixed in the phased implementation plan.

If a proposed ticket changes any of those, the change must first be approved in the canonical documents.

Read this together with:

- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)

---

## 2. Execution Rules

Execution for `Phase 0` follows these rules:

1. `Phase 0` blocks foundation implementation that depends on unresolved naming, contract, privacy, or ownership ambiguity.
2. `Phase 0` is documentation-and-inventory heavy by design. That is not overhead; it is what prevents platform rework later.
3. Every ticket must produce one of:
   - frozen contract documentation;
   - inventory artifacts;
   - explicit register or matrix artifacts;
   - validation and evidence templates.
4. Every ticket must identify which source-of-truth boundary it protects.
5. Every ticket must identify which later packets it unlocks.
6. Inventory work must use real repository paths, not abstract statements like “audit the infra”.
7. No `Phase 1` control-plane buildout should start until the `Phase 0` blocking tickets are signed off.
8. Temporary exceptions are allowed only if they are captured in the register with an owner and removal phase.

---

## 3. Ticket Naming And Board Model

Ticket identifiers use the format:

- `T0.x` for `Phase 0`

Recommended workboards:

| Board | Scope | Primary owners |
|---|---|---|
| `B0` | platform contracts, naming, source-of-truth boundaries | platform architecture, backend platform |
| `B1` | secrets, PKI, trust-anchor, and infrastructure naming | platform architecture, infra/platform |
| `B2` | analytics, privacy, feature-flag governance | product, growth/data, security |
| `B3` | fleet model, node lifecycle, automation boundaries | platform architecture, infra/platform, transport/backend |
| `B4` | repository inventory, temporary exceptions, evidence templates | platform architecture, SRE/platform, QA/program |

Suggested backlog labels:

- `platform-foundation`
- `phase-0`
- `contracts`
- `inventory`
- `source-of-truth`
- `eventing`
- `openbao`
- `posthog`
- `fleet-controller`
- `observability`
- `blocking`

---

## 4. Sequencing Summary

| Ticket | Phase | Packet alignment | Primary board | Size | Hard blockers |
|---|---|---|---|---|---|
| `T0.1` | `Phase 0` | `P0.1` | `B0` | `S` | none |
| `T0.2` | `Phase 0` | `P0.2` | `B0` | `M` | `T0.1` |
| `T0.3` | `Phase 0` | `P0.3` | `B1` | `S` | `T0.1` |
| `T0.4` | `Phase 0` | `P0.4` | `B2` | `M` | `T0.1` |
| `T0.5` | `Phase 0` | `P0.5` | `B3` | `M` | `T0.1`, `T0.2`, `T0.3` |
| `T0.6` | `Phase 0` | `P0.6` | `B4` | `L` | `T0.1`, `T0.2`, `T0.3`, `T0.4`, `T0.5` |
| `T0.7` | `Phase 0` | `P0.8` | `B4` | `S` | `T0.6` |
| `T0.8` | `Phase 0` | `P0.7` | `B4` | `S` | `T0.6`, `T0.7` |
| `T0.9` | `Phase 0` | phase-exit sign-off | `B4` | `S` | `T0.1` through `T0.8` |

`Phase 1` work should not start before `T0.1` through `T0.5` are complete.  
`Gate A` should not be declared complete before `T0.1` through `T0.9` are complete.

---

## 5. Phase 0 Ticket Decomposition

## 5.1 `T0.1` Canonical Platform Naming And Boundary Registry Freeze

**Packet alignment:** `P0.1`  
**Primary owners:** platform architecture, backend platform  
**Supporting owners:** infra/platform, security, product

**Repository touchpoints:**

- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:1)
- Modify: [2026-04-21-platform-foundation-phased-implementation-plan.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md:1)
- Create: `docs/plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md`

**Scope:**

- freeze canonical names for:
  - environments;
  - management clusters;
  - workload clusters;
  - provider, region, country, and node-class references;
  - external control planes;
  - GitOps repos and deployment state surfaces;
  - secret, PKI, and event-domain identifiers;
  - source-of-truth boundaries between PostgreSQL, NATS, OpenBao, Node Fleet Controller DB, PostHog, and Prometheus/Grafana.

**Deliverables:**

- canonical naming registry;
- explicit boundary registry describing what each control surface may and may not own;
- reserved-name list for terms that must not be reused differently later.

**Acceptance criteria:**

- the same environment, cluster, or control-plane surface is not named differently across the architecture and phased roadmap;
- `source of truth`, `event backbone`, `product intelligence`, and `operational truth` are defined once and used consistently;
- all later `T0.x` tickets can refer to frozen names without reinterpretation.

**Evidence required:**

- signed registry document;
- architecture sign-off from platform and infra leads;
- explicit change log of terms normalized from older docs.

---

## 5.2 `T0.2` Event Taxonomy, Envelope, Stream Domain, And Consumer Contract Freeze

**Packet alignment:** `P0.2`  
**Primary owners:** platform architecture, backend platform  
**Supporting owners:** transport/backend, product/data, SRE

**Repository touchpoints:**

- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:540)
- Create: `docs/api/platform-foundation-event-taxonomy.md`
- Create: `docs/api/platform-foundation-consumer-contract.md`
- Create: `docs/api/platform-foundation-outbox-contract.md`
- Reference current code: [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)
- Reference current code: [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)

**Scope:**

- freeze canonical event families and subject patterns;
- freeze the required event envelope fields;
- freeze what counts as event vs command vs durable state;
- freeze the durable consumer contract template;
- freeze outbox publication semantics for business-critical events.

**Deliverables:**

- event taxonomy document;
- consumer contract template;
- outbox contract baseline;
- explicit rule that direct business-critical publish from request handlers is prohibited.

**Acceptance criteria:**

- billing, subscription, partner, node lifecycle, node health, and analytics events have one canonical naming pattern;
- event envelope fields align with the target-state document;
- every future durable consumer can be instantiated from the same contract template;
- current Redis/SSE behavior is clearly marked as delivery mechanics, not business source of truth.

**Evidence required:**

- event taxonomy document approved by backend and platform owners;
- consumer contract template approved by SRE/platform;
- explicit backlog note showing which existing publish paths violate the target and must be migrated in later phases.

---

## 5.3 `T0.3` OpenBao, PKI, And Trust-Naming Registry Freeze

**Packet alignment:** `P0.3`  
**Primary owners:** platform architecture, infra/platform  
**Supporting owners:** security

**Repository touchpoints:**

- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:229)
- Create: `docs/security/platform-foundation-openbao-and-pki-registry.md`
- Reference current bootstrap docs: [CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/CONTROL_PLANE_RELEASE_PROMOTION_RUNBOOK.md:1)
- Reference current secrets guidance: [docs/secret-rotation.md](/home/beep/projects/VPNBussiness/docs/secret-rotation.md:1)

**Scope:**

- freeze OpenBao cluster names, namespace names, auth mount naming, policy naming, PKI mount naming, and path conventions;
- freeze certificate trust-domain naming and environment separation rules;
- freeze which bootstrap flows are allowed to use AppRole and which are not.

**Deliverables:**

- OpenBao and PKI naming registry;
- auth-mount naming matrix per future cluster type;
- bootstrap exception matrix for external machine bootstrap.

**Acceptance criteria:**

- no later OpenBao automation needs to invent path names;
- `prod` and `non-prod` separation is explicit in all naming examples;
- PKI domains for `k8s` and `infra` are named once and reused consistently;
- AppRole use is bounded to documented bootstrap cases only.

**Evidence required:**

- signed registry document;
- platform and security approval;
- explicit mapping examples for management cluster, workload cluster, and external node auth paths.

---

## 5.4 `T0.4` Product Analytics Taxonomy, Privacy Baseline, And Feature-Flag Governance Freeze

**Packet alignment:** `P0.4`  
**Primary owners:** product, growth/data, security  
**Supporting owners:** backend platform, frontend/platform

**Repository touchpoints:**

- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:979)
- Create: `docs/growth-platform/posthog-product-taxonomy-and-privacy-baseline.md`
- Create: `docs/growth-platform/posthog-feature-flag-governance.md`
- Reference current feature flags: [frontend/src/features/dev/lib/feature-flags.ts](/home/beep/projects/VPNBussiness/frontend/src/features/dev/lib/feature-flags.ts:1)
- Reference current partner analytics runtime route: [partner/src/app/api/analytics/frontend-runtime/route.ts](/home/beep/projects/VPNBussiness/partner/src/app/api/analytics/frontend-runtime/route.ts:1)

**Scope:**

- freeze allowed and blocked analytics events and properties for PostHog;
- freeze privacy rules for VPN product analytics;
- freeze which feature-flag use cases are allowed and which are prohibited;
- freeze ownership and cleanup expectations for product flags and experiments.

**Deliverables:**

- PostHog event taxonomy baseline;
- blocked-property list;
- feature-flag governance contract;
- experiment governance template.

**Acceptance criteria:**

- prohibited categories such as VPN destinations, traffic metadata, raw IP, secrets, and private keys are explicitly listed;
- critical commercial events are marked as server-side or authoritative bridge only;
- product flags and infra/security kill switches are explicitly separated;
- frontend teams have one approved flag usage model and one fallback rule.

**Evidence required:**

- product and security sign-off;
- approved blocked-property list;
- sample event matrix showing frontend-only vs server-side vs NATS-bridge sources.

---

## 5.5 `T0.5` Node Fleet Controller Durable Model And Lifecycle Contract Freeze

**Packet alignment:** `P0.5`  
**Primary owners:** platform architecture, infra/platform, transport/backend  
**Supporting owners:** SRE/security

**Repository touchpoints:**

- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:805)
- Create: `docs/api/node-fleet-controller-domain-model.md`
- Create: `docs/api/node-fleet-controller-operator-command-model.md`
- Create: `docs/runbooks/platform-foundation-node-lifecycle-state-machine.md`
- Reference current fleet manual procedures: [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1)
- Reference current Helix scope: [services/helix-adapter/README.md](/home/beep/projects/VPNBussiness/services/helix-adapter/README.md:1)

**Scope:**

- freeze canonical entities for fleet automation;
- freeze node lifecycle states and observed-state fields;
- freeze the operator command model behind future `make node-add ...`;
- freeze safety boundaries between Node Fleet Controller, OpenTofu, OpenBao, and runtime adapters.

**Deliverables:**

- Node Fleet Controller domain model;
- node lifecycle state machine;
- operator command model and durable request semantics;
- boundary statement for what the controller owns vs what OpenTofu and adapters own.

**Acceptance criteria:**

- no later controller design needs to invent durable state types from scratch;
- `desired state`, `observed state`, `operation run`, `traffic eligibility`, and `bootstrap state` are defined once;
- `make node-add ...` is explicitly documented as wrapper UX, not source of truth;
- failover guardrail inputs are named and frozen.

**Evidence required:**

- signed fleet domain model document;
- transport/backend and infra owner approval;
- explicit state diagram or lifecycle table.

---

## 5.6 `T0.6` Monorepo Platform Foundation Inventory

**Packet alignment:** `P0.6`  
**Primary owners:** platform architecture, SRE/platform  
**Supporting owners:** backend, frontend, infra/platform, transport/backend

**Repository touchpoints:**

- Create: `docs/plans/2026-04-21-platform-foundation-monorepo-inventory.md`
- Reference deploy and infra baseline: [infra/docker-compose.yml](/home/beep/projects/VPNBussiness/infra/docker-compose.yml:1)
- Reference current CI/workflows: [iac-ci.yml](/home/beep/projects/VPNBussiness/.github/workflows/iac-ci.yml:1)
- Reference current edge rollout docs: [EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md](/home/beep/projects/VPNBussiness/docs/runbooks/EDGE_POST_DEPLOY_VERIFICATION_CHECKLIST.md:1)
- Reference current observability runbooks: [PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md](/home/beep/projects/VPNBussiness/docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md:1)
- Reference current outbox code: [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)
- Reference current SSE path: [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)
- Reference current fleet/manual procedures: [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1)

**Scope:**

- inventory every known deployment path;
- inventory current secrets sprawl and `.env` usage surfaces;
- inventory current collector and telemetry assumptions;
- inventory current realtime/event paths;
- inventory current node bootstrap and manual fleet steps;
- inventory current docs and prompts that still describe retired patterns.

**Minimum inventory sections:**

- deployment paths and who owns them;
- `promtail` and `otel-collector` references;
- `.env` and secrets-loading surfaces;
- outbox/eventing/realtime paths;
- edge and node bootstrap surfaces;
- GitHub Actions and release/promotion workflows;
- docs and runbooks that encode obsolete operational guidance.

**Acceptance criteria:**

- inventory references real paths, not category-only prose;
- every inventoried legacy path is marked as keep, migrate, or retire;
- every inventoried path has an owning team or owner lane;
- inventory covers `backend`, `services`, `frontend`, `partner`, `admin`, `infra`, `.github`, and docs.

**Evidence required:**

- merged inventory document;
- review sign-off from platform and SRE;
- explicit list of blockers this inventory creates for `Phase 1` and `Phase 2`.

---

## 5.7 `T0.7` Temporary Exceptions Register And Removal Deadlines

**Packet alignment:** `P0.8`  
**Primary owners:** platform architecture, program/SRE  
**Supporting owners:** all phase-owning lanes

**Repository touchpoints:**

- Create: `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
- Modify: [2026-04-21-platform-foundation-phased-implementation-plan.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md:368)

**Scope:**

- turn inventory findings into an explicit exceptions register;
- assign owner, risk, creation phase, and removal phase to each temporary exception;
- mark which exceptions are blocking and which are tolerated only in non-prod.

**Minimum exception classes to capture:**

- manual Compose deploys;
- Ansible-managed steady-state node procedures;
- host-local `.env` secrets;
- Promtail or standalone OTEL assumptions;
- Redis pub/sub paths still acting as primary business trigger paths;
- docs or prompts that still describe obsolete runtime models.

**Acceptance criteria:**

- every exception has owner, risk statement, and removal phase;
- no exception is recorded as “temporary” without removal verification requirements;
- no undocumented exception survives the register creation.

**Evidence required:**

- signed register;
- owner assignment completed;
- removal-phase mapping completed for every exception.

---

## 5.8 `T0.8` Phase Gates, Evidence Templates, And Conformance Scoring Model

**Packet alignment:** `P0.7`  
**Primary owners:** platform architecture, QA/program  
**Supporting owners:** SRE, backend platform, infra/platform

**Repository touchpoints:**

- Create: `docs/evidence/platform-foundation/platform-foundation-phase-evidence-template.md`
- Create: `docs/testing/platform-foundation-conformance-scorecard.md`
- Modify: [2026-04-21-platform-foundation-phased-implementation-plan.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md:396)
- Modify: [2026-04-21-platform-foundation-target-state-architecture.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-target-state-architecture.md:1138)

**Scope:**

- define what evidence must exist for `Gate A` through `Gate D`;
- define conformance scoring inputs against the target-state document;
- define mandatory proof shape for:
  - OpenBao;
  - NATS;
  - GitOps/Flux;
  - Alloy migration;
  - Node Fleet Controller;
  - PostHog privacy and server-side event delivery;
  - backup and recovery drills.

**Acceptance criteria:**

- no later phase can claim completion without evidence template coverage;
- conformance scorecard refers back to canonical production criteria, not ad-hoc phase opinions;
- evidence requirements distinguish between non-prod readiness and production conformance.

**Evidence required:**

- approved evidence template;
- approved conformance scorecard;
- explicit phase-gate mapping for `P1`, `P2`, and `P3`.

---

## 5.9 `T0.9` Phase 0 Closure And Sign-Off Pack

**Packet alignment:** phase-exit sign-off  
**Primary owners:** platform architecture, program/SRE  
**Supporting owners:** all `T0.x` owners

**Repository touchpoints:**

- Create: `docs/evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md`
- Modify: [2026-04-21-platform-foundation-phased-implementation-plan.md](/home/beep/projects/VPNBussiness/docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md:113)

**Scope:**

- collect outputs from `T0.1` through `T0.8`;
- list open residuals that block `P1`;
- formally declare `Gate A` pass or fail.

**Acceptance criteria:**

- every required `T0.x` artifact exists in git;
- every blocker is named and assigned;
- `Phase 1` start recommendation is explicit rather than implied.

**Evidence required:**

- signed closure pack;
- blocker list with owners and remediation path;
- explicit statement that `Gate A` is either passed or still blocked.

---

## 6. What Is Explicitly Out Of Scope For Phase 0

The following are intentionally **not** part of `Phase 0` execution:

- provisioning real `OpenBao`, `NATS`, or `PostHog` infrastructure;
- bootstrapping Talos management clusters;
- writing the first Helm charts or Flux manifests;
- implementing the outbox dispatcher or consumer framework;
- creating the Node Fleet Controller service;
- migrating runtime secrets into OpenBao;
- replacing Promtail with Alloy in code or manifests;
- instrumenting applications with PostHog SDKs.

If any ticket needs those to be considered “done”, the ticket is oversized and belongs to `Phase 1+`.

---

## 7. Phase 0 Can Be Declared Complete When

`Phase 0` can be declared complete only when all of the following are true:

1. Platform naming and boundary registry is frozen and signed off.
2. Event taxonomy, consumer contract, and outbox contract are frozen and signed off.
3. OpenBao and PKI naming registry is frozen and signed off.
4. PostHog taxonomy, privacy baseline, and feature-flag governance are frozen and signed off.
5. Node Fleet Controller durable model and lifecycle contract are frozen and signed off.
6. Monorepo inventory exists and covers all required repository areas.
7. Temporary exceptions register exists and every exception has owner plus removal phase.
8. Phase evidence template and conformance scorecard exist.
9. Phase 0 closure pack explicitly states whether `Gate A` is passed.

---

## 8. Immediate Next Actions After Phase 0

Once `Phase 0` is signed off, the next planning and execution documents should start in this order:

1. `OpenBao And PKI Implementation Plan`
2. `NATS JetStream Streams, Consumers, And Replay Spec`
3. `Platform GitOps Bootstrap Plan`
4. `Alloy Monorepo Migration Plan`
5. `Platform Foundation DR And Drill Plan`
6. `Node Fleet Controller Technical Design`
7. `PostHog Product Analytics And Privacy Spec`

No `Phase 1` infrastructure buildout should begin before the corresponding `Phase 0` blocking contracts are merged.

