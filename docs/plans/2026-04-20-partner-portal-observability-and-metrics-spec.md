# CyberVPN Partner Portal Observability And Metrics Spec

**Date:** 2026-04-20  
**Status:** Observability architecture spec  
**Purpose:** define the canonical observability model for the CyberVPN partner platform across partner portal, admin portal, backend services, workers, and infrastructure.

---

## 1. Document Role

This document fixes the observability architecture and signal policy for the partner platform.

It defines:

- what we observe;
- why we observe it;
- which signals belong in metrics, traces, logs, or analytics;
- naming and label policy;
- cardinality boundaries;
- the canonical stack for dashboards and alerting.

It does not replace:

- product requirements for the partner portal;
- backend DTO/API contract specs;
- finance or risk domain rules;
- product analytics or BI reporting definitions.

---

## 2. Observability Goals

The partner platform observability layer must answer five questions:

1. Is the platform available and responsive for partner operators and admin operators?
2. Is the partner lifecycle progressing correctly from application to activation and payout?
3. Are finance, compliance, governance, and notification flows working correctly?
4. Can teams explain failures, restrictions, and anomalies quickly?
5. Can we prove correctness and operational safety before and after rollout?

---

## 3. Scope

This package covers:

- partner portal frontend;
- admin portal partner-ops surfaces;
- backend partner APIs and auth/runtime bootstrap;
- workers and asynchronous jobs;
- outbox/event pipeline;
- integrations and postbacks;
- finance and settlement flows;
- compliance, governance, and notification flows;
- infrastructure and observability pipeline health.

---

## 4. Real Stack Baseline

The current repository already contains the observability foundation:

- `Prometheus` as the primary metrics system;
- `Alertmanager` for alert routing;
- `Grafana` for dashboards and drilldowns;
- `OpenTelemetry Collector` for OTLP ingestion;
- `Tempo` for tracing and trace-derived metrics;
- `Loki` and `Promtail` for structured logs;
- `postgres-exporter`, `redis-exporter`, `node-exporter`, `cadvisor` for infra signals.

Current implementation posture:

- Prometheus scrapes backend, worker, telegram bot, helix services, exporters, and otel collector;
- Grafana datasources for `Prometheus`, `Loki`, and `Tempo` are already provisioned;
- Tempo metrics generator remote-writes span-derived metrics back into Prometheus;
- backend tracing is already wired to the OTel collector;
- backend exposes a dedicated internal metrics port.

This means the observability package is not a greenfield design. It is a contract and completion layer on top of an existing stack.

---

## 5. Signal Classes

The platform uses four complementary signal classes.

### 5.1 Metrics

Metrics are the primary source for:

- SLOs and SLIs;
- dashboards;
- alerting;
- queue health;
- business-operational counts and latency trends;
- infrastructure saturation.

Prometheus is the canonical source of truth for operational metrics.

### 5.2 Traces

Traces are the primary source for:

- request path inspection;
- partner action to backend mutation correlation;
- admin-to-partner workflow correlation;
- latency decomposition;
- downstream dependency debugging.

Tempo is the canonical trace store.

### 5.3 Logs

Structured logs are the primary source for:

- event narratives;
- audit-adjacent operational context;
- payload validation failures;
- non-metric business detail;
- deep incident investigation.

Loki is the canonical operational log store.

### 5.4 Analytics / Reporting

The analytics/reporting layer remains separate from observability.

It is used for:

- long-horizon business analysis;
- partner economics;
- per-order or per-code drilldowns;
- warehouse-style reporting;
- product analytics.

It must not be substituted by Prometheus.

---

## 6. Domain Coverage

Observability must cover all of the following domains:

1. backend API health;
2. frontend UX health;
3. auth, realm, session, and bootstrap;
4. application and onboarding;
5. workspace profile, team, and RBAC;
6. programs and lane memberships;
7. codes, links, QR, and tracking;
8. attribution;
9. orders, conversions, and commissionability;
10. growth rewards;
11. finance, settlement, and payouts;
12. refunds, disputes, and chargebacks;
13. compliance, risk, and governance;
14. notifications, inbox, and cases;
15. integrations, postbacks, and exports;
16. admin partner operations;
17. workers, queues, and outbox/event pipeline;
18. infrastructure and observability pipeline health.

---

## 7. Core Methodology

The base SRE frame for user-facing services is:

- latency;
- traffic;
- errors;
- saturation.

This applies to:

- partner backend APIs;
- partner bootstrap;
- auth/session flows;
- admin partner-ops APIs;
- workers and queues where saturation matters.

Business and operational metrics are layered on top of this base.

---

## 8. Metric Namespace Policy

### 8.1 Custom Domain Metrics

Partner platform domain metrics must use:

- `cybervpn_partner_*` for partner-facing and shared partner domain metrics;
- `cybervpn_admin_partner_*` for admin partner-ops specific metrics.

Examples:

- `cybervpn_partner_application_submissions_total`
- `cybervpn_partner_statement_close_duration_seconds`
- `cybervpn_partner_notifications_generated_total`
- `cybervpn_admin_partner_actions_total`

### 8.2 Standard HTTP / Runtime Metrics

Where standard OpenTelemetry or service metrics already exist, keep conventional names instead of inventing parallel custom names.

Examples:

- HTTP server request metrics;
- HTTP client request metrics;
- otel collector telemetry;
- exporter-native metrics.

### 8.3 Units And Suffixes

Metric names must include semantic units where appropriate:

- `_seconds`
- `_bytes`
- `_usd`
- `_total`
- `_ratio` only for derived or controlled use

Counters should normally end with `_total`.

---

## 9. Label Policy

### 9.1 Allowed Labels

The default bounded label set is:

- `env`
- `service`
- `surface`
- `realm_type`
- `principal_class`
- `role`
- `permission_key`
- `route_group`
- `endpoint_template`
- `method`
- `status_class`
- `error_code`
- `reason`
- `reason_code`
- `review_level`
- `decision`
- `from_status`
- `to_status`
- `workspace_status`
- `lane`
- `program_type`
- `code_type`
- `owner_type`
- `owner_source`
- `touchpoint_type`
- `event_type`
- `settlement_state`
- `payout_state`
- `payment_provider`
- `payout_rail`
- `currency`
- `maker_checker_state`
- `admin_action_type`
- `object_type`
- `risk_review_type`
- `governance_action_type`
- `declaration_type`
- `creative_type`
- `severity`
- `notification_type`
- `recipient_scope`
- `case_type`
- `case_priority`
- `integration_type`
- `target_service`
- `job_name`
- `queue_name`
- `consumer_name`
- `form_name`
- `blocked_reason`
- `failure_reason`
- `result`

### 9.2 Conditionally Allowed Labels

Use only where bounded by controlled enum or small inventory:

- `storefront_id`
- `merchant_profile_id`
- `release_ring`
- `region`
- `geo_bucket`

### 9.3 Forbidden Metric Labels

The following values must never appear as Prometheus labels:

- `user_id`
- `partner_account_id`
- `workspace_id`
- `partner_code_id`
- `order_id`
- `payment_id`
- `statement_id`
- `payout_execution_id`
- `email`
- `telegram_id`
- `ip_address`
- `session_id`
- `trace_id`

These identifiers may exist in:

- traces as attributes where policy allows;
- structured log bodies;
- analytics/reporting stores;
- admin drilldown APIs.

They must not be metric labels.

---

## 10. Cardinality Policy

### 10.1 Principle

Metrics are for bounded dimensions and alertable aggregates, not per-entity inspection.

### 10.2 Explicit Rules

Do not create:

- one time series per workspace;
- one time series per code;
- one time series per order;
- one time series per payout execution;
- one time series per notification thread;
- one time series per admin actor.

### 10.3 Where Detail Belongs

Use:

- Prometheus for aggregates and trend detection;
- Tempo for trace-level execution paths;
- Loki for structured event detail;
- reporting APIs or warehouse for per-entity analysis.

---

## 11. Metric Type Policy

| Use case | Required type |
|---|---|
| event count | counter |
| current queue size or backlog | gauge |
| latency or duration | histogram |
| payload size | histogram |
| long-running job duration | histogram |
| current liability or outstanding amount | gauge |
| ratio or percentage | derived query / recording rule by default |

Rules:

- count the numerator and denominator separately;
- compute ratios in PromQL or recording rules where possible;
- do not create duplicate raw ratios unless there is a clear external reason.

---

## 12. Metrics Vs Traces Vs Logs Vs Analytics

### 12.1 Put In Metrics

Use metrics for:

- request counts and latency;
- queue depth and lag;
- counts of submissions, approvals, failures, or transitions;
- unread notification backlog;
- payout liability;
- statements open/closed;
- risk review backlog;
- postback success rate inputs.

### 12.2 Put In Traces

Use traces for:

- login;
- bootstrap;
- application submit;
- admin review decision;
- payout execution;
- notification generation;
- export generation;
- postback delivery;
- cross-service latency chains.

### 12.3 Put In Logs

Use structured logs for:

- decision reasons;
- validation errors;
- evidence upload failures;
- governance context;
- admin action narratives;
- payout execution result detail;
- correlation fields.

### 12.4 Put In Analytics / Reporting

Use analytics/reporting stores for:

- per-order explainability;
- per-code performance;
- per-workspace drilldowns;
- partner economics by entity;
- payout and statement detail history beyond operational aggregate use.

---

## 13. Frontend Observability Policy

Frontend observability is required because the partner portal is an operational tool, not a marketing page.

Frontend signals must cover:

- route load latency;
- browser-side API call latency;
- route guard blocks;
- form submit attempts and failures;
- render and unhandled errors;
- Web Vitals:
  - LCP
  - INP
  - CLS
  - TTFB

Frontend labels must stay bounded:

- `surface`
- `route_group`
- `workspace_status`
- `lane`
- `result`
- `error_code`

Do not emit:

- full URL with identifiers;
- query strings;
- email or personal identifiers;
- workspace identifiers.

---

## 14. Finance And Risk Observability Policy

Finance and risk signals are treated as first-class observability concerns.

The following require direct metrics, dashboards, and alerts:

- holds;
- reserves;
- available earnings;
- payout liability;
- statement close duration;
- payout failures;
- reconciliation mismatches;
- risk review backlog;
- governance action spikes;
- legal acceptance backlog;
- notification delivery failures for finance or risk tasks.

Critical rule:

finance correctness is not optional telemetry. It is release-blocking observability.

---

## 15. Observability Pipeline Health

The observability package must monitor the observability stack itself:

- Prometheus scrape health;
- otel collector accepted/refused/dropped spans;
- Tempo ingestion and query health;
- Loki ingest/drop health;
- Promtail scrape health;
- exporter health;
- Alertmanager delivery failures.

No service is considered fully observable if the telemetry pipeline is unhealthy.

---

## 16. Alerting Principles

1. Alerts must map to a runbook or escalation path.
2. Severity labels must be consistent and bounded.
3. SLO burn-rate alerts are preferred over raw threshold spam for service health.
4. Business-critical integrity alerts may remain hard-threshold based.
5. Alerts must not depend on high-cardinality labels.
6. Alert routing must remain understandable by on-call and business operations teams.

---

## 17. Dashboard Principles

Dashboards must be separated by audience:

- executive and product;
- partner ops;
- finance ops;
- risk and compliance;
- support;
- engineering and SRE.

Every dashboard should prefer:

- bounded variables;
- drilldown to logs and traces;
- clearly named panels;
- panel links to alerts or runbooks where applicable.

---

## 18. PII And Sensitive Data Rules

Observability must never expose:

- passwords;
- raw tokens;
- API secrets;
- session cookies;
- full payout account details;
- raw payment credentials;
- unmasked personal data;
- private keys.

Identifiers that are operationally useful must remain in:

- trace attributes only where policy allows;
- structured log bodies;
- controlled admin or reporting surfaces.

They must not leak into labels, public dashboards, or unaudited exports.

---

## 19. Required Deliverables Of This Package

This observability package is complete only when the following companion documents exist:

1. metric catalog;
2. SLO/SLI and alerting spec;
3. Grafana dashboard spec;
4. OTEL tracing and log correlation spec;
5. implementation plan;
6. observability conformance test plan.

---

## 20. Acceptance Conditions

This spec is acceptable only when:

- Prometheus remains the canonical operational metrics source;
- OTel tracing is defined as the canonical trace path;
- logs, traces, metrics, and analytics responsibilities are separated clearly;
- label and cardinality rules are explicit;
- partner, admin, finance, risk, and infrastructure domains are all covered;
- the companion observability package is sufficient to move directly into implementation.
