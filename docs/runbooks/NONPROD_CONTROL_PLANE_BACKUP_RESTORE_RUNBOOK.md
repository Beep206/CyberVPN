# Non-Prod Control-Plane Backup And Restore Runbook

**Date:** 2026-04-22  
**Scope:** `openbao-nonprod`, `nats-nonprod`, `posthog-nonprod`, `nonprod-mgmt`

This runbook describes the operator workflow introduced by `P1.8`.

The canonical bundle renderer is:

- [infra/scripts/control_plane_recovery.py](/home/beep/projects/VPNBussiness/infra/scripts/control_plane_recovery.py:1)

The bundle is operator-facing, not in-cluster automation. It freezes:

- artifact layout;
- backup command baseline;
- restore note baseline;
- optional `S3` sync path for captured artifacts.

## 1. Render The Bundle

Prepare current stack outputs or equivalent JSON extracts for:

- `staging/openbao` node outputs
- `staging/nats` node outputs
- `staging/posthog` node outputs
- `nonprod-mgmt` Talos endpoints

Render:

```bash
python infra/scripts/control_plane_recovery.py render-bundle \
  --output-dir infra/artifacts/control-plane-recovery/nonprod \
  --openbao-nodes-file <openbao_nodes.json> \
  --nats-nodes-file <nats_nodes.json> \
  --posthog-nodes-file <posthog_nodes.json> \
  --talos-endpoints-file <talos_endpoints.json>
```

## 2. OpenBao

Required operator inputs:

- `VAULT_TOKEN`
- optional `OPENBAO_CA_CERT`
- optional `OPENBAO_SSH_TARGET`

Run:

```bash
bash infra/artifacts/control-plane-recovery/nonprod/openbao/snapshot-openbao.sh
```

Restore guidance:

- use [restore-openbao.md](/home/beep/projects/VPNBussiness/infra/artifacts/control-plane-recovery/nonprod/openbao/restore-openbao.md) from the rendered bundle
- prefer normal quorum recovery before snapshot restore

## 3. NATS

Required operator inputs:

- either `NATS_CONTEXT`, `NATS_CREDS_FILE`, or another valid CLI auth method
- optional `NATS_URL`

Run:

```bash
bash infra/artifacts/control-plane-recovery/nonprod/nats/backup-nats-account.sh
```

Restore guidance:

- use the rendered `restore-nats.md`
- prefer automatic quorum recovery when intact replicas still exist

## 4. PostHog

Required operator inputs:

- `POSTHOG_SSH_TARGET`
- optional `POSTHOG_SSH_KEY`

Run:

```bash
bash infra/artifacts/control-plane-recovery/nonprod/posthog/backup-posthog-over-ssh.sh
```

This triggers the host-local PostHog backup producer, then retrieves the newest artifact set and configuration snapshots.

## 5. Talos And etcd

Required operator inputs:

- `TALOSCONFIG`
- optional `TALOS_SNAPSHOT_NODE`

Run:

```bash
bash infra/artifacts/control-plane-recovery/nonprod/nonprod-mgmt/backup-etcd.sh
bash infra/artifacts/control-plane-recovery/nonprod/nonprod-mgmt/backup-machine-configs.sh
```

Restore guidance:

- use the rendered `restore-nonprod-mgmt.md`
- `talosctl bootstrap --recover-from` is the canonical snapshot recovery path

## 6. Object Store Sync

If object-store upload is enabled, export:

- `S3_URI`
- optional `AWS_S3_SSE`
- optional `AWS_S3_SSE_KMS_KEY_ID`

Each backup script calls the common sync helper after a successful artifact capture.

## 7. What This Runbook Does Not Claim

This runbook does not, by itself, prove:

- live restore success;
- Prometheus or Grafana runtime evidence;
- production DR readiness.

Those require explicit live drills and attached evidence packs.
