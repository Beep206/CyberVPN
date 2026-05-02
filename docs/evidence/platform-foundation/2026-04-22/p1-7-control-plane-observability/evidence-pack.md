# CyberVPN Platform Foundation P1.7 Control-Plane Observability Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P1.7`  
**Phase:** `P1`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `platform-architecture`, `security`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P1.7`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p1-7-control-plane-observability-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p1-7-control-plane-observability-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- the sign-off pack allows `P1` implementation work to proceed while that governance step remains open.
- this evidence pack currently carries `EX-019` as the formal reason `P1.7` may remain in progress while later `P1` packets begin.

---

## 2. Result Snapshot

Current `P1.7` result:

- canonical helper added at `infra/scripts/control_plane_observability.py`;
- helper renders per-host Alloy bundles for:
  - `openbao-nonprod`
  - `nats-nonprod`
  - `posthog-nonprod`
- helper renders Prometheus `file_sd` target artifacts for:
  - `alloy-control-plane`
  - `openbao`
- Prometheus config extended with dedicated `alloy-control-plane` and `openbao` scrape jobs;
- baseline `control_plane_alerts.yml` added for collector and OpenBao availability;
- dedicated Grafana dashboard added at `infra/grafana/dashboards/control-plane-observability-dashboard.json`;
- dashboard validation script extended to assert the new dashboard exists and references the new telemetry surface;
- operator docs updated to freeze `Alloy` as the collector family for these new external control-plane systems.

This packet is **not yet claimed complete** because:

- no live bundle has been installed onto real `OpenBao`, `NATS`, or `PostHog` hosts yet;
- no real monitoring-host `file_sd` handoff has been executed yet;
- no live Prometheus target evidence exists yet for:
  - `alloy-control-plane`
  - `openbao`
- no live Grafana or Loki screenshots or query output have been attached yet;
- no live alert firing or silence-validation evidence has been attached yet.

That is intentional. `P1.7` first closes the safe repo and validation slice, while keeping live rollout explicitly gated.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/control_plane_observability.py`
  - renders per-node `config.alloy`, `cybervpn-alloy.service`, and `install-alloy.sh`
  - renders Prometheus `file_sd` target files for the new control-plane substrate
  - freezes the non-goal that `nonprod-mgmt` Talos add-on observability is not part of this host-level packet

- `infra/tests/test_control_plane_observability.py`
  - validates bundle rendering for synthetic `OpenBao`, `NATS`, and `PostHog` node inventories
  - validates Prometheus target generation
  - validates helper input checks for partial Loki auth configuration

### 3.2 Monitoring Surface

- `infra/prometheus/prometheus.yml`
  - adds `control_plane_alerts.yml`
  - adds `alloy-control-plane` `file_sd` discovery
  - adds `openbao` `file_sd` discovery with HTTPS metrics scrape

- `infra/prometheus/rules/control_plane_alerts.yml`
  - adds:
    - `AlloyControlPlaneDown`
    - `OpenBaoMetricsDown`

- `infra/grafana/dashboards/control-plane-observability-dashboard.json`
  - adds dedicated operator dashboard for:
    - control-plane Alloy target availability
    - OpenBao target availability
    - NATS exporter availability
    - logs via Loki

- `infra/tests/validate_dashboards.sh`
  - now asserts the control-plane dashboard exists and references `alloy-control-plane`

### 3.3 Operator Documentation

- `infra/README.md`
  - now documents the new helper as the canonical operator surface for the new control-plane VM collector baseline

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_control_plane_observability
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Helper Smoke Render

Command shape:

```bash
python infra/scripts/control_plane_observability.py render-bundle \
  --output-dir <temporary-dir> \
  --openbao-nodes-file <synthetic-openbao.json> \
  --nats-nodes-file <synthetic-nats.json> \
  --posthog-nodes-file <synthetic-posthog.json>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `hosts/<name>/config.alloy`
  - `hosts/<name>/cybervpn-alloy.service`
  - `hosts/<name>/install-alloy.sh`
  - `prometheus/control-plane-alloy-nonprod.json`
  - `prometheus/openbao-nonprod-targets.json`
  - `README.md`

### 4.3 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/control_plane_observability.py
```

Result:

- compilation completed successfully

### 4.4 Grafana Dashboard Validation

Command:

```bash
bash infra/tests/validate_dashboards.sh
```

Result:

- dashboard count check passed
- JSON syntax validation passed
- Loki and Tempo datasource checks passed
- edge dashboard check passed
- control-plane dashboard check passed

### 4.5 Workspace Readiness Check For Live Observability Evidence

Observed in the current workspace on 2026-04-22:

- no real `OpenBao`, `NATS`, or `PostHog` hosts have been provisioned in this evidence window;
- no monitoring-host `file_sd` directory or Prometheus reload evidence is attached in this workspace;
- no live Loki endpoint credentials are present for a real host bundle rollout;
- no real Grafana screenshots or query captures exist yet for the new dashboard.

Meaning:

- live host rollout cannot be claimed honestly from the current workspace;
- live scrape, log-ingest, and alert evidence cannot be attached yet;
- `P1.7` must carry a formal residual until those steps are executed against the real non-prod substrate.

---

## 5. Remaining Live Closure Requirements

`P1.7` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. live bundle render using real `tofu output -json` artifacts from:
   - `infra/terraform/live/staging/openbao`
   - `infra/terraform/live/staging/nats`
   - `infra/terraform/live/staging/posthog`
2. successful host-level installation of the rendered Alloy bundle on the real external control-plane VMs;
3. monitoring-host handoff of:
   - `control-plane-alloy-*.json`
   - `openbao-*.json`
4. live Prometheus evidence for:
   - `up{job="alloy-control-plane"}`
   - `up{job="openbao"}`
   - continued `up{job="nats-exporter"}`
5. live Grafana or Loki evidence showing:
   - logs arriving from `openbao`, `nats`, and `posthog`
   - dashboard panels returning real non-prod data
6. at least one operator-attached proof that `nonprod-mgmt` host-level rollout was intentionally not attempted as part of `P1.7`.

