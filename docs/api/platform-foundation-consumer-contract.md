# CyberVPN Platform Foundation Consumer Contract

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.2`

This document freezes the minimum contract every durable consumer must satisfy before it is allowed to process canonical platform events in production.

It applies to:

- NATS JetStream durable consumers;
- outbox-fed projection consumers;
- analytics bridge consumers;
- fleet-control and health-evaluation consumers;
- notification and real-time gateway consumers when they become part of the durable event path.

It does not apply to purely local in-memory callbacks or one-off developer tooling.

## 1. Core Invariants

Every durable consumer must satisfy all of the following:

1. It has a named owner.
2. It has a declared input contract.
3. It operates under at-least-once delivery assumptions.
4. It is idempotent for every externally visible side effect.
5. It has a replay policy.
6. It has alerting and a runbook.
7. It does not become an undeclared source of truth.

Anonymous or ad-hoc production consumers are prohibited.

## 2. Canonical Consumer Contract Fields

Every consumer contract must define at least these fields:

| Field | Meaning |
|---|---|
| `consumer_name` | stable durable consumer identifier |
| `consumer_class` | projection, notification, analytics_bridge, orchestration, health_evaluator, command_handler, or other declared class |
| `owning_service` | deployed service or controller that runs the consumer |
| `owning_team` | accountable team or platform function |
| `stream` | canonical stream name |
| `filter_subjects` | subject filters or subject families this consumer receives |
| `input_schema_refs` | schema references or event families the consumer supports |
| `delivery_policy` | replay/initial positioning behavior |
| `ack_policy` | explicit ack expectations |
| `ack_wait` | timeout before unacked work is retried |
| `max_deliver` | maximum delivery attempts before terminal handling |
| `backoff` | retry backoff schedule |
| `max_ack_pending` | consumer concurrency/backpressure guard |
| `idempotency_store` | where dedupe or effect-tracking state lives |
| `idempotency_key_rule` | deterministic rule used to detect duplicate side effects |
| `side_effect_type` | projection update, outbound notification, provider API call, analytics capture, or similar |
| `source_of_truth_boundary` | authoritative state owner this consumer must not replace |
| `retry_policy` | retry and escalation behavior |
| `dlq_policy` | terminal failure policy if applicable |
| `replay_policy` | how to safely rebuild or replay from prior events |
| `alert_policy` | lag, failure, saturation, and freshness alert expectations |
| `slo` | target processing latency or freshness objective |
| `runbook_url` | operator runbook path |

Recommended additional fields:

- `pii_classification`
- `auth_domain`
- `environment_scope`
- `depends_on`
- `rollback_notes`

## 3. Contract Template

Canonical template:

```yaml
consumer_name: partner_dashboard_projection
consumer_class: projection
owning_service: realtime-gateway
owning_team: platform-backend
stream: PARTNER_EVENTS
filter_subjects:
  - partner.*.v1
input_schema_refs:
  - events/partner/growth_code_issued/v1.json
delivery_policy: all
ack_policy: explicit
ack_wait: 30s
max_deliver: 10
backoff:
  - 1s
  - 5s
  - 30s
max_ack_pending: 200
idempotency_store: postgres.partner_dashboard_projection_offsets
idempotency_key_rule: event_id
side_effect_type: read_model_projection
source_of_truth_boundary: postgres.partner_control_db
retry_policy: retry_then_alert
dlq_policy: move_to_dlq_after_max_deliver
replay_policy: full_replay_supported
alert_policy:
  lag_warning_seconds: 30
  lag_critical_seconds: 120
  failure_rate_window: 15m
slo:
  p95_end_to_end_seconds: 1
runbook_url: docs/runbooks/PARTNER_PORTAL_OBSERVABILITY_RUNBOOK.md
```

## 4. Delivery Semantics

CyberVPN durable consumers must be built for at-least-once delivery.

Production assumptions:

- duplicate delivery is normal;
- replay is normal;
- out-of-order arrival may occur across different aggregates or subject families;
- side effects may be retried after partial progress.

Forbidden assumptions:

- exactly-once side effects without explicit idempotency state;
- hidden reliance on ephemeral in-memory dedupe only;
- consumers that require operator memory to know whether replay is safe.

## 5. Idempotency Rules

Every business-critical consumer must define a deterministic idempotency key.

Examples:

| Consumer class | Example key |
|---|---|
| notification | `event_id + channel + recipient` |
| projection | `event_id` or `aggregate_id + version` |
| analytics bridge | `event_id` |
| fleet command handler | `operation_run_id` |
| webhook fanout | `event_id + endpoint_id` |

Rules:

1. Idempotency storage must be durable for business-critical consumers.
2. Redis-only dedupe is insufficient when replay or crash recovery would re-trigger the same side effect.
3. Consumers that mutate provider-side state must persist enough correlation data to prove duplicate suppression.

## 6. Replay Rules

Every durable consumer must choose and document one of the following replay models:

- `full_replay_supported`
- `replay_with_compaction`
- `replay_requires_snapshot_seed`
- `replay_not_supported_without_manual_procedure`

If replay is not full and safe by design, the contract must document:

- what authoritative state must seed recovery;
- how the replay window is bounded;
- who approves replay execution;
- what monitoring confirms completion.

## 7. Alerting And Operational Baseline

Every durable consumer must have alerts for at least:

- lag or freshness breach;
- repeated failure or poison-message loop;
- saturation or max-ack-pending pressure;
- inability to publish downstream side effects where relevant.

Minimum operational references:

- owner/team
- dashboard path or dashboard UID
- runbook path
- escalation policy

## 8. Current Baseline Consumers Already Present

The current backend already declares two outbox consumer keys:

- `analytics_mart`
- `operational_replay`

Source:

- [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)

These consumers are the current durable baseline and must be treated as first-class owned consumers, not as anonymous implementation details.

## 9. Current Delivery Paths That Do Not Yet Satisfy This Contract

The following repository paths are currently delivery mechanics or transient listeners, not durable governed consumers:

- [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)
- [backend/src/application/events/handlers/notification_handler.py](/home/beep/projects/VPNBussiness/backend/src/application/events/handlers/notification_handler.py:1)
- [backend/src/application/use_cases/webhooks/remnawave_webhook.py](/home/beep/projects/VPNBussiness/backend/src/application/use_cases/webhooks/remnawave_webhook.py:1)
- [backend/src/infrastructure/messaging/websocket_manager.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/messaging/websocket_manager.py:1)

These flows do not yet satisfy the full durable consumer contract because they currently lack one or more of:

- durable ownership declaration;
- replay model;
- idempotency model;
- backlog visibility;
- stream/subject governance.

## 10. Policy Rules For Later Phases

1. No future production durable consumer may be introduced without a written contract matching this baseline.
2. UI-facing real-time delivery may remain transient, but only downstream of a durable projection or durable event boundary for business-critical facts.
3. Product analytics bridge consumers must follow this contract even if PostHog ingestion itself is best-effort and non-blocking.
4. Node Fleet Controller consumers are not exempt; command handlers, health evaluators, and traffic-eligibility handlers all require contracts.
