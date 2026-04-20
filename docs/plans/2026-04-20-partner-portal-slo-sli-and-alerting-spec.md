# CyberVPN Partner Portal SLO, SLI, And Alerting Spec

**Date:** 2026-04-20  
**Status:** Reliability and alerting spec  
**Purpose:** define the service-level indicators, objectives, error-budget posture, alert severity model, and routing contract for the partner platform.

---

## 1. Document Role

This document defines:

- what “healthy” means for the partner platform;
- which SLIs and SLOs are used for operational governance;
- how alerts are prioritized;
- how error budget consumption is detected;
- how alerts are routed and linked to runbooks.

---

## 2. Scope

The SLO and alerting model covers:

- partner portal APIs;
- partner auth and bootstrap;
- partner frontend UX availability;
- admin partner-ops APIs;
- async partner processing;
- finance correctness and payout safety;
- observability pipeline availability.

---

## 3. General Principles

1. Not every metric needs an alert.
2. Page-worthy alerts must map to customer or money risk, not noise.
3. Burn-rate alerts are preferred for user-facing service health.
4. Finance correctness alerts may stay threshold-based where any incident is unacceptable.
5. Alerts must route to a real owner and a runbook.
6. Alert labels must remain bounded and operationally meaningful.

---

## 4. Core SLI Inventory

### 4.1 Availability SLIs

- successful partner portal API requests;
- bootstrap success rate;
- auth login success excluding invalid credentials;
- admin partner-ops API success rate;
- partner dashboard load success.

### 4.2 Latency SLIs

- bootstrap latency;
- read API latency;
- mutation API latency;
- application submit latency;
- analytics dashboard API latency;
- export acceptance latency.

### 4.3 Async SLIs

- notification delivery latency;
- attribution resolution latency;
- postback delivery latency;
- analytics freshness;
- statement close job success;
- outbox publish lag.

### 4.4 Integrity SLIs

- payout duplicate incidents;
- reconciliation mismatches;
- negative available balance;
- unexplained earning adjustment.

---

## 5. Baseline SLO Targets

### 5.1 Availability Targets

| SLI | Target |
|---|---|
| successful partner portal API requests | 99.9% |
| bootstrap success rate | 99.9% |
| auth login success excluding bad credentials | 99.9% |
| partner dashboard load success | 99.5% |

### 5.2 Latency Targets

| Endpoint group | Target |
|---|---|
| bootstrap p95 | < 500 ms |
| read APIs p95 | < 500 ms |
| mutation APIs p95 | < 1500 ms |
| application submit p95 | < 2000 ms |
| analytics dashboard API p95 | < 2500 ms |
| export job accepted p95 | < 1000 ms |

### 5.3 Async Targets

| Process | Target |
|---|---|
| notification delivery p95 | < 60 sec |
| attribution resolution p95 | < 30 sec |
| postback delivery p95 | < 120 sec |
| analytics freshness p95 | < 5 min |
| statement close job success | 99.9% |
| outbox publish lag p95 | < 60 sec |

### 5.4 Finance Correctness Targets

| SLI | Target |
|---|---|
| payout duplicate incidents | 0 |
| unresolved critical statement reconciliation mismatch | 0 |
| negative partner available balance | 0 |
| unexplained earning adjustment | 0 |

---

## 6. Error Budget Policy

### 6.1 Error Budget Interpretation

For availability and latency SLOs:

- the platform consumes error budget when the SLI falls below target;
- sustained high burn requires engineering response;
- fast burn pages immediately;
- slow burn creates planned remediation work.

### 6.2 No-Budget Domains

The following do not use permissive error budgets:

- payout duplication;
- critical reconciliation mismatch;
- cross-realm auth leakage;
- observability data loss causing blindness during rollout;
- silent event pipeline data loss.

These are treated as direct incidents.

---

## 7. Burn-Rate Alert Policy

For user-facing service SLOs, use multi-window multi-burn alerts.

### 7.1 Page-Level Burn Alerts

Recommended pattern:

- fast window: `5m` or `15m`;
- slow window: `1h` or `6h`;
- page when both windows indicate aggressive burn.

Suggested use:

- partner API availability;
- bootstrap success;
- auth success excluding expected bad credentials.

### 7.2 Ticket / Business-Hours Burn Alerts

Recommended pattern:

- medium window: `2h`;
- long window: `24h`.

Suggested use:

- dashboard latency degradation;
- export performance degradation;
- non-critical async degradation.

---

## 8. Alert Severity Model

### 8.1 `P0`

Immediate page.

Use for:

- partner portal unavailable;
- partner auth realm leakage;
- admin token accepted by partner portal or partner token accepted by admin;
- payout duplicate detected;
- critical statement reconciliation mismatch;
- event or outbox data loss;
- database unavailable;
- Redis session store unavailable.

### 8.2 `P1`

Fast response.

Use for:

- API error budget burn;
- bootstrap failures spike;
- login failures spike;
- payout execution failures;
- notification delivery dead-letter;
- postback dead-letter;
- attribution resolution failures;
- worker queue oldest age too high;
- risk review queue stuck;
- legal acceptance flow broken.

### 8.3 `P2`

Business-hours triage.

Use for:

- application review SLA breach;
- creative approval SLA breach;
- traffic declaration backlog;
- case SLA breach;
- dashboard freshness degraded;
- export jobs failing;
- elevated refund or chargeback rate.

### 8.4 `P3`

Informational.

Use for:

- capacity approaching threshold;
- slow query trend;
- moderate queue growth;
- low-frequency retry growth;
- non-critical panel staleness.

---

## 9. Alert Routing Contract

Every alert must carry enough labels for routing and triage.

Required alert labels:

- `severity`
- `service`
- `surface`
- `environment`
- `owner_team`
- `runbook_url`

Recommended where applicable:

- `realm_type`
- `lane`
- `route_group`
- `queue_name`
- `job_name`
- `integration_type`

Forbidden alert labels:

- per-workspace identifiers;
- per-order identifiers;
- email or personal identifiers;
- session identifiers.

---

## 10. Alert Ownership

| Domain | Primary owner |
|---|---|
| partner API and auth | backend |
| partner frontend UX | frontend |
| admin partner ops | admin/backend |
| onboarding and review | partner ops + backend |
| finance and payouts | finance ops + backend |
| risk and governance | risk/compliance + backend |
| notifications and cases | platform/backend + support |
| workers and event pipeline | backend/platform |
| infra and observability stack | SRE / platform |

---

## 11. Baseline Alert Families

### 11.1 Partner API And Auth

- partner API availability burn;
- bootstrap availability burn;
- partner auth login anomaly;
- wrong-host token rejection spike;
- cross-realm denial anomaly;
- permission-denied spike after deploy.

### 11.2 Onboarding And Review

- application submission failure spike;
- review queue age breach;
- evidence upload failure spike;
- needs-info backlog growth;
- approval latency breach.

### 11.3 Commercial And Attribution

- attribution no-owner spike;
- attribution conflict spike;
- manual override spike;
- tracking click rejection spike;
- postback failure or dead-letter.

### 11.4 Finance And Settlement

- statement close failure;
- payout failure spike;
- payout duplicate risk;
- negative available balance;
- reconciliation mismatch;
- reserve/liability mismatch.

### 11.5 Compliance And Governance

- risk review queue age breach;
- traffic declaration backlog;
- creative approval backlog;
- governance action spike;
- legal acceptance backlog.

### 11.6 Notifications, Cases, And Integrations

- notification delivery failure spike;
- unread action-required backlog spike;
- case first response SLA breach;
- case resolution SLA breach;
- export failure spike;
- API token auth failure spike.

### 11.7 Pipeline And Infrastructure

- Prometheus scrape target down;
- collector refused or dropped spans;
- Tempo ingest failure;
- Loki ingest failure;
- Promtail scrape failure;
- database unavailable;
- Redis unavailable;
- host or container saturation.

---

## 12. Alert Rule Design Guidance

### 12.1 Prefer Numerator And Denominator Rules

Examples:

- errors and total requests;
- successful postbacks and all postbacks;
- cases breaching SLA and total cases.

Derive rates in PromQL or recording rules.

### 12.2 Avoid High-Noise Thresholds

Do not alert on:

- single failed export job;
- isolated validation errors;
- low-volume, non-customer-facing retries;
- dashboard panels that are informational only.

### 12.3 Require Explainability

Every page-worthy alert must allow the operator to answer:

- what broke;
- who is affected;
- which route, job, or flow is failing;
- where to drill down next;
- which runbook to execute.

---

## 13. Runbook Link Policy

All `P0` and `P1` alerts must link to a runbook.

At minimum, each runbook must include:

- scope;
- impact;
- top dashboards;
- top queries;
- top logs and traces to inspect;
- common causes;
- safe mitigations;
- escalation owner.

---

## 14. Acceptance Conditions

This SLO/SLI and alerting spec is acceptable only when:

- all major partner platform domains have at least one defined SLI;
- page-worthy alerts are clearly separated from business-hours alerts;
- finance and security incidents are treated as hard-critical;
- routing labels and runbook linkage are explicit;
- the spec can be implemented directly in Prometheus, Alertmanager, and Grafana.
