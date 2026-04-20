# CyberVPN Partner Portal OTEL Tracing And Log Correlation Spec

**Date:** 2026-04-20  
**Status:** Tracing and logging correlation spec  
**Purpose:** define the tracing model, correlation fields, structured logging rules, and PII boundaries for the partner platform.

---

## 1. Document Role

This document defines:

- which partner-platform flows must produce traces;
- how trace context is propagated;
- how structured logs must correlate with traces and events;
- which log fields are required;
- Loki label restrictions;
- sensitive-data rules.

---

## 2. Current Stack Baseline

The repository already has:

- OTLP ingestion through `OpenTelemetry Collector`;
- Tempo as the trace store;
- Loki and Promtail as the log stack;
- Prometheus linked to Tempo and Loki in Grafana.

Current target model:

- metrics stay in Prometheus;
- traces flow through OTel Collector to Tempo;
- logs flow through Promtail to Loki;
- traces, logs, and metrics remain correlated but distinct.

---

## 3. Trace Context Policy

### 3.1 Propagation

Trace context must propagate across:

- browser request -> backend API;
- backend API -> downstream service calls;
- admin portal action -> backend mutation -> partner-visible event;
- backend mutation -> worker job;
- worker job -> notification/postback/export delivery.

### 3.2 Core Correlation Fields

At minimum, the platform should carry:

- `trace_id`
- `span_id`
- `request_id`
- `service.name`
- `surface`
- `realm_type`
- `principal_class`

`request_id` may remain useful for logs even when the full trace chain is not visible in every tool.

---

## 4. Required Partner Platform Spans

Required top-level or meaningful child spans include:

- partner login;
- session bootstrap;
- application submit;
- application resubmit;
- application withdraw;
- admin review decision;
- lane decision;
- code create or update;
- attribution resolution;
- earning creation;
- statement close;
- payout execution;
- notification generation;
- postback delivery;
- export generation;
- legal acceptance;
- traffic declaration review;
- creative approval review;
- case creation and case reply.

---

## 5. Trace Attribute Policy

### 5.1 Allowed Low-Risk Attributes

Allowed trace attributes include bounded or operationally meaningful attributes such as:

- `surface`
- `realm_type`
- `principal_class`
- `route_group`
- `endpoint_template`
- `workspace_status`
- `lane`
- `result`
- `error_code`
- `job_name`
- `queue_name`
- `integration_type`
- `notification_type`
- `case_type`
- `governance_action_type`

### 5.2 Controlled Higher-Detail Attributes

These may appear in traces if access is restricted and policy allows:

- `workspace_id`
- `order_id`
- `statement_id`
- `payout_execution_id`
- `source_event_id`

They must not be promoted into Prometheus labels or Grafana variables.

### 5.3 Forbidden Attributes

Never record in traces:

- passwords;
- raw tokens;
- session cookies;
- API secrets;
- private keys;
- full payout account details;
- payment credentials;
- unmasked personal data.

---

## 6. Structured Log Policy

Logs must be structured JSON, not ad hoc text blobs.

At minimum, logs should include:

- `timestamp`
- `level`
- `service`
- `event_name`
- `surface`
- `realm_type`
- `principal_class`
- `workspace_status` when relevant
- `lane` when relevant
- `trace_id`
- `span_id`
- `request_id`
- `result`
- `error_code` or `reason_code` when relevant

Recommended example:

```json
{
  "timestamp": "2026-04-20T12:00:00Z",
  "level": "INFO",
  "service": "backend",
  "event_name": "partner_application.submitted",
  "surface": "partner_portal",
  "realm_type": "partner",
  "principal_class": "partner_operator",
  "workspace_status": "submitted",
  "lane": "creator_affiliate",
  "trace_id": "abc123",
  "span_id": "def456",
  "request_id": "req789",
  "result": "success"
}
```

---

## 7. Loki Label Policy

### 7.1 Allowed Loki Labels

Use low-cardinality labels only:

- `env`
- `service`
- `surface`
- `level`
- `realm_type`
- `principal_class`

Conditionally allowed if tightly bounded:

- `notification_type`
- `case_type`
- `integration_type`

### 7.2 Forbidden Loki Labels

Never use as Loki labels:

- `workspace_id`
- `order_id`
- `statement_id`
- `payout_execution_id`
- `partner_code_id`
- `email`
- `session_id`
- `trace_id`
- `request_id`

These values should live in the structured log body, not in Loki labels.

---

## 8. Required Event Naming Conventions

Use consistent event names for logs and trace span naming where possible.

Recommended event families:

- `partner_application.*`
- `partner_workspace.*`
- `partner_lane.*`
- `partner_code.*`
- `partner_attribution.*`
- `partner_earning.*`
- `partner_statement.*`
- `partner_payout.*`
- `partner_notification.*`
- `partner_case.*`
- `partner_governance.*`
- `admin_partner.*`

Examples:

- `partner_application.submitted`
- `partner_application.info_requested`
- `partner_workspace.approved_probation`
- `partner_lane.approved`
- `partner_code.suspended`
- `partner_payout.execution_approved`
- `partner_governance.action_applied`

---

## 9. Cross-Surface Correlation Requirements

The observability layer must make it possible to follow these chains:

### 9.1 Applicant Lifecycle Chain

partner submit -> review request -> admin decision -> notification -> bootstrap state change

### 9.2 Finance Chain

commissionability -> earning creation -> hold/reserve -> statement close -> payout execution

### 9.3 Governance Chain

risk review -> governance action -> partner-visible restriction -> notification -> remediation

### 9.4 Support Chain

case created -> case reply -> partner notification -> resolution

### 9.5 Integration Chain

event emitted -> outbox publish -> worker pickup -> postback delivery -> retry/dead-letter

---

## 10. Admin And Partner Correlation Rules

Where admin actions affect partner-facing state:

- the admin action log must include the same correlation path as the partner-visible result;
- the partner notification or case event should include a shared source event identity;
- traces must allow the platform to connect the initiating admin action and the resulting partner-visible mutation.

---

## 11. Sensitive Data Rules

### 11.1 Allowed In Log Body Under Control

These may appear in log body when justified and access-controlled:

- `workspace_id`
- `order_id`
- `statement_id`
- `payout_execution_id`
- `source_event_id`

### 11.2 Forbidden In Logs

Never log:

- passwords;
- raw access or refresh tokens;
- raw API secrets;
- raw payment credentials;
- full payout account details;
- session cookies;
- private keys;
- unmasked personal data.

---

## 12. Required Log Examples By Domain

Required logged event families include:

- auth success/failure and cross-realm denial;
- bootstrap failure with reason;
- application submit and decision events;
- lane transitions;
- code pause or revoke;
- attribution conflict and no-owner outcomes;
- statement close outcome;
- payout execution outcome;
- notification dispatch success/failure;
- case creation and SLA breach;
- postback dead-letter;
- outbox publish failure;
- admin privileged action.

---

## 13. Acceptance Conditions

This tracing and logging spec is acceptable only when:

- required spans are defined for the core partner lifecycle;
- trace context can connect partner, admin, backend, worker, and notification flows;
- Loki labels stay low-cardinality;
- sensitive data rules are explicit;
- engineers can implement structured logs and traces without inventing ad hoc field names.
