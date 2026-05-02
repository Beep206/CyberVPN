# CyberVPN Platform Foundation P1.8 Control-Plane Backup And Restore Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live backup and restore evidence pending  
**Packet:** `P1.8`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `platform-architecture`, `security`

---

## 1. Packet Role

This document is the execution packet for `P1.8` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md](../runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.8` exists to establish the first canonical backup and restore baseline for the new non-prod control planes and the management-cluster metadata layer:

- `openbao-nonprod`
- `nats-nonprod`
- `posthog-nonprod`
- `nonprod-mgmt` `etcd` and machine configuration metadata

Implementation note:

- the repository slice for this packet is implemented and locally validated in the monorepo;
- live closure still depends on real backup captures, object-store handoff if enabled, and at least one restore or rebuild proof for the covered systems.

---

## 2. Current Baseline

Before this packet:

- the target-state architecture already froze:
  - scheduled OpenBao Raft snapshots
  - NATS backup and rebuild drills
  - Talos `etcd` snapshots plus machine-config backup
  - separate PostHog backup posture
- `P1.4` already introduced a host-local PostHog backup producer, but not a unified operator bundle and restore contract;
- the repo already had legacy control-plane PostgreSQL backup surfaces, but not a dedicated non-prod control-plane recovery bundle for the new foundational systems.

Observed strengths:

- `P1.2` through `P1.5` already froze the control-plane ids and stack boundaries;
- the target-state and phased plan already place backup and DR work in `WS3`;
- operator-facing helper patterns already exist in this monorepo for `OpenBao`, `NATS`, `PostHog`, and `nonprod-mgmt`.

Observed implementation risks:

- backup logic can drift into four unrelated ad hoc procedures unless one operator-facing bundle is frozen now;
- `PostHog` can be mistaken for “already backed up enough” because of the local timer even though retrieval and restore contracts were not yet explicit;
- Talos `etcd` recovery can be hand-waved unless the exact `talosctl` backup and `bootstrap --recover-from` posture is written down alongside operator scripts.

---

## 3. Canonical Decisions For P1.8

`P1.8` fixes the following decisions:

1. `P1.8` uses one operator-facing non-prod recovery bundle, not four unrelated one-off procedures.
2. OpenBao backup is based on `bao operator raft snapshot save` plus peer/config capture.
3. OpenBao restore is based on `bao operator raft snapshot restore` or the equivalent API endpoint.
4. NATS backup baseline uses `nats account backup` and restore baseline uses `nats account restore`.
5. NATS recovery still prefers intact-quorum automatic recovery before manual restore.
6. Talos backup baseline uses `talosctl etcd snapshot` plus machine-config capture.
7. Talos disaster recovery baseline uses `talosctl bootstrap --recover-from`.
8. PostHog backup baseline remains separate from platform observability and is retrieved through the dedicated host-local backup producer plus configuration capture.
9. Optional `S3` sync is part of the operator bundle, but live object-store closure is not faked inside this packet.

---

## 4. Scope

In scope for `P1.8`:

- add a canonical helper under [infra/scripts/control_plane_recovery.py](../../infra/scripts/control_plane_recovery.py);
- render one operator-facing backup and recovery bundle for:
  - `OpenBao`
  - `NATS`
  - `PostHog`
  - `Talos etcd` and machine config
- add unit tests and local render smoke for the helper;
- add a dedicated runbook for non-prod control-plane backup and restore;
- update operator docs and residual tracking for honest `P1.8` closure.

Out of scope for `P1.8`:

- live restore of every system from this workspace;
- Kubernetes-native backup orchestration (`Velero`, `CSI`, `CNPG`) which belongs later in `P2`;
- production control-plane DR;
- VPN or edge node backup, which remains reprovision-first.

---

## 5. Official Constraints

The execution of `P1.8` follows current primary-source guidance:

- OpenBao integrated storage supports `raft snapshot save` and `raft snapshot restore`, and large snapshots may require a raised `VAULT_CLIENT_TIMEOUT`;
- NATS JetStream disaster recovery prefers automatic recovery from intact quorum nodes, and `nats account backup` / `nats account restore` exist for full account-level stream snapshot workflows;
- Talos disaster recovery requires routine `etcd` snapshots and machine-configuration backups, and recovery uses `talosctl bootstrap --recover-from`;
- PostHog self-host remains an external VM and Docker-based system; the backup and restore producer for this program is therefore explicitly operator-managed and separate from the platform observability stack.

Primary sources:

- OpenBao `operator raft`: https://openbao.org/docs/commands/operator/raft/
- OpenBao Raft snapshot API: https://openbao.org/api-docs/system/storage/raft/
- NATS JetStream disaster recovery: https://docs.nats.io/running-a-nats-service/nats_admin/jetstream_admin/disaster_recovery
- Talos disaster recovery: https://docs.siderolabs.com/talos/v1.9/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery
- Talos CLI reference: https://docs.siderolabs.com/talos/v1.13/reference/cli
- PostHog self-host overview: https://posthog.com/docs/self-host
- PostHog hobby deploy posture: https://posthog.com/docs/self-host/deploy/hobby

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.8`:

### 6.1 Recovery Helper And Tests

- [infra/scripts/control_plane_recovery.py](../../infra/scripts/control_plane_recovery.py)
- [infra/tests/test_control_plane_recovery.py](../../infra/tests/test_control_plane_recovery.py)

### 6.2 Operator Docs And Runbooks

- [infra/README.md](../../infra/README.md)
- [../runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md](../runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p1-8-control-plane-backup-and-restore/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p1-8-control-plane-backup-and-restore/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T1.8.1` Freeze The Non-Prod Recovery Bundle Shape

**Goal:** create one canonical operator-facing artifact set instead of scattered component-specific scratch notes.

Deliverables:

- a helper that renders bundle structure for:
  - `openbao/`
  - `nats/`
  - `posthog/`
  - `nonprod-mgmt/`
  - `common/`
- per-component backup script and restore note
- one shared optional `S3` sync helper

Acceptance criteria:

- bundle renders reproducibly from current stack node data;
- every covered control-plane system has both a backup path and a restore note;
- bundle output is operator-facing and does not claim live automation that does not exist.

### 7.2 `T1.8.2` Freeze The Recovery Commands To Primary-Source Posture

**Goal:** stop drift between architecture docs and real operator commands.

Deliverables:

- OpenBao snapshot script using `bao operator raft snapshot save`
- NATS backup script using `nats account backup`
- Talos `etcd` snapshot and machine-config scripts
- restore notes for OpenBao, NATS, and Talos that reference the canonical recovery primitives

Acceptance criteria:

- scripts and restore notes match the official command family;
- restore notes explicitly prefer non-destructive or quorum-preserving recovery where the upstream docs do;
- the repo no longer depends on tacit recovery knowledge for these systems.

### 7.3 `T1.8.3` Fold PostHog Into The Same Recovery Contract Without Merging Domains

**Goal:** make PostHog recoverable without pretending it is a platform-critical control plane.

Deliverables:

- PostHog SSH retrieval script that triggers the host-local backup producer
- PostHog restore note that preserves the dedicated VM or Docker boundary
- explicit statement that PostHog recovery is separate from platform observability and does not replace later product-validation work

Acceptance criteria:

- the script retrieves the host-local artifact plus config baseline;
- the restore note stays within the dedicated PostHog domain;
- the packet does not mislabel PostHog as source-of-truth business state.

### 7.4 `T1.8.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real DR drill is claimed.

Deliverables:

- helper unit tests;
- local render smoke;
- packet evidence pack;
- formal carry-forward residual for missing live backup and restore evidence.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are written explicitly;
- later packets may begin without pretending that actual restore drills already passed.

---

## 8. State-Boundary Rules

`P1.8` must keep the following invariants:

1. OpenBao remains the secrets plane and is backed up through Raft snapshots, not through generic VM-image backup as the primary path.
2. NATS remains the event backbone and is backed up through JetStream snapshot semantics, not treated as business source of truth.
3. Talos recovery protects `etcd` metadata and machine configuration, not arbitrary host package state.
4. PostHog remains a separate product-intelligence system and is recovered through its own bundle path.
5. VPN and edge fleet DR remains reprovision-first and outside this packet.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| backup procedures fragment per component | DR becomes person-dependent and non-repeatable | one canonical operator bundle and one runbook |
| NATS is treated like a database restore-first system | replay and source-of-truth boundaries blur | keep NATS restore notes explicit about intact quorum preference |
| Talos recovery is reduced to “we have kubeconfig somewhere” | control-plane metadata becomes irrecoverable after node loss | freeze etcd snapshot and machine-config capture in the same bundle |
| PostHog is either ignored or over-elevated | analytics either become unrecoverable or get conflated with control truth | keep dedicated PostHog script and restore note with separate domain language |

