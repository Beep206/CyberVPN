# CyberVPN Analytics And Reporting Spec

**Date:** 2026-04-17  
**Status:** Domain specification  
**Purpose:** define the canonical analytics, reporting, metric-definition, export, and alerting model for the CyberVPN partner platform.

---

## 1. Document Role

This document defines the analytical layer used by:

- finance;
- growth;
- partner management;
- risk and fraud;
- support;
- partner operators.

---

## 2. Analytical Architecture

The platform requires three analytical layers:

| Layer | Purpose |
|---|---|
| `OLTP` | operational truth for live platform state |
| `event/outbox layer` | reliable change publication and replay |
| `analytical layer` | marts, cohorts, liability analytics, partner exports |

---

## 3. Canonical Metric Definitions

The platform must maintain single definitions for:

- paid conversion;
- qualifying first payment;
- refund rate;
- chargeback rate;
- D30 paid retention;
- earnings available;
- payout liability;
- net paid orders 90d.

No team may define alternative versions of these metrics in isolation.

---

## 4. Reporting Surfaces

Required reporting surfaces:

- executive dashboard;
- partner manager dashboard;
- finance settlement dashboard;
- risk dashboard;
- storefront performance dashboard;
- partner portal reporting;
- exports and statement views.

---

## 5. Exports And Partner Reporting

Partner reporting must support:

- code-level reporting;
- storefront-level reporting;
- geo/source/creative dimensions;
- statement exports;
- payout-status exports;
- attribution explainability.

Row-level restrictions must be enforced server-side.

---

## 6. Alerts

Required alert families:

- refund spikes;
- chargeback spikes;
- abnormal registration velocity;
- postback failures;
- payout reconciliation mismatches;
- cross-realm abuse anomalies.

---

## 7. Acceptance Conditions

This spec is acceptable only when:

- metric definitions are canonical and shared;
- reporting reconciles against operational sources;
- partner reporting preserves row-level isolation;
- alerting covers payout, fraud, and attribution health.
