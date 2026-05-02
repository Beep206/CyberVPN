# CyberVPN Platform Foundation P1.7 Control-Plane Observability Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live rollout evidence pending  
**Packet:** `P1.7`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `platform-architecture`, `security`

---

## 1. Packet Role

This document is the execution packet for `P1.7` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.7` exists to establish the first canonical observability substrate for the newly introduced non-prod external control planes:

- `openbao-nonprod`
- `nats-nonprod`
- `posthog-nonprod`

Implementation note:

- the repository slice for this packet is implemented and locally validated in the monorepo;
- live closure still depends on real host rollout, real Prometheus target handoff, and running Grafana or Prometheus evidence.

---

## 2. Current Baseline

Before this packet:

- the target-state architecture already froze the rule that newly introduced systems must converge on a single target collector family, with `Alloy` as the external VM collector baseline;
- the repo already had an edge-focused Alloy rollout path and edge dashboarding, but nothing yet for the new control-plane VM class;
- `P1.3` already introduced `nats-exporter`, but there was no common dashboard or alert surface tying `OpenBao`, `NATS`, and `PostHog` VM logs and host collectors together;
- the monorepo inventory already recorded `promtail` and standalone `otel-collector` as legacy surfaces to retire rather than expand.

Observed strengths:

- the repo already includes a working local Prometheus and Grafana surface;
- the edge Alloy role provided a stable pattern for `loki.write`, `loki.source.file`, and `file_sd` target generation;
- `P1.2`, `P1.3`, and `P1.4` already froze canonical cluster and instance ids for `OpenBao`, `NATS`, and `PostHog`.

Observed implementation risks:

- adding new VM control planes without immediate observability would create blind spots before `P2` workload migration starts;
- pushing host-level Alloy onto Talos nodes would violate the frozen boundary that management-cluster add-on observability lands later through Kubernetes-native paths;
- keeping `promtail` or standalone `otel-collector` alive as the rollout pattern for newly introduced systems would directly contradict the target-state collector convergence.

---

## 3. Canonical Decisions For P1.7

`P1.7` fixes the following decisions:

1. Newly introduced external control-plane VMs use `Alloy` as the canonical collector baseline.
2. `promtail` and standalone long-lived `otel-collector` processes are not valid rollout targets for new external control-plane systems.
3. `P1.7` covers only the new external VM control planes:
   - `openbao-nonprod`
   - `nats-nonprod`
   - `posthog-nonprod`
4. `nonprod-mgmt` Talos add-on observability is explicitly out of scope for this packet and lands later through the Kubernetes path.
5. Prometheus discovers new control-plane Alloy targets through `file_sd`.
6. OpenBao metrics are scraped directly from the dedicated metrics listener using HTTPS and a dedicated `openbao` scrape job.
7. The `P1.3` `nats-exporter` job remains the canonical NATS metrics path; `P1.7` does not replace it.
8. Grafana gets a dedicated control-plane dashboard rather than overloading the edge dashboard.

---

## 4. Scope

In scope for `P1.7`:

- add a canonical helper under [infra/scripts/control_plane_observability.py](../../infra/scripts/control_plane_observability.py);
- render per-host Alloy bundles for the new external control-plane VMs;
- render Prometheus `file_sd` target artifacts for:
  - `alloy-control-plane`
  - `openbao`
- extend Prometheus scrape config and alert rules for the new surfaces;
- add a dedicated Grafana dashboard for the new control-plane observability surface;
- update operator docs and residual tracking for honest `P1.7` closure.

Out of scope for `P1.7`:

- host-level Alloy rollout on Talos nodes;
- Kubernetes DaemonSet or Deployment observability rollout;
- Tempo, OTLP gateway, or full workload tracing cut-in;
- production control-plane observability rollout;
- decommission of every legacy `promtail` or `otel-collector` path already present elsewhere in the repo.

---

## 5. Official Constraints

The execution of `P1.7` follows current primary-source guidance:

- `loki.write` is the supported way to forward logs from Alloy to Loki;
- `loki.source.journal` is valid for systemd journal reads but requires the `alloy` user to be in the `adm` and `systemd-journal` groups;
- `loki.source.file` is valid for file tails and supports `local.file_match` or built-in `file_match` discovery;
- on Linux, Alloy is configured through `/etc/alloy/config.alloy` and additional command-line flags are added via the systemd service configuration;
- Promtail is in end-of-life transition and new collection work should land in Alloy instead.

Primary sources:

- Alloy `loki.write`: https://grafana.com/docs/grafana-cloud/send-data/alloy/reference/components/loki/loki.write/
- Alloy `loki.source.journal`: https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.journal/
- Alloy `loki.source.file`: https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.file/
- Configure Alloy on Linux: https://grafana.com/docs/alloy/latest/configure/linux/
- Promtail merge and EOL direction: https://grafana.com/blog/grafana-loki-3-4-standardized-storage-config-sizing-guidance-and-promtail-merging-into-alloy/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.7`:

### 6.1 Bootstrap Helper And Tests

- [infra/scripts/control_plane_observability.py](../../infra/scripts/control_plane_observability.py)
- [infra/tests/test_control_plane_observability.py](../../infra/tests/test_control_plane_observability.py)

### 6.2 Monitoring Surface

- [infra/prometheus/prometheus.yml](../../infra/prometheus/prometheus.yml)
- [infra/prometheus/rules/control_plane_alerts.yml](../../infra/prometheus/rules/control_plane_alerts.yml)
- [infra/grafana/dashboards/control-plane-observability-dashboard.json](../../infra/grafana/dashboards/control-plane-observability-dashboard.json)
- [infra/tests/validate_dashboards.sh](../../infra/tests/validate_dashboards.sh)

### 6.3 Operator Docs And Evidence

- [infra/README.md](../../infra/README.md)
- [../evidence/platform-foundation/2026-04-22/p1-7-control-plane-observability/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p1-7-control-plane-observability/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T1.7.1` Freeze The New External Control-Plane Collector Baseline

**Goal:** stop new VM control planes from drifting into `promtail` or standalone `otel-collector` rollout paths.

Deliverables:

- a canonical bundle renderer for external control-plane Alloy installs;
- stable log label shape for:
  - `job`
  - `project`
  - `environment`
  - `component`
  - `cluster_id`
  - `instance`
- per-host install script with the required journal access posture.

Acceptance criteria:

- all new external control-plane VMs use the same collector family;
- the helper writes reproducible per-host bundle artifacts;
- the helper explicitly documents that Talos host-level rollout is out of scope.

### 7.2 `T1.7.2` Freeze The Prometheus And Alert Surface

**Goal:** make the new telemetry paths visible in the canonical monitoring stack.

Deliverables:

- `alloy-control-plane` scrape job;
- `openbao` scrape job;
- baseline alert rules for control-plane collector and OpenBao metrics availability.

Acceptance criteria:

- Prometheus can discover the new control-plane surfaces through `file_sd`;
- rules are based on metrics that can be validated locally or are already present through standard `up` semantics;
- the existing `nats-exporter` path remains intact.

### 7.3 `T1.7.3` Freeze The First Operator Dashboard

**Goal:** give operators one dedicated place to inspect the new external control-plane telemetry without overloading unrelated dashboards.

Deliverables:

- a dedicated Grafana dashboard for:
  - control-plane Alloy availability
  - OpenBao metrics availability
  - NATS exporter availability
  - control-plane logs via Loki

Acceptance criteria:

- the dashboard is valid JSON;
- the dashboard references the new `alloy-control-plane` surface explicitly;
- dashboard validation scripts acknowledge the new file.

### 7.4 `T1.7.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without pretending the real hosts already have Alloy installed.

Deliverables:

- helper unit tests;
- local bundle-render smoke;
- dashboard JSON validation;
- packet evidence pack;
- carry-forward exception for missing live rollout and monitoring evidence.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are written explicitly;
- later packets may begin without pretending that the live non-prod control-plane observability substrate is already proven.

---

## 8. State-Boundary Rules

`P1.7` must keep the following invariants:

1. New external control-plane VMs use `Alloy` as the target collector.
2. `P1.7` does not convert Talos nodes into package-managed Linux hosts.
3. OpenBao remains scraped through its own metrics endpoint and does not depend on logs-only visibility.
4. NATS metrics remain sourced from the dedicated exporter introduced in `P1.3`.
5. `PostHog` remains a product-intelligence system and not a substitute for operational observability.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| Talos gets treated like a normal Ubuntu host | would violate the frozen management-cluster posture and create unowned host drift | document `nonprod-mgmt` as an explicit non-goal in helper output and packet scope |
| new control-plane VMs drift back to Promtail or standalone OTEL | collector convergence slips before `P2` | helper and docs state Alloy-only posture for new systems |
| rules depend on non-validated component-specific metrics | alerting becomes brittle before live rollout exists | limit `P1.7` alerts to `up`-based availability checks |
| operator assumes live observability already exists | later packets inherit false confidence | carry forward a formal residual until live rollout and scrape evidence is attached |

