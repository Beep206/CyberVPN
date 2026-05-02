# CyberVPN Platform Foundation Event Taxonomy

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.2`

This document freezes the canonical event taxonomy, transport subject pattern, envelope expectations, and source-of-truth boundaries for the platform foundation program.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)

This document does not redefine durable state ownership. It freezes how platform events must be named and transported once they cross a durable publication boundary.

## 1. Canonical Object Types

### Event

An event is a fact that already happened.

Examples:

- `billing.payment.captured`
- `subscription.activated`
- `partner.growth_code.issued`
- `node.health.dpi_detected`
- `node.lifecycle.ready`

### Command

A command is a request to attempt an action. It is not proof that the action succeeded.

Examples:

- `node.command.provision_requested`
- `node.command.replace_requested`
- `partner.command.projection_rebuild_requested`

### Durable State

Durable state is the authoritative desired or observed state stored in PostgreSQL or another owning control database.

Examples:

- `subscription.status = active`
- `node_pool.desired_capacity = 10`
- `node.traffic_eligibility = eligible`

Rules:

1. Durable state remains authoritative; events are propagation artifacts, not replacements for source-of-truth state.
2. Commands may travel over NATS, but command success must still be reflected in durable state and follow-up lifecycle events.
3. Browser-facing surfaces do not become durable consumers or sources of truth.

## 2. Naming Rules

Canonical platform naming follows these rules:

1. `event_type` is lower-case and dot-separated.
2. `event_type` does not include a transport version suffix.
3. `subject` is the transport subject and must end in `.v<version>`.
4. Events describe completed facts and should use past-tense semantics.
5. Commands describe requested actions and should use `_requested` or similarly explicit naming.
6. Provider-native terminology must not become the top-level namespace for platform events.
7. The canonical top-level platform domains are frozen as:
   - `billing`
   - `subscription`
   - `partner`
   - `node`
   - `provider`
   - `analytics`
   - `system`

Examples:

- `event_type = billing.payment.captured`
- `subject = billing.payment.captured.v1`
- `event_type = node.command.provision_requested`
- `subject = node.command.provision_requested.v1`

## 3. Canonical Platform Domains And Subject Patterns

| Domain | Canonical purpose | Subject pattern examples | Durable owner |
|---|---|---|---|
| `billing` | payments, refunds, commercial money movement | `billing.payment.captured.v1`, `billing.refund.completed.v1` | billing/control DB |
| `subscription` | subscription and account lifecycle | `subscription.activated.v1`, `subscription.cancelled.v1` | billing/control DB |
| `partner` | partner-platform business events and projections | `partner.growth_code.issued.v1`, `partner.settlement.statement.generated.v1` | partner/control DB |
| `node.lifecycle` | external node provisioning, enrollment, rotation, readiness | `node.lifecycle.bootstrap_issued.v1`, `node.lifecycle.ready.v1` | Node Fleet Controller DB |
| `node.command` | fleet action requests | `node.command.provision_requested.v1`, `node.command.quarantine_requested.v1` | Node Fleet Controller DB |
| `node.health` | node health and impairment signals | `node.health.heartbeat_observed.v1`, `node.health.dpi_detected.v1` | Node Fleet Controller DB / health pipeline |
| `provider.health` | provider region, capacity, and impairment signals | `provider.health.region_impaired.v1` | Node Fleet Controller DB / provider health pipeline |
| `analytics.product` | product-intelligence bridge events | `analytics.product.checkout_started.v1`, `analytics.product.trial_converted.v1` | PostHog bridge input only |
| `system` | internal advisories and control-plane operational events | `system.control_plane.component_degraded.v1` | owning control plane |

Reserved stream-domain layout:

| Stream | Subject patterns |
|---|---|
| `BILLING_EVENTS` | `billing.*.*.v1`, `billing.*.*.*.v1` |
| `SUBSCRIPTION_EVENTS` | `subscription.*.v1`, `subscription.*.*.v1`, `account.*.v1` |
| `PARTNER_EVENTS` | `partner.*.v1`, `partner.*.*.v1`, `partner.*.*.*.v1` |
| `NODE_LIFECYCLE_EVENTS` | `node.lifecycle.*.v1`, `node.command.*.v1` |
| `NODE_HEALTH_EVENTS` | `node.health.*.v1`, `provider.health.*.v1` |
| `ANALYTICS_EVENTS` | `analytics.product.*.v1` |
| `SYSTEM_ADVISORIES` | `system.*.v1` and selected broker/system advisories |

## 4. Canonical Transport Envelope

Every durable platform event must be transportable in the following canonical envelope:

```json
{
  "event_id": "01HVZK7Q9S6Z8J4Y6X2ZKXK2B7",
  "event_type": "billing.payment.captured",
  "event_version": 1,
  "subject": "billing.payment.captured.v1",
  "source": "billing-service",
  "occurred_at": "2026-04-21T10:15:30.123Z",
  "published_at": "2026-04-21T10:15:30.456Z",
  "environment": "prod",
  "aggregate_type": "subscription",
  "aggregate_id": "sub_789",
  "correlation_id": "req_abc",
  "causation_id": "payment_webhook_xyz",
  "idempotency_key": "outbox_evt_01HVZK7Q9S6Z8J4Y6X2ZKXK2B7",
  "pii_classification": "low",
  "schema_ref": "events/billing/payment_captured/v1.json",
  "payload": {
    "plan": "premium",
    "currency": "EUR",
    "amount_cents": 999
  }
}
```

Required envelope fields:

- `event_id`
- `event_type`
- `event_version`
- `subject`
- `source`
- `occurred_at`
- `environment`
- `aggregate_type`
- `aggregate_id`
- `correlation_id`
- `idempotency_key`
- `pii_classification`
- `schema_ref`
- `payload`

Rules:

1. `published_at` is required once the event leaves the outbox and is published durably.
2. `subject` must equal `event_type + .v<event_version>`.
3. `idempotency_key` must be deterministic for the business action being propagated.
4. `schema_ref` must resolve to a version-controlled schema or documented contract path.

## 5. Existing Frozen Partner-Platform Subset

The backend already contains a frozen partner-platform event subset in:

- [backend/src/application/events/partner_platform_events.py](/home/beep/projects/VPNBussiness/backend/src/application/events/partner_platform_events.py:1)
- [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)

Those current application-level event names remain valid and must not be renamed during `Phase 0`.

Frozen current families:

- `growth_code`
- `invite`
- `referral`
- `promo`
- `gift`
- `storefront`
- `realm`
- `order`
- `attribution`
- `growth_reward`
- `settlement`
- `risk`
- `rollout`
- `entitlement`
- `service_access`
- `reporting`

Transport mapping rule for this subset:

- current application event name `growth_code.issued` maps to transport subject `partner.growth_code.issued.v1`
- current application event name `settlement.statement.generated` maps to transport subject `partner.settlement.statement.generated.v1`

This preserves current backend semantics while freezing the forward platform rule that cross-service transport belongs under the `partner` stream domain.

## 6. Current Legacy Event Shapes That Are Not Yet Canonical

The repository still contains legacy in-process event names such as:

- `user.created`
- `user.updated`
- `payment.completed`
- `server.status_changed`

Source:

- [backend/src/domain/events/base.py](/home/beep/projects/VPNBussiness/backend/src/domain/events/base.py:1)

These are not yet the canonical durable transport taxonomy for the platform foundation target state. They must either:

1. be normalized into the platform taxonomy before they become durable cross-service events; or
2. remain explicitly scoped as local in-process events only.

## 7. Delivery Mechanics Versus Business Eventing

The following are delivery mechanics, not authoritative event domains:

- Redis pub/sub channel `cybervpn:sse:events`
- direct FastAPI WebSocket broadcasts
- cron-driven notification polling

These paths may continue temporarily, but they do not define canonical event taxonomy and must not be treated as business source-of-truth channels.

## 8. Migration Notes For Later Phases

`T0.2` freezes the taxonomy. It does not require immediate implementation cutover.

Later phases must ensure:

1. business-critical state transitions flow through `transactional outbox -> NATS JetStream -> durable consumers`;
2. browser/UI live updates are fed by projection consumers plus server-side SSE/WebSocket gateways;
3. legacy delivery paths are either reimplemented downstream of NATS or explicitly retired;
4. the current `outbox_events.event_family` database column is not mistaken for final NATS stream ownership.
