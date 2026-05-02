# CyberVPN Platform Foundation P1.3 NATS Non-Prod Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.3`  
**Phase:** `P1`  
**Primary owners:** `infra-platform` / `sre-platform`  
**Supporting owners:** `platform-architecture`, `security`  
**Purpose:** record the concrete repository, validation, and operator-surface changes completed for `P1.3`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-3-nats-nonprod-foundation-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-3-nats-nonprod-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-015` as the formal reason `P1.3` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.3` result:

- dedicated non-prod `NATS` stack created at `infra/terraform/live/staging/nats`;
- dedicated Hetzner VM module created at `infra/terraform/modules/nats_node`;
- canonical 3-node `nats-nonprod` topology established with local JetStream storage paths;
- route ingress restricted to cluster node IPs through firewall policy and attachments;
- pinned cloud-init/systemd/bootstrap path created for `nats-server 2.12.7` and `prometheus-nats-exporter 0.18.0`;
- canonical account and subject-permission example created at `infra/nats/examples/accounts.json.example`;
- canonical bootstrap helper created at `infra/scripts/nats_bootstrap.py`;
- unit tests and local bundle-render smoke added for the bootstrap helper;
- local Prometheus baseline updated with a dedicated `nats-exporter` scrape job and `nats_alerts.yml`.

This packet is **not yet claimed complete** because:

- no operator-approved live `tofu apply` against real remote backend and cloud credentials has been executed in this evidence window;
- no live config/TLS bundle installation has been executed on real nodes yet;
- no live cluster-formation, stream-create, publish/consume, replay, or credential-rotation evidence has been attached yet;
- no real Prometheus target handoff from bundle output to a running metrics plane has been attached yet.

That is intentional. `P1.3` has completed the safe repo and validation slice first, while leaving live event-backbone bring-up under manual approval.

---

## 3. Repository Changes Recorded

### 3.1 Reusable Infrastructure Layer

- `infra/terraform/modules/nats_node`
  - added dedicated Hetzner VM module for external `NATS`
  - provisions:
    - primary IPv4
    - cloud-init bootstrap
    - pinned `nats-server` install
    - pinned `prometheus-nats-exporter` install
    - gated systemd units
    - bootstrap metadata for out-of-band bundle installation

### 3.2 Non-Prod NATS Stack

- `infra/terraform/live/staging/nats`
  - dedicated stack for the canonical `nats-nonprod` control plane
  - creates:
    - 3 dedicated NATS nodes
    - NATS firewall
    - firewall attachments after node IP discovery
  - reads only the legacy `staging/foundation` SSH key registry through remote state

### 3.3 NATS Baseline Assets

- `infra/nats/examples/accounts.json.example`
  - bounded non-prod baseline for:
    - `SYS`
    - `PLATFORM`
  - includes subject-scoped example users for:
    - billing
    - notifications
    - partner realtime
    - fleet control
    - node agents
    - analytics bridge

### 3.4 Bootstrap Helper And Tests

- `infra/scripts/nats_bootstrap.py`
  - renders:
    - local CA
    - per-node server certs
    - per-node `nats-server.conf`
    - per-node `nats-exporter.env`
    - per-node install script
    - generated credentials manifest
    - Prometheus `file_sd` target artifact

- `infra/tests/test_nats_bootstrap.py`
  - validates account rendering
  - validates bundle output structure under mocked crypto helpers

### 3.5 Monitoring And Operator Docs

- `infra/prometheus/prometheus.yml`
  - narrowed `alloy-edge` target discovery to `alloy-*.json`
  - added dedicated `nats-exporter` target discovery for `nats-*.json`

- `infra/prometheus/rules/nats_alerts.yml`
  - added exporter, route-count, and slow-consumer baseline alerts

- `infra/terraform/README.md`
- `infra/README.md`
- `infra/terraform/live/staging/nats/README.md`

These now acknowledge the new shared non-prod `NATS` foundation path.

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 OpenTofu Formatting

Command:

```bash
/tmp/opentofu-1.11.6/tofu fmt -recursive \
  infra/terraform/modules/nats_node \
  infra/terraform/live/staging/nats
```

Result:

- formatting completed successfully

### 4.2 OpenTofu Init And Validate

Commands:

```bash
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/nats init -backend=false -input=false -no-color
/tmp/opentofu-1.11.6/tofu -chdir=infra/terraform/live/staging/nats validate -no-color
```

Result:

- initialization completed successfully with `-backend=false`
- validation completed successfully

### 4.3 Bootstrap Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_nats_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

Coverage intent:

- account rendering generates bounded credentials correctly
- bundle rendering writes config, installer, credential, and Prometheus artifacts as expected

### 4.4 Bootstrap Helper Smoke Render

Command shape:

```bash
python infra/scripts/nats_bootstrap.py render-bundle \
  --cluster-name nats-nonprod \
  --nodes-file <synthetic-nodes.json> \
  --accounts-file infra/nats/examples/accounts.json.example \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against a synthetic 3-node input
- expected artifacts were created:
  - `credentials.json`
  - `prometheus/nats-nonprod-targets.json`
  - `<node>/nats-server.conf`
  - `<node>/nats-exporter.env`
  - `<node>/install-node.sh`

### 4.5 Stack Lockfile

Observed artifact:

- `infra/terraform/live/staging/nats/.terraform.lock.hcl`

Interpretation:

- the new stack is pinned and reproducible under the current `OpenTofu` toolchain

### 4.6 Workspace Readiness Check For Live NATS Evidence

Observed in the current workspace on 2026-04-22:

- no `backend.hcl` is present under `infra/terraform/live/staging/nats`
- no real `TF_VAR_hcloud_token` or remote-backend credentials are present for a live stack apply
- no live node outputs exist from a real `tofu apply`
- no real Prometheus target handoff exists for the generated `nats-*.json` file

Meaning:

- live `tofu init/plan/apply` cannot be executed honestly from this workspace yet
- live config/TLS bundle installation evidence cannot be attached yet
- live stream, publish/consume, replay, and monitoring evidence cannot be attached yet
- the blocker is missing operator-provided backend config and cloud credentials, not missing repo automation

---

## 5. State-Boundary Confirmation

The following invariants were preserved during this evidence window:

1. `staging/nats` is a separate stack from:
   - `staging/foundation`
   - `staging/openbao`
   - `staging/edge`
   - `staging/dns`
   - `staging/control-plane`
2. the new stack reads only `staging/foundation` remote state for SSH key names
3. canonical ids remain:
   - `environment = nonprod`
   - `nats_cluster_id = nats-nonprod`
4. no legacy control-plane state was merged or extended
5. no live infrastructure apply was executed as part of this repo/validation slice

Explicitly not changed:

- legacy `staging` implementation path naming on disk
- current `foundation`, `openbao`, `edge`, `dns`, and `control-plane` state boundaries
- runtime event publishing or consumer cut-over from existing app paths
- live stream declarations, replay drills, or credential rotation automation

---

## 6. Residuals Before Packet Closure

Open residuals:

1. `remote-backend apply evidence` for the first real non-prod `NATS` stack apply is still pending.
2. `bundle installation evidence` for all three nodes is still pending.
3. `cluster formation evidence` is still pending.
4. `stream create/publish/consume evidence` is still pending.
5. `replay evidence` is still pending.
6. `Prometheus scrape evidence` for `nats-exporter` is still pending.
7. `credential replacement or rotation evidence` is still pending.
8. `live metric-name verification` for `nats_alerts.yml` against a running exporter is still pending.

These residuals block a full `P1.3 complete` claim, but they do **not** invalidate the already-completed repository and validation slice above.

---

## 7. Recommended Next Live Commands

When operator-provided `backend.hcl` and credentials exist, the first honest live sequence should be:

```bash
tofu -chdir=infra/terraform/live/staging/nats init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/staging/nats plan -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/nats apply -var-file=terraform.tfvars
tofu -chdir=infra/terraform/live/staging/nats output -json nats_nodes > /tmp/nats-nonprod-nodes.json
```

Then from the repository workspace:

```bash
python infra/scripts/nats_bootstrap.py render-bundle \
  --cluster-name nats-nonprod \
  --nodes-file /tmp/nats-nonprod-nodes.json \
  --accounts-file infra/nats/examples/accounts.json.example \
  --output-dir infra/artifacts/nats-bootstrap/nats-nonprod
```

Then on each provisioned host:

```bash
sudo /path/to/install-node.sh
sudo systemctl status --no-pager nats.service
sudo systemctl status --no-pager nats-exporter.service
```

Finally, with real credentials:

```bash
nats --server tls://<node>:4222 stream add ...
nats --server tls://<node>:4222 pub ...
nats --server tls://<node>:4222 consumer next ...
```

Evidence for each step should be archived under:

```text
docs/evidence/platform-foundation/2026-04-22/p1-3-nats-nonprod-foundation/
```
