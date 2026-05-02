# Security and Abuse Prevention

## Objective

Protect customer flows, partner isolation, payment integrity, and public trust surfaces before production rollout.

## Core Security Principles

1. Server-authoritative trust decisions only.
2. Tenant isolation by design.
3. Signed attribution and referral payloads.
4. Payment activation only after authoritative confirmation.
5. Public surfaces expose sanitized data only.

## Telegram Security

### initData Validation

- raw Telegram init data must be validated on the backend;
- `initDataUnsafe` must never be trusted for security-sensitive decisions;
- session creation must bind to validated Telegram identity;
- telemetry emitted by the client must never be used as security proof.

### startapp and Referral Payloads

- sign payloads with expiry;
- include partner and campaign metadata only where necessary;
- reject malformed or expired payloads;
- audit suspicious reuse.

## Partner Tenant Isolation

Controls:

- explicit tenant resolution per request;
- no implicit default tenant on partner-aware surfaces;
- repository and service layer tenant checks;
- audit logging for cross-tenant access attempts;
- test coverage for negative isolation cases.

## Payment Verification

- invoice creation is server-side;
- pre-checkout validation must be explicit and auditable;
- invoice status is reconciled from authoritative payment events;
- entitlement activation occurs only after confirmed success;
- refunds and disputes update platform state explicitly.

## Token and Credential Security

- encrypt bot tokens and payment secrets at rest;
- rotate credentials with auditable workflows;
- restrict plaintext token exposure in UI and logs;
- revoke and rebind credentials on emergency suspend.

## Webhook Security

- verify Telegram or internal webhook authenticity;
- isolate webhook handling by bot identity and tenant context;
- prevent replay where supported;
- alert on repeated invalid signatures or malformed payloads.

## Public API Controls

- rate limit public network endpoints;
- cache responses aggressively but safely;
- strip internal identifiers and topology;
- enforce public schema validation before serving.

## Trial Abuse Prevention

Signals may include:

- Telegram identity history;
- device or browser fingerprint signals;
- IP and ASN patterns;
- referral loop patterns;
- partner risk score;
- prior payment and trial history.

## White-Label Abuse Prevention

- KYB and moderation tiers;
- brand review and impersonation detection;
- bot creation limits;
- payout holds for suspicious accounts;
- emergency suspend with token revoke;
- blocked category enforcement.

## Audit Logs

Required for:

- partner provisioning actions;
- brand and commercial policy changes;
- token rotations;
- payout requests and approvals;
- cross-tenant security events;
- payment state transitions;
- admin and operator actions against partners, incidents, payouts, or refunds.

## Emergency Controls

- suspend partner workspace;
- suspend partner bot;
- disable branded Mini App binding;
- stop payouts;
- force public widget disable for a tenant;
- disable purchase while leaving read-only support access.

## Data Exposure Rules

Never expose publicly:

- internal node names;
- raw Prometheus labels;
- credential references;
- secret partner commercial terms;
- sensitive abuse or risk scoring internals.

Expose publicly only if sanitized:

- aggregated metrics;
- public incident summaries;
- public region labels;
- freshness and confidence state.
