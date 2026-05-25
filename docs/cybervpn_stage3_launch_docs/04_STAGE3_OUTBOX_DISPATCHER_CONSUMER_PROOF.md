# Stage 3 Outbox Dispatcher And Consumer Proof

**Stage:** `S3-STAGE-04`
**Status:** Passed for local/non-production proof
**Date:** 2026-05-24
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-03: Non-Prod Event Backbone Topology`

---

## 1. Назначение

Этот документ фиксирует proof для пути:

```text
PostgreSQL transactional outbox
-> backend dispatcher
-> NATS JetStream
-> durable consumers
-> consumer receipts / operational projection
```

Цель этапа: доказать, что S3 partner/reseller platform не будет зависеть от ручной очистки `outbox_events`, direct publish из request handler или silent-loss поведения при отказе broker.

Production partner event backbone после этого этапа остаётся выключенным. Этот proof разрешает двигаться к partner portal disabled-state boundary, но не разрешает включать real partner webhooks, payouts или public partner access.

---

## 2. Решение

Для S3 утверждён следующий runtime contract:

```text
OUTBOX_SOURCE_OF_TRUTH=PostgreSQL
BROKER_TARGET=NATS_JETSTREAM
STREAM=PARTNER_EVENTS
SUBJECT_PREFIX=partner
PRODUCTION_PARTNER_EVENT_BACKBONE_ENABLED=false
```

Business-critical события должны создаваться через transactional outbox в той же DB-транзакции, где меняется source-of-truth состояние. Dispatcher публикует только committed outbox publications.

---

## 3. Реализованный Контракт Dispatcher

### 3.1 Publication Lifecycle

Проверенный lifecycle:

```text
pending -> claimed -> submitted -> published
```

Для poison/broker-failure сценария:

```text
pending -> claimed -> submitted -> dead_letter
event_status -> failed
```

### 3.2 NATS Publish Contract

Каждая publication отправляется в JetStream с:

| Field | Contract |
|---|---|
| `stream` | `PARTNER_EVENTS` |
| `subject` | `partner.<consumer_key>.<event_name>.v<schema_version>` |
| `Nats-Msg-Id` header | `<consumer_key>:<event_key>` |
| `idempotency_key` | `<consumer_key>:<event_key>` |
| publish metadata | `broker_sequence`, `duplicate`, `event_version`, `published_at` |

`Nats-Msg-Id` нужен, чтобы broker-level duplicate window не создавал вторую publication при повторной отправке того же сообщения.

### 3.3 Consumer Contract

Проверенные consumers:

| Consumer | Purpose | Proof |
|---|---|---|
| `analytics_mart` | analytics/reporting consumer path | consumer receipt persisted |
| `analytics_mart.transport` | PostHog/analytics transport wrapper | disabled receipt persisted when `POSTHOG_ENABLED=false` |
| `operational_replay` | support/replay/workspace feed projection | receipt and workspace feed event persisted |

Повторная обработка того же payload не должна создавать повторный receipt или повторный workspace feed event.

---

## 4. Code Changes

| Area | Change |
|---|---|
| `OutboxPublicationStatus` | Added `dead_letter` terminal publication state. |
| Settings | Added `outbox_dispatch_dead_letter_after_attempts`. |
| Outbox repository | Claimed publications are refetched with `outbox_event` eager-loaded before dispatch. |
| Outbox repository | Added `mark_publication_dead_letter()`. |
| Event status refresh | `failed` and `dead_letter` publication terminal states now drive failed event status. |
| NATS runtime | Publish uses explicit JetStream stream and `Nats-Msg-Id`. |
| NATS runtime | Publish metadata is persisted into `publication_payload`. |
| NATS runtime | Success/failure/lag metrics and structured logs are recorded. |
| Partner lab | Added disposable PostgreSQL service for real DB-backed proof. |
| Proof tooling | Added repeatable outbox dispatcher and consumer proof script. |

Important blocker found and fixed:

```text
OutboxPublicationModel.outbox_event was unavailable under lazy='raise' during dispatch.
```

The repository now refetches claimed publications with `selectinload(OutboxPublicationModel.outbox_event)`, so dispatcher code can build the NATS envelope from the real persisted outbox event.

---

## 5. Evidence

Authoritative evidence directory:

```text
docs/evidence/partner-platform/stage3-outbox-20260524T170000Z
```

Proof command:

```bash
STAGE3_OUTBOX_EVIDENCE_DIR=docs/evidence/partner-platform/stage3-outbox-20260524T170000Z \
  bash scripts/partner/run-stage3-outbox-dispatcher-proof.sh
```

Key files:

| File | Proof |
|---|---|
| `summary.json` | Overall proof result. |
| `db-after-append.json` | Event and publication rows created through transactional outbox. |
| `db-after-dispatch.json` | Publications reached `published` with broker metadata. |
| `consumed-payloads.json` | Durable consumers fetched real JetStream payloads. |
| `consumer-receipts.json` | Consumer receipt rows persisted. |
| `workspace-feed-events.json` | Operational replay projection persisted. |
| `duplicate-idempotency-proof.json` | Duplicate delivery did not double-apply side effects. |
| `dead-letter-proof.json` | Synthetic broker failure produced `dead_letter`. |
| `backlog-alert-input.json` | Pending publication backlog input captured for alert rules. |
| `metrics-proof.json` | Prometheus samples captured for created/published/failure/lag metrics. |
| `nats-jsz-after.json` | JetStream stream and consumer state after proof. |
| `compose.config.yml` | Rendered local lab topology with secrets redacted. |
| `checksums.sha256` | Evidence checksums. |

Observed proof summary:

```text
status=ok
successful_event_status=published
published_publications=2
consumer_receipts=3
duplicate_delivery_idempotent=true
dead_letter_publications=1
backlog_pending_publications=1
metrics_samples=52
containers_after_smoke=stopped
volumes_after_smoke=removed
network_after_smoke=removed
```

---

## 6. Exit Criteria Check

| Exit Criteria | Result |
|---|---|
| At least one partner/growth event passed full outbox -> broker -> consumer path | Passed: `entitlement.grant.activated`. |
| Dispatcher lifecycle proven | Passed: `pending -> claimed -> submitted -> published`. |
| Consumer receipt persisted | Passed: 3 receipts. |
| Duplicate delivery is idempotent | Passed. |
| Broker failure does not silently lose event | Passed: synthetic failure became `dead_letter`. |
| Alert input sees backlog | Passed: pending publication captured in `backlog-alert-input.json`. |
| Metrics exist for created/published/failure/lag | Passed: 52 labeled Prometheus samples captured. |
| Production remains disabled | Passed. |

---

## 7. Production Boundary

After this stage, production must remain:

```text
PARTNER_EVENT_BACKBONE_ENABLED=false
PARTNER_WEBHOOKS_ENABLED=false
PARTNER_PAYOUTS_ENABLED=false
PARTNER_PORTAL_ENABLED=false
```

Allowed after this stage:

1. Continue to `S3-STAGE-05`.
2. Build partner portal surfaces behind disabled-state gates.
3. Keep testing event backbone in local/non-prod lab.
4. Use the outbox dispatcher code path as the basis for later staging proof.

Not allowed after this stage:

1. Enable production partner event fan-out.
2. Enable partner payouts.
3. Enable external partner webhook delivery.
4. Treat this local proof as full production event-backbone readiness.

---

## 8. Next Stage

Proceed to:

```text
S3-STAGE-05: Partner Portal Disabled-State Boundary
```

Before any production partner activation, repeat this proof against the selected real staging topology and connect alert delivery to the live observability stack.
