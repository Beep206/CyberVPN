# CyberVPN PostHog Product Taxonomy And Privacy Baseline

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.4`

This document freezes the canonical product-event taxonomy, privacy rules, blocked-property list, and source-of-capture model for `PostHog` in CyberVPN.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](../plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md)

This baseline exists so later phases do not mix:

- product analytics;
- runtime observability;
- business source-of-truth state;
- feature-flag control;
- privacy-sensitive VPN telemetry.

## 1. Canonical Decisions Frozen Here

The following decisions are fixed and are not reopened by this document:

1. `PostHog self-hosted` is the canonical product analytics, product-facing feature flag, and experimentation platform.
2. `PostHog` is not the source of operational health truth.
3. `PostHog` is not the source of business source-of-truth state.
4. Critical commercial events must arrive through server-side or authoritative bridge paths.
5. CyberVPN product analytics is privacy-first because CyberVPN is a VPN platform.
6. VPN usage, browsing activity, destinations, raw traffic telemetry, secrets, and private keys are prohibited from product analytics.
7. Session replay is off by default.
8. Uncontrolled autocapture is prohibited in production posture.

## 2. Domain Separation And Current-State Mapping

The current repository already contains analytics-like surfaces, but they do not define the target-state product analytics contract.

Current-state references:

- [frontend/src/features/dev/lib/feature-flags.ts](/home/beep/projects/VPNBussiness/frontend/src/features/dev/lib/feature-flags.ts:1) is a local dev/testing override mechanism. It is not the canonical product flag system.
- [partner/src/app/api/analytics/frontend-runtime/route.ts](/home/beep/projects/VPNBussiness/partner/src/app/api/analytics/frontend-runtime/route.ts:1) is frontend runtime observability and forwarding. It is not the canonical product analytics ingestion path.

Frozen domain separation:

| Surface | Canonical role | Explicit non-role |
|---|---|---|
| `PostHog` | product analytics, product flags, experiments | runtime error monitoring, platform SLOs, secrets, business source of truth |
| `Prometheus/Grafana/Loki/Tempo/Sentry` | operational telemetry, traces, logs, runtime diagnostics | funnel analytics, feature experiments |
| `PostgreSQL` | durable transactional state | event bus, analytics warehouse |
| `NATS JetStream` | durable near-real-time event backbone | authoritative business object storage |
| `partner/src/app/api/analytics/frontend-runtime/route.ts` | runtime observability bridge | product checkout/onboarding analytics |
| `frontend/src/features/dev/lib/feature-flags.ts` | dev-only local testing flags | production product rollout system |

## 3. Canonical Product Event Families

Frozen product event families:

| Event family | Purpose | Default source class |
|---|---|---|
| `checkout_*` | checkout funnel and payment-step progression | mixed |
| `subscription_*` | lifecycle and retention milestones | server-side or NATS bridge |
| `trial_*` | trial entry and conversion analysis | mixed |
| `client_download_*` | install funnel | frontend or server-side |
| `app_*` | client first-run and onboarding completion | mixed |
| `onboarding_*` | onboarding funnel | frontend or server-side |
| `partner_*` | partner/admin product usage | mixed |
| `feature_flag_*` | flag exposure and evaluation analytics | frontend or server-side |
| `experiment_*` | experiment exposure and analysis | frontend or server-side |

Representative frozen event names:

- `checkout_started`
- `checkout_step_viewed`
- `checkout_step_completed`
- `checkout_payment_submitted`
- `checkout_payment_failed`
- `checkout_payment_captured`
- `subscription_activated`
- `subscription_renewed`
- `subscription_cancelled`
- `trial_started`
- `trial_converted`
- `client_download_started`
- `client_download_completed`
- `app_first_launch`
- `vpn_config_generated`
- `onboarding_started`
- `onboarding_step_completed`
- `partner_dashboard_viewed`
- `partner_invite_sent`
- `partner_user_activated`
- `feature_flag_evaluated`
- `experiment_exposure_recorded`

Naming rules:

1. Event names use `snake_case`.
2. Completed facts use past-tense wording where applicable.
3. Every event has one owner.
4. Every event has an allowed property list and blocked property list.
5. Every event must be attributable to one source class: `frontend_sdk`, `server_side`, or `nats_bridge`.

## 4. Source-Of-Capture Model

Frozen source classes:

| Source class | Meaning | Allowed examples |
|---|---|---|
| `frontend_sdk` | user interaction or client context that only the UI can see reliably | page/view, step visibility, onboarding interaction |
| `server_side` | authoritative backend-side commercial or lifecycle action | payment captured, subscription activated |
| `nats_bridge` | analytics consumer fed by canonical domain events via transactional outbox and NATS | subscription renewed, cancellation, payment success fanout |

Critical commercial events must not be browser-only.

### 4.1 Sample Event Matrix

This matrix is the `T0.4` approved baseline evidence for source boundaries.

| Event | Owner domain | Source class | Why |
|---|---|---|---|
| `checkout_started` | growth/product | `frontend_sdk` | user entered funnel in browser/app |
| `checkout_step_viewed` | growth/product | `frontend_sdk` | step visibility is UI-local |
| `checkout_step_completed` | growth/product | `frontend_sdk` or `server_side` | frontend for UX steps, server-side when completion depends on backend validation |
| `checkout_payment_submitted` | billing/product | `frontend_sdk` | submit intent originates in UI |
| `checkout_payment_failed` | billing | `server_side` or `nats_bridge` | authoritative failure result must come from backend/payment workflow |
| `checkout_payment_captured` | billing | `server_side` or `nats_bridge` | authoritative commercial event only |
| `subscription_activated` | billing/subscription | `server_side` or `nats_bridge` | authoritative lifecycle event only |
| `subscription_renewed` | billing/subscription | `nats_bridge` | derived from canonical lifecycle event stream |
| `subscription_cancelled` | billing/subscription | `server_side` or `nats_bridge` | authoritative lifecycle event only |
| `client_download_started` | product/growth | `frontend_sdk` | user interaction in product UI |
| `client_download_completed` | product/growth | `frontend_sdk` or `server_side` | browser/app completion signal or signed-download backend |
| `app_first_launch` | product | `server_side` or approved client SDK path | depends on client telemetry integration |
| `onboarding_started` | product | `frontend_sdk` | UX event |
| `onboarding_step_completed` | product | `frontend_sdk` | UX event |
| `partner_dashboard_viewed` | partner/product | `frontend_sdk` | UI usage event |
| `partner_user_activated` | partner/admin | `server_side` or `nats_bridge` | authoritative account state change |
| `feature_flag_evaluated` | platform/product | `frontend_sdk` or `server_side` | depends on evaluation locus |
| `experiment_exposure_recorded` | product/growth | `frontend_sdk` or `server_side` | exposure belongs near evaluation path |

## 5. Allowed Property Classes

Allowed property classes are intentionally narrow:

- anonymous or hashed user identifier;
- hashed account or tenant identifier;
- plan or tier;
- checkout step name;
- lifecycle status category;
- locale or reviewed country attribute;
- client app version;
- platform type;
- feature flag key;
- experiment key or cohort;
- high-level partner/account cohort;
- non-sensitive release ring or app surface identifier.

Rules:

1. Prefer pseudonymous identifiers over raw user identity.
2. Prefer categorical values over free-form text.
3. Product analytics properties must be schema-bound and allowlisted.
4. Free-form payload dumping into PostHog is prohibited.

## 6. Blocked Property List

The following properties or data classes are prohibited from `PostHog` unless an explicit future privacy exception is approved in writing:

- raw IP address;
- VPN destination domain;
- VPN destination IP;
- visited site or browsing history;
- traffic metadata that reveals user browsing behavior;
- connection log data that reveals user browsing behavior;
- access tokens;
- refresh tokens;
- session secrets;
- VPN configuration secrets;
- node private keys;
- private certificates or unredacted certificate material;
- payment card data;
- raw email address;
- phone number;
- support ticket message body;
- chat transcript content;
- free-form error payloads containing user content;
- request headers or cookies copied wholesale;
- stack traces containing secrets or user payload.

Rules:

1. If a property is not explicitly allowlisted, it is treated as blocked until reviewed.
2. Hashing is not a license to send new identity fields without review.
3. Runtime observability payloads must not be mirrored into PostHog by convenience.

## 7. Privacy Baseline

### 7.1 Identity Handling

Frozen privacy posture:

- distinct user/account identity should prefer stable pseudonymous identifiers;
- raw email is prohibited by default;
- raw phone number is prohibited by default;
- identity joins to internal business systems happen outside PostHog when possible.

### 7.2 Session Replay

Frozen baseline:

1. Session replay is off by default.
2. Enabling replay requires privacy review and explicit scope definition.
3. Text and form inputs must be masked by default.
4. Payment and other highly sensitive forms remain excluded unless a specific exception is approved.
5. Consent and opt-out behavior must be honored where applicable.

### 7.3 Autocapture

Frozen baseline:

1. Autocapture is off by default in production posture.
2. If enabled later, it must be allowlist-only.
3. Uncontrolled DOM text, attribute, or element capture is prohibited.

### 7.4 Runtime And Observability Boundaries

The following rule is frozen:

`partner/src/app/api/analytics/frontend-runtime/route.ts` remains an operational telemetry path, not a shortcut into PostHog.

Consequences:

1. Runtime error and route telemetry stay in observability systems.
2. Product analytics events are modeled explicitly and emitted intentionally.
3. No future team may mirror operational payloads into PostHog without a reviewed event contract.

## 8. Canonical Delivery Path For Critical Commercial Events

Critical commercial events must use the canonical authoritative path:

```text
PostgreSQL commit
  -> transactional outbox
  -> NATS JetStream
  -> analytics bridge consumer
  -> PostHog capture using event_id-based idempotency
```

Rules:

1. Browser-only delivery is prohibited for `payment`, `subscription`, and other authoritative commercial milestones.
2. Analytics bridge consumers must be idempotent.
3. Missing PostHog availability must create retry/backlog behavior, not checkout failure.

## 9. Event Contract Requirements

Every product event contract must define:

- `event_name`
- `owner`
- `purpose`
- `source_class`
- `allowed_properties`
- `blocked_properties`
- `identifier_strategy`
- `schema_reference`
- `retention_expectation`
- `privacy_review_required`

No event may be introduced in production code without this contract.

## 10. Implementation Implications For Later Phases

This document freezes these later-phase expectations:

1. PostHog SDK rollout does not start until the event taxonomy and blocked-property list are accepted.
2. Frontend teams may instrument `frontend_sdk` events only against the frozen allowlist model.
3. Backend teams must implement server-side or `nats_bridge` capture for critical commercial events.
4. Existing runtime telemetry paths remain separate and are not silently upgraded into product analytics.
