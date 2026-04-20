# CyberVPN Partner Platform Metric Dictionary

**Date:** 2026-04-17  
**Status:** Canonical metric baseline for `T0.2`

This dictionary freezes the minimum shared metric vocabulary for platform, finance, risk, and partner operations.

## 1. Core Commercial Metrics

| Metric | Canonical meaning |
|---|---|
| `paid_conversion` | an order that reached paid status under canonical order rules |
| `qualifying_first_payment` | the first paid order that satisfies the active qualifying policy for the program or lane |
| `net_paid_orders_90d` | count of paid orders in the last 90 days after refund and dispute policy adjustments |

## 2. Risk And Retention Metrics

| Metric | Canonical meaning |
|---|---|
| `refund_rate` | refunded commercial volume or refunded qualifying orders divided by the relevant paid base, using one declared denominator per report |
| `chargeback_rate` | canonical `payment_dispute` records with chargeback-class outcomes divided by the relevant paid base |
| `d30_paid_retention` | share of qualifying paid customers or paid subscriptions still retained at day 30 under the declared cohort definition |

## 3. Finance And Payout Metrics

| Metric | Canonical meaning |
|---|---|
| `earnings_available` | partner earnings that have cleared holds, reserves, and dispute blocks and are eligible for payout |
| `payout_liability` | total partner-facing liability not yet paid, including available, on-hold, and reserved earnings where reporting policy requires it |

## 4. Reconciliation Vocabulary

- `order_total` = committed commercial total on the order object after pricing resolution.
- `reward_total` = sum of non-cash growth reward allocations linked to the relevant reporting scope.
- `statement_total` = statement-period sum of earning events plus adjustments under statement rules.
- `payout_total` = executed payout amount tied to one or more payout instructions and executions.

## 5. Rules

1. Every dashboard, export, or reconciliation report must point to these metric names.
2. If a report uses a narrower denominator or cohort, the narrowed scope must be named explicitly without redefining the canonical metric.
3. Metrics must resolve from order-centric and statement-centric systems of record, not from mutable UI calculations.
