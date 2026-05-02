# CyberVPN Platform Foundation P1.8 Control-Plane Backup And Restore Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.8`  
**Phase:** `P1`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `platform-architecture`, `security`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P1.8`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-8-control-plane-backup-and-restore-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-8-control-plane-backup-and-restore-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-020` as the formal reason `P1.8` may remain in progress while later work begins.

---

## 2. Result Snapshot

Current `P1.8` result:

- canonical helper added at `infra/scripts/control_plane_recovery.py`;
- helper renders one operator-facing non-prod recovery bundle for:
  - `OpenBao`
  - `NATS`
  - `PostHog`
  - `Talos etcd` and machine-config metadata
- helper renders a shared optional `S3` sync helper for artifact upload;
- a dedicated runbook was added at `docs/runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md`;
- operator docs updated so `P1.8` recovery work is discoverable from `infra/README.md`.

This packet is **not yet claimed complete** because:

- no live bundle has been rendered from real stack outputs in this evidence window;
- no live `OpenBao` snapshot has been captured yet;
- no live `NATS` account backup or restore evidence has been attached yet;
- no live `Talos` `etcd` snapshot or `bootstrap --recover-from` drill evidence has been attached yet;
- no live `PostHog` retrieval evidence has been attached yet.

That is intentional. `P1.8` first closes the reproducible repo and operator-contract slice, while leaving actual DR drills explicit and evidence-driven.

---

## 3. Repository Changes Recorded

### 3.1 Recovery Helper And Tests

- `infra/scripts/control_plane_recovery.py`
  - renders backup scripts for:
    - `OpenBao`
    - `NATS`
    - `PostHog`
    - `Talos etcd` and machine configs
  - renders per-component restore notes
  - renders a common optional `S3` sync helper

- `infra/tests/test_control_plane_recovery.py`
  - validates bundle rendering against synthetic stack data
  - validates endpoint parsing for Talos control-plane endpoints

### 3.2 Operator Docs

- `infra/README.md`
  - now documents `control_plane_recovery.py` as the canonical `P1.8` operator surface

- `docs/runbooks/NONPROD_CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md`
  - provides one operational path for rendering and using the bundle

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_control_plane_recovery
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/control_plane_recovery.py
```

Result:

- compilation completed successfully

### 4.3 Helper Smoke Render

Command shape:

```bash
python infra/scripts/control_plane_recovery.py render-bundle \
  --output-dir <temporary-dir> \
  --openbao-nodes-file <synthetic-openbao.json> \
  --nats-nodes-file <synthetic-nats.json> \
  --posthog-nodes-file <synthetic-posthog.json> \
  --talos-endpoints-file <synthetic-talos.json>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `common/sync-to-s3.sh`
  - `openbao/snapshot-openbao.sh`
  - `openbao/restore-openbao.md`
  - `nats/backup-nats-account.sh`
  - `nats/restore-nats.md`
  - `posthog/backup-posthog-over-ssh.sh`
  - `posthog/restore-posthog.md`
  - `nonprod-mgmt/backup-etcd.sh`
  - `nonprod-mgmt/backup-machine-configs.sh`
  - `nonprod-mgmt/restore-nonprod-mgmt.md`
  - `README.md`
  - `versions.env`

### 4.4 Workspace Readiness Check For Live Recovery Evidence

Observed in the current workspace on 2026-04-22:

- no real `OpenBao`, `NATS`, `PostHog`, or `nonprod-mgmt` credentials are present for live DR execution;
- no real `TALOSCONFIG`, `NATS` auth material, or `VAULT_TOKEN` is available in the current session;
- no real object-store destination is configured for artifact upload evidence;
- no actual restore drills have been executed from this workspace.

Meaning:

- the packet cannot honestly claim live backup or restore success yet;
- live DR evidence must remain a follow-up step under explicit operator control;
- `P1.8` therefore carries a formal residual until real backup and restore proof exists.

---

## 5. Remaining Live Closure Requirements

`P1.8` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. real bundle render from current non-prod stack outputs;
2. one successful `OpenBao` snapshot capture plus artifact record;
3. one successful `NATS` account backup and either:
   - a restore drill in isolation
   - or a documented rebuild validation against backup artifacts;
4. one successful `Talos` `etcd` snapshot capture plus machine-config backup capture;
5. one explicit `Talos` recovery proof using `bootstrap --recover-from` in a drill or approved isolated environment;
6. one successful `PostHog` backup retrieval over the frozen SSH flow;
7. if `S3` upload is enabled, one proof that the captured artifacts reached the intended object-store prefix.

