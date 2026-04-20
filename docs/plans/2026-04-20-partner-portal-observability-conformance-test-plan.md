# CyberVPN Partner Portal Observability Conformance Test Plan

**Date:** 2026-04-20  
**Status:** Conformance test plan  
**Purpose:** define how to verify that partner-platform metrics, traces, logs, dashboards, and alerts behave correctly under real and synthetic scenarios.

---

## 1. Document Role

This document is the verification layer for the observability package.

It defines:

- scenario-based checks;
- expected metrics, traces, and logs;
- synthetic failure validation;
- dashboard freshness checks;
- exit criteria for rollout readiness.

---

## 2. General Test Principles

1. Conformance checks must validate real observable outputs, not only code paths.
2. Every critical business workflow should emit observable evidence.
3. Synthetic failures must prove alerting without causing uncontrolled side effects.
4. Negative tests must confirm security and isolation signals.
5. Dashboard freshness must be validated as part of operational readiness.

---

## 3. Required Evidence Per Scenario

For each conformance scenario capture:

- scenario ID;
- trigger time window;
- expected metric names;
- expected trace/spans;
- expected structured log event names;
- expected alert result;
- evidence links or screenshots where applicable.

---

## 4. Partner Lifecycle Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-PARTNER-001` | applicant registers on partner host | auth login/register metrics, auth trace, structured auth log |
| `OBS-PARTNER-002` | email verified | email verification metric, onboarding trace, verification log |
| `OBS-PARTNER-003` | application draft saved | draft metric, draft save log, optional trace |
| `OBS-PARTNER-004` | application submitted | submission metric, submit duration metric, `partner_application.submitted` log, submit trace |
| `OBS-PARTNER-005` | admin requests more info | requested-info metric, admin action metric, notification metric, correlated trace |
| `OBS-PARTNER-006` | applicant responds with evidence | evidence upload metric, response log, related case/review trace |
| `OBS-PARTNER-007` | admin approves to probation | application decision metric, admin action metric, notification metric, bootstrap state change |
| `OBS-PARTNER-008` | partner accepts legal docs | legal acceptance metric, legal trace, legal log |
| `OBS-PARTNER-009` | partner sets payout account | payout account creation metric, finance trace, finance log |
| `OBS-PARTNER-010` | partner submits traffic declaration | declaration metric, compliance trace, compliance log |
| `OBS-PARTNER-011` | admin approves traffic declaration | approval metric, admin action metric, notification metric |
| `OBS-PARTNER-012` | partner creates or receives code | code metric, code trace, code log |
| `OBS-PARTNER-013` | attributed conversion appears | order/attribution/commissionability metrics, attribution trace, explainability log |
| `OBS-PARTNER-014` | earning enters hold | earnings and hold metrics, finance trace, hold log |
| `OBS-PARTNER-015` | statement closes | statement close metrics, finance trace, statement log |
| `OBS-PARTNER-016` | payout becomes executable and is executed | payout metrics, payout trace, payout log |

---

## 5. Negative And Security Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-AUTH-001` | partner token used on admin surface | cross-realm denial metric/log, security trace outcome |
| `OBS-AUTH-002` | admin token used on partner surface | cross-realm denial metric/log, security trace outcome |
| `OBS-AUTH-003` | customer token used on partner surface | denial metric/log, no bootstrap success |
| `OBS-AUTH-004` | wrong-host token usage | wrong-host rejection metric/log |
| `OBS-AUTH-005` | logout-all then reuse session | revocation outcome metrics/logs, denied bootstrap |
| `OBS-AUTH-006` | CSRF or origin rejection path | CSRF/CORS rejection metric/log |
| `OBS-PERM-001` | suspended partner attempts to create code | permission/governance metric, denial log |
| `OBS-PERM-002` | payout attempt without readiness | finance block metric/log |
| `OBS-PERM-003` | performance lane submits undeclared traffic expansion | compliance/governance metric/log |

---

## 6. Admin Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-ADMIN-001` | application review queue read | admin review queue metric, admin trace, admin log |
| `OBS-ADMIN-002` | lane approval action | admin action metric, lane transition metric, notification metric |
| `OBS-ADMIN-003` | code suspension | governance metric, code pause/revoke metric, partner notification |
| `OBS-ADMIN-004` | creative rejection | creative rejection metric, notification metric, compliance log |
| `OBS-ADMIN-005` | payout account verification | finance metric, admin maker-checker metric, finance log |
| `OBS-ADMIN-006` | payout maker-checker action | maker-checker metric, payout metric, audit event log |
| `OBS-ADMIN-007` | governance action applied | governance metric, partner-visible restriction metric, notification metric |
| `OBS-ADMIN-008` | audit event written | audit metric and structured audit log |

---

## 7. Async And Integration Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-ASYNC-001` | notification dispatch success | notification metric, worker metric, dispatch trace |
| `OBS-ASYNC-002` | notification dispatch failure | delivery failure metric/log, optional alert |
| `OBS-ASYNC-003` | postback success | postback success metric, delivery latency metric, integration trace |
| `OBS-ASYNC-004` | postback failure and retry | failed metric, retry metric, related logs |
| `OBS-ASYNC-005` | dead-letter event | dead-letter metric, high-severity log, alert if critical |
| `OBS-ASYNC-006` | export success | export request/completion metrics, export trace |
| `OBS-ASYNC-007` | outbox publish lag | lag metric and alert under synthetic delay |

---

## 8. Finance Integrity Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-FIN-001` | hold created | hold metric, finance log, trace |
| `OBS-FIN-002` | hold released | release metric, finance log, trace |
| `OBS-FIN-003` | statement adjustment | adjustment metric, audit-style log |
| `OBS-FIN-004` | payout failure | payout failure metric, finance log, alert if threshold exceeded |
| `OBS-FIN-005` | reconciliation mismatch synthetic test | mismatch metric, critical alert, finance log |
| `OBS-FIN-006` | negative available balance synthetic guard | integrity metric/log, critical alert |

---

## 9. Observability Pipeline Conformance Scenarios

| Scenario ID | Scenario | Expected signals |
|---|---|---|
| `OBS-PIPE-001` | Prometheus scrape target healthy | target metrics visible, panel freshness |
| `OBS-PIPE-002` | OTel collector receives spans | accepted span metric increases, traces searchable |
| `OBS-PIPE-003` | OTel collector span export failure synthetic test | refused or failed span metric increases, alert if threshold crossed |
| `OBS-PIPE-004` | Loki ingestion working | fresh structured logs searchable by service and request_id |
| `OBS-PIPE-005` | Tempo query path works | trace searchable and linked from Grafana |
| `OBS-PIPE-006` | Alertmanager delivery path works | test alert delivered to expected route |

---

## 10. Dashboard Freshness Checks

Every required dashboard must be checked for:

- panel data visible within expected time window;
- variables resolving correctly;
- no broken datasource references;
- trace/log drilldowns functional where specified;
- panels for critical metrics not stale beyond tolerated freshness.

Minimum freshness checks:

- executive overview;
- API health;
- onboarding funnel;
- finance/payouts;
- risk/compliance;
- observability pipeline.

---

## 11. Synthetic Failure Tests

Synthetic failures should be limited, reversible, and safe.

Recommended synthetic tests:

- bootstrap failure injection in non-production;
- queue lag growth in staging;
- postback target failure using test endpoint;
- export worker timeout;
- notification dispatch failure with test workspace;
- reconciliation mismatch dry-run or simulation path;
- collector export failure simulation in isolated environment.

Never use production customer or payout credentials for synthetic tests.

---

## 12. Expected Alert Outcomes

### 12.1 Must Trigger

The following classes must be proven to alert:

- cross-realm auth anomaly;
- bootstrap failure spike;
- payout failure spike;
- reconciliation mismatch;
- outbox publish lag high;
- notification delivery dead-letter;
- case SLA breach;
- observability pipeline degradation.

### 12.2 Must Not Trigger On Normal Flow

Normal successful lifecycle scenarios must not trigger:

- `P0` finance incidents;
- `P0` auth incidents;
- queue-stuck alerts;
- postback dead-letter alerts;
- false dashboard freshness alerts.

---

## 13. Required Outputs For QA And Release Readiness

The conformance process must produce:

- scenario evidence table;
- screenshots or exported dashboard evidence where relevant;
- metric query results or snapshots;
- trace screenshots or trace IDs;
- log samples with correlation fields;
- alert screenshots or Alertmanager evidence;
- pass/fail summary by scenario ID.

---

## 14. Exit Criteria

This test plan is considered satisfied only when:

- critical partner lifecycle scenarios produce the expected metrics, traces, and logs;
- negative auth and permission scenarios emit the correct denial signals;
- synthetic failure tests prove alerting paths;
- dashboards are fresh and drilldowns work;
- staging evidence is sufficient for production readiness review.
