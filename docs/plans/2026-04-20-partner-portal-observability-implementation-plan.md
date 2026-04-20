# CyberVPN Partner Portal Observability Implementation Plan

**Date:** 2026-04-20  
**Status:** Implementation plan  
**Purpose:** define the practical rollout plan for partner platform observability across backend, frontend, workers, dashboards, alerts, and conformance verification.

---

## 1. Document Role

This document turns the observability package into executable work.

It defines:

- implementation waves;
- module-level instrumentation targets;
- recording rules and dashboards to add;
- alert provisioning work;
- verification and rollout sequence.

---

## 2. Current State Summary

Already present in the repository:

- Prometheus, Alertmanager, Grafana, OTel Collector, Tempo, Loki, Promtail;
- backend Prometheus endpoint on a dedicated metrics port;
- backend OpenTelemetry tracing to OTel Collector;
- existing exporters for PostgreSQL, Redis, node, and containers;
- Grafana datasources provisioned for Prometheus, Loki, and Tempo.

Not yet closed by default:

- partner-specific business metrics;
- admin partner-ops metrics;
- frontend partner UX metrics;
- full dashboard pack;
- partner-specific alert rules;
- observability conformance tests tied to partner lifecycle.

---

## 3. Implementation Principles

1. Reuse existing stack instead of introducing parallel telemetry systems.
2. Land metric names and label policy before broad instrumentation.
3. Instrument backend and worker paths before trying to alert on them.
4. Add frontend metrics only with bounded labels and controlled aggregation.
5. Provision dashboards and alerts from repo-controlled config where practical.

---

## 4. Wave Structure

### 4.1 `OBS-01` Metrics Contract Freeze

Deliverables:

- observability and metrics spec;
- metric catalog;
- SLO/SLI and alerting spec;
- dashboard spec;
- tracing and log correlation spec;
- implementation plan;
- conformance test plan.

Exit criteria:

- all domains named;
- naming conventions frozen;
- label policy frozen;
- dashboard families agreed;
- alert severity model agreed.

### 4.2 `OBS-02` Backend Runtime Instrumentation

Scope:

- HTTP server metrics and traces validation;
- auth/session/realm metrics;
- bootstrap metrics;
- onboarding/application metrics;
- workspace/team/legal/settings metrics;
- structured logs for core partner lifecycle.

Target modules:

- auth routes;
- partner session bootstrap;
- partner application workflows;
- workspace core routes;
- route guards and permission enforcement outcomes.

Exit criteria:

- backend emits core partner runtime metrics;
- traces exist for auth, bootstrap, and onboarding;
- logs contain correlation fields.

### 4.3 `OBS-03` Commercial, Finance, Risk, And Async Instrumentation

Scope:

- codes and tracking;
- attribution;
- orders and commissionability;
- finance and settlement;
- notifications and cases;
- postbacks and exports;
- workers, outbox, and queue metrics;
- admin partner-ops actions.

Target modules:

- attribution and conversion flows;
- finance/statement/payout flows;
- compliance and governance flows;
- notification dispatch;
- export jobs;
- outbox/event consumers;
- admin partner operations surfaces.

Exit criteria:

- commercial and finance metrics land;
- critical async jobs emit duration/failure/lag metrics;
- admin actions emit partner-ops metrics and structured logs.

### 4.4 `OBS-04` Frontend Instrumentation

Scope:

- partner portal route load metrics;
- partner portal browser API latency metrics;
- Web Vitals;
- route guard blocks;
- form submit and validation failure metrics;
- frontend error capture.

Target surfaces:

- auth;
- bootstrap/home;
- application/onboarding;
- finance;
- compliance;
- notifications/cases;
- integrations.

Exit criteria:

- bounded browser metrics visible in Prometheus or the chosen ingestion bridge;
- no per-entity identifiers emitted from frontend;
- release-ring comparison possible.

### 4.5 `OBS-05` Recording Rules, Dashboards, And Alerts

Scope:

- recording rules;
- Grafana dashboards;
- Alertmanager routes;
- runbook links;
- Prometheus alert rules.

Required recording rules:

- API error rate;
- API p95 latency;
- bootstrap error rate;
- review age p95;
- attribution no-owner rate;
- postback success rate;
- reconciliation mismatch count;
- payout liability aggregate;
- case SLA breach rate;
- outbox lag percentile.

Exit criteria:

- core dashboards exist;
- critical alerts provisioned;
- alert routing labels present;
- runbook linkage works.

### 4.6 `OBS-06` Conformance And Rollout Readiness

Scope:

- synthetic scenario checks;
- observability assertions in E2E;
- dashboard freshness checks;
- failure injection where safe;
- staging evidence package.

Exit criteria:

- metrics appear for known lifecycle scenarios;
- traces and logs correlate;
- critical alerts fire under synthetic failure;
- normal flow does not generate false incident noise.

---

## 5. Backend Instrumentation Targets

### 5.1 Auth And Session

Instrument:

- login;
- refresh;
- logout;
- password reset request;
- email verification;
- MFA challenge and failure;
- wrong-host token rejection;
- cross-realm denial;
- bootstrap request and failure.

### 5.2 Onboarding And Workspace Core

Instrument:

- draft created and saved;
- submit;
- resubmit;
- withdraw;
- needs-info;
- decision issued;
- team invite flows;
- legal acceptance;
- role change;
- permission denial.

### 5.3 Commercial Flows

Instrument:

- code creation/activation/pause/revoke;
- tracking click ingestion;
- attribution resolution;
- commissionability evaluation;
- conversion classification.

### 5.4 Finance And Settlement

Instrument:

- earning creation;
- holds and reserves;
- statement close;
- statement adjustment;
- payout account create/verify/reject;
- payout instruction creation;
- payout execution and failure;
- reconciliation mismatch.

### 5.5 Compliance, Notifications, And Cases

Instrument:

- traffic declaration submit/approve/reject;
- creative approval submit/approve/reject;
- governance action applied;
- risk review open/close;
- notification generate/send/fail;
- case create/respond/resolve/SLA breach.

### 5.6 Integrations And Async

Instrument:

- API token issue and auth failure;
- postback send/retry/dead-letter;
- export request/complete/fail;
- worker job start/complete/fail;
- queue depth and age;
- outbox create/publish/fail/lag.

---

## 6. Frontend Instrumentation Targets

### 6.1 Core Partner UX

Instrument:

- route load start/finish;
- route-group-level render failure;
- browser API latency by endpoint template group;
- submit attempts and failures;
- route guard blocks;
- form validation failures.

### 6.2 Web Vitals

Collect:

- LCP;
- INP;
- CLS;
- TTFB.

### 6.3 Sampling And Aggregation

Rules:

- sample or batch where necessary to control volume;
- emit aggregated route groups, not raw full paths;
- never emit user or workspace identifiers.

---

## 7. Dashboard And Alert Provisioning Targets

### 7.1 Grafana

Provision:

- dashboard folders by audience;
- variables with bounded defaults;
- trace and log drilldowns;
- annotations for incidents or deploys where useful.

### 7.2 Prometheus

Add:

- partner-specific recording rules;
- partner-specific alert rules;
- validation that alert labels are bounded.

### 7.3 Alertmanager

Add or update:

- partner owner-team routing;
- finance and risk escalation routes;
- runbook links or templated annotations.

---

## 8. Suggested Workboard Breakdown

| Workboard | Scope |
|---|---|
| `OBS-WB-01` | metrics contract freeze and naming library |
| `OBS-WB-02` | backend auth/bootstrap/onboarding instrumentation |
| `OBS-WB-03` | backend workspace/commercial/finance instrumentation |
| `OBS-WB-04` | compliance/notifications/worker/outbox/admin instrumentation |
| `OBS-WB-05` | frontend partner portal instrumentation |
| `OBS-WB-06` | recording rules, dashboards, alerts |
| `OBS-WB-07` | conformance tests and staging readiness |

---

## 9. Dependencies

Observability implementation depends on:

- stable route groups and endpoint templates;
- stable partner/admin runtime contracts;
- accessible worker and queue metrics;
- alert routing ownership;
- staging environment with real host-to-realm mapping.

---

## 10. Rollout Order

Recommended order:

1. contract freeze;
2. backend auth/bootstrap/onboarding;
3. commercial + finance + compliance + workers;
4. frontend metrics;
5. dashboards and alerts;
6. conformance validation;
7. staging evidence;
8. production enablement.

---

## 11. Acceptance Conditions

This implementation plan is acceptable only when:

- it maps directly to actual repo modules and infrastructure;
- backend, frontend, worker, admin, and SRE work can proceed in parallel from it;
- recording rules, dashboards, and alerts are treated as first-class deliverables;
- conformance is part of the rollout plan, not an afterthought.
