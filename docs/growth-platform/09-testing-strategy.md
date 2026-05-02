# Testing Strategy

## Objective

Testing must prove that the Growth Platform is correct across surface, tenant, payment, and public-data boundaries.

## Test Layers

### Unit Tests

- pricing and attribution helpers;
- tenant context resolution;
- referral signing and verification;
- payment state transitions;
- snapshot freshness logic.

### Integration Tests

- Mini App bootstrap composition;
- payment to entitlement activation;
- partner provisioning state transitions;
- public snapshot publication flow;
- webhook handling and reconciliation.

### Contract Tests

- Mini App API contracts;
- Partner API contracts;
- Public Network API contracts;
- Telegram payment and webhook adapters.

### End-to-End Tests

- Telegram Mini App critical purchase path;
- partner application to active branded bot;
- public snapshot generation to SSR page rendering;
- stale snapshot degraded rendering behavior.

## Critical E2E Scenarios

1. User opens Mini App, pays, and gets config.
2. Partner creates bot, user buys through partner context, partner receives attributed sale.
3. Network snapshot worker publishes fresh data and public page renders it.
4. Snapshot becomes stale and UI clearly shows stale or degraded state instead of fake live status.
5. Refund occurs after entitlement activation and produces correct reversal behavior.
6. Partner suspension occurs after active bot and customer-facing behavior degrades safely.

## Security Test Areas

- invalid Telegram init data rejection;
- cross-tenant access rejection;
- unsigned or expired referral payload rejection;
- premature entitlement activation prevention;
- public data sanitization verification.

## Payment Test Areas

- quote idempotency;
- invoice creation idempotency;
- duplicate `successful_payment` event handling;
- `pre_checkout_query` validation handling;
- successful payment reconciliation;
- canceled invoice handling;
- refund-aware entitlement behavior;
- duplicate webhook resilience;
- partner ledger reversal correctness.

## Performance and Load

- Mini App bootstrap latency under realistic mobile conditions;
- public network API response under cached and uncached paths;
- provisioning queue throughput;
- analytics ingestion durability.

## Smoke Tests

Must exist for:

- Mini App bootstrap
- Stars payment status check
- public network overview
- partner workspace load
- provisioning job health

## Rollback Tests

- disable purchase while keeping Mini App readable;
- revert public network page to safe degraded mode;
- suspend a partner bot and verify customer-facing behavior;
- roll back provisioning state after partial failure;
- release and re-apply payout hold entries cleanly.

## Additional Production-Critical Scenarios

- failed provisioning rollback after partial webhook or menu binding;
- stale snapshot with last valid snapshot retained;
- public incident publication and update workflow;
- negative tenant leakage tests for partner data, payments, and configs;
- admin/operator audit trail tests.

## Environment Strategy

- local dev for contract and unit coverage;
- staging for Telegram-integrated flows where possible;
- pre-production for snapshot freshness, provisioning, and settlement rehearsals;
- production canary for partner and public rollout.
