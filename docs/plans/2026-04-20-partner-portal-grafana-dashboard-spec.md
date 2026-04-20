# CyberVPN Partner Portal Grafana Dashboard Spec

**Date:** 2026-04-20  
**Status:** Dashboard specification  
**Purpose:** define the required Grafana dashboards, audiences, panels, drilldowns, and datasource usage for the partner platform.

---

## 1. Document Role

This document defines the dashboard layer for:

- engineering;
- SRE;
- partner ops;
- finance ops;
- risk and compliance;
- support;
- product leadership.

It describes what must exist in Grafana, not the exact JSON provision files.

---

## 2. Datasource Baseline

Dashboards must use the provisioned datasources already present in the repository:

- `Prometheus` for metrics and recording rules;
- `Tempo` for traces;
- `Loki` for structured logs.

Preferred flow:

- metrics panel -> drilldown to trace or logs;
- incident panel -> link to alert or runbook;
- business-operational panel -> bounded filters only.

---

## 3. Shared Dashboard Variables

Use these variables where relevant:

- `env`
- `service`
- `surface`
- `lane`
- `route_group`
- `release_ring`
- `region`
- `queue_name`
- `job_name`
- `integration_type`
- `payment_provider`

Do not use free-form per-entity variables such as workspace ID or code ID as top-level dashboard variables.

---

## 4. Dashboard Design Principles

1. Keep each dashboard audience-specific.
2. Put SLI/SLO panels above diagnostic panels.
3. Prefer rate, latency, queue age, and backlog over raw counters alone.
4. Every dashboard should include at least one drilldown path to logs or traces where relevant.
5. Avoid variable combinations that explode Prometheus cardinality or produce unreadable panels.

---

## 5. Required Dashboards

### 5.1 Partner Platform Executive Overview

**Audience:** leadership, product, ops leads  
**Primary datasource:** Prometheus

Required panels:

- active partner workspaces;
- active lane memberships;
- application submissions;
- applications under review;
- approved probation workspaces;
- active workspaces;
- first paid conversions;
- gross earnings created;
- partner payout liability;
- earnings on hold;
- refund or chargeback rate;
- active incidents by severity.

Drilldowns:

- onboarding funnel dashboard;
- finance dashboard;
- risk dashboard;
- active incidents runbook.

### 5.2 Partner Portal API Health

**Audience:** backend, SRE  
**Primary datasource:** Prometheus, Tempo, Loki

Required panels:

- request rate;
- error rate;
- p50, p95, p99 latency;
- endpoint-group latency;
- bootstrap request rate;
- bootstrap failure rate;
- auth login failures;
- permission denied count;
- realm mismatch count;
- top error codes.

Drilldowns:

- trace search by route group;
- logs by endpoint template;
- alert panels for active incidents.

### 5.3 Partner Portal Frontend UX

**Audience:** frontend, product  
**Primary datasource:** Prometheus

Required panels:

- LCP p75/p95;
- INP p75/p95;
- CLS distribution;
- TTFB distribution;
- route load latency;
- browser-side API latency;
- frontend unhandled errors;
- render errors;
- route guard blocks;
- form submit failures.

Drilldowns:

- route-group specific panels;
- release-ring comparison;
- error code breakdown.

### 5.4 Partner Onboarding Funnel

**Audience:** product, partner ops  
**Primary datasource:** Prometheus

Required panels:

- drafts created;
- submissions;
- under review;
- needs info;
- waitlisted;
- approved probation;
- active;
- rejected;
- submit conversion;
- time to first review;
- time to decision;
- evidence upload failures.

Drilldowns:

- application review ops dashboard;
- cases and notifications dashboard.

### 5.5 Partner Application Review Ops

**Audience:** partner ops, support, backend  
**Primary datasource:** Prometheus

Required panels:

- pending queue;
- under-review queue;
- needs-info backlog;
- review age p50/p95;
- SLA breaches;
- decisions by lane;
- decisions by result;
- needs-info loop rate;
- evidence upload failures;
- review-request volume.

Drilldowns:

- partner cases dashboard;
- admin partner ops dashboard.

### 5.6 Partner Codes, Tracking, And Attribution

**Audience:** growth, backend, product  
**Primary datasource:** Prometheus, Tempo

Required panels:

- codes created / activated / paused / revoked;
- tracking links created;
- QR codes generated;
- tracking clicks;
- rejected clicks;
- touchpoints recorded;
- attribution resolutions;
- no-owner rate;
- conflict rate;
- manual override count;
- attribution latency;
- conversions by owner type.

Drilldowns:

- postback and integrations dashboard;
- attribution traces;
- relevant logs.

### 5.7 Finance, Settlement, And Payouts

**Audience:** finance ops, backend, leadership  
**Primary datasource:** Prometheus, Loki

Required panels:

- earnings created;
- earnings on hold;
- earnings available;
- earnings reserved;
- clawbacks;
- holds created / released / extended;
- statements open / closed;
- statement close latency;
- payout accounts created / verified / rejected;
- payout executions and failures;
- payout liability;
- reconciliation mismatches;
- refund volume;
- dispute volume.

Drilldowns:

- finance logs by payout event;
- traces for payout execution;
- alert panels for critical finance incidents.

### 5.8 Risk, Compliance, And Governance

**Audience:** risk, compliance, partner ops  
**Primary datasource:** Prometheus, Loki

Required panels:

- risk reviews open;
- risk review age p95;
- risk review SLA breaches;
- traffic declarations submitted / approved / rejected;
- creative approvals submitted / approved / rejected;
- governance actions by type;
- policy acceptances;
- legal acceptance required backlog;
- active restrictions by lane.

Drilldowns:

- cases dashboard;
- admin partner ops dashboard;
- compliance-related logs.

### 5.9 Notifications And Cases

**Audience:** support, partner ops, backend  
**Primary datasource:** Prometheus, Loki

Required panels:

- notifications generated;
- notification delivery failures;
- unread notifications;
- action-required backlog;
- notification delivery latency;
- cases created;
- cases open;
- cases resolved;
- first response latency;
- resolution latency;
- case SLA breaches.

Drilldowns:

- logs for notification events;
- traces for async dispatch;
- admin message creation flow.

### 5.10 Integrations, Postbacks, And Exports

**Audience:** technical ops, backend, support  
**Primary datasource:** Prometheus, Tempo, Loki

Required panels:

- API tokens created;
- API token auth failures;
- postbacks sent / success / failed;
- postback latency;
- postback retries;
- postback dead-letter;
- exports requested / completed / failed;
- export latency.

Drilldowns:

- logs by integration type;
- traces for export or postback execution;
- worker queue dashboard.

### 5.11 Admin Partner Ops

**Audience:** admin ops, partner ops, finance ops, compliance  
**Primary datasource:** Prometheus, Loki

Required panels:

- admin partner actions;
- review queue open;
- review duration;
- privileged reads;
- maker-checker actions;
- audit events;
- queue age for payout review;
- queue age for application review.

Drilldowns:

- admin action logs;
- audit event stream;
- partner lifecycle dashboards.

### 5.12 Observability Pipeline

**Audience:** SRE, backend  
**Primary datasource:** Prometheus

Required panels:

- Prometheus scrape health;
- otel collector accepted / refused / dropped spans;
- Tempo ingest rate and query failures;
- Loki ingest and drop health;
- Promtail scrape errors;
- Alertmanager delivery failures;
- dashboard datasource health.

Drilldowns:

- infra dashboard;
- service dashboards;
- collector or Tempo logs.

### 5.13 Infrastructure

**Audience:** SRE, backend  
**Primary datasource:** Prometheus

Required panels:

- backend CPU and memory;
- worker CPU and memory;
- PostgreSQL availability and deadlocks;
- Redis memory and connected clients;
- container restarts;
- node CPU and memory;
- disk usage;
- throttling and OOM indicators.

Drilldowns:

- service-specific API health dashboards;
- observability pipeline dashboard.

---

## 6. Dashboard Variables By Dashboard

### 6.1 Broad Product Dashboards

Allowed variables:

- `env`
- `lane`
- `surface`
- `release_ring`

### 6.2 Engineering Dashboards

Allowed variables:

- `env`
- `service`
- `route_group`
- `endpoint_template`
- `job_name`
- `queue_name`
- `integration_type`

### 6.3 Finance And Risk Dashboards

Allowed variables:

- `env`
- `lane`
- `payment_provider`
- `payout_rail`
- `settlement_state`
- `case_type`
- `notification_type`

---

## 7. Dashboard Drilldown Rules

1. Metrics dashboards should link to Tempo traces where request or job latency matters.
2. Metrics dashboards should link to Loki logs where result reason or event narrative matters.
3. Every dashboard with active alert panels should link to runbooks.
4. No dashboard should depend on manual copy/paste of per-entity IDs as a default operating mode.

---

## 8. Provisioning Rules

Dashboards should be provisioned from the repository where possible.

Required delivery artifacts:

- dashboard JSON or source definition;
- folder placement;
- owner metadata;
- linked datasource assumptions;
- linked runbooks or alerts where relevant.

---

## 9. Acceptance Conditions

This dashboard spec is acceptable only when:

- all required dashboards have a clear audience and panel set;
- metrics dashboards are paired with trace/log drilldowns where needed;
- dashboard variables stay bounded;
- engineering and business operations can use the dashboards without inventing ad hoc views.
