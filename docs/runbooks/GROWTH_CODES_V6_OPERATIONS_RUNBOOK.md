# Growth Codes v6 Operations Runbook

## Scope

This runbook covers the operational gate for Growth Codes v6:

- campaign and code-set lifecycle
- checkout preview, quote reservation, checkout session and order commit
- zero-gateway internal settlement
- private catalog grants
- multi-code basket evaluation
- runtime anti-fraud checkpoints
- manual FX and managed XTR approval
- post-registration onboarding support state
- provider reconciliation, refund/reversal and rollback evidence

It is the operator companion for `docs/plans/CyberVPN_Growth_Codes_v6_Technical_Spec_RU.md`, especially the v6 release/smoke requirements in sections 37 and 38.

## Dashboards And Alerts

- Grafana dashboard: `infra/grafana/dashboards/growth-codes-v6-operations-dashboard.json`
- Prometheus rules: `infra/prometheus/rules/growth_codes_v6_alerts.yml`
- Rule file registration: `infra/prometheus/prometheus.yml`

Primary alert families:

- `GrowthCodesV6ZeroGatewayExternalProviderLeak`
- `GrowthCodesV6ReservationLeakCandidate`
- `GrowthCodesV6RiskBlockedSpike`
- `GrowthCodesV6FxApprovalAging`
- `GrowthCodesV6ProviderReconciliationMismatch`
- `GrowthCodesV6RawOnboardingIdempotencyPayloadDetected`

## Key Signals

- `cybervpn_growth_v6_zero_gateway_external_provider_requests_total`
- `cybervpn_growth_v6_reservations`
- `cybervpn_growth_v6_quote_sessions`
- `cybervpn_growth_v6_runtime_risk_decisions_total`
- `cybervpn_growth_v6_fx_pending_approval_oldest_age_seconds`
- `cybervpn_growth_v6_provider_reconciliation_mismatches_total`
- `cybervpn_growth_v6_raw_onboarding_idempotency_payload_detected`
- `growth_codes_v6:zero_gateway_external_provider_requests:increase10m`
- `growth_codes_v6:reservation_leak_candidates`
- `growth_codes_v6:risk_blocked:increase15m`
- `growth_codes_v6:manual_fx_pending_approval_oldest_age_seconds`
- `growth_codes_v6:provider_reconciliation_mismatches:increase30m`

## Release Smoke Matrix

Run this matrix in local, staging, or a release rehearsal before enabling a Growth Codes v6 campaign outside an internal allowlist.

| Check | Expected evidence | Failure action |
| --- | --- | --- |
| Preview / resolve | Code preview returns accepted/rejected/conflicted statuses without reservation rows or raw-code leakage. | Disable code input flag and inspect resolver logs. |
| Quote reservation | Quote creates one code-set reservation group with deterministic status and bounded caps. | Release reservation group and block campaign publish. |
| Checkout session | Checkout session binds quote and code-set snapshot without re-pricing drift. | Cancel checkout session and compare quote/order snapshots. |
| Zero-gateway order | Order is `pending_internal_settlement`, `gateway_amount=0`, no payment or attempt exists before payment-attempt creation. | Stop zero-gateway campaign and inspect order snapshots. |
| Internal zero attempt | Payment attempt uses `provider=internal_zero`, status `succeeded`, no invoice payload and no external provider request. | Treat as P0; check provider logs and idempotency path. |
| Benefit fulfillment | Benefits execute only after succeeded settlement and emit deterministic fulfillment/outbox records. | Pause campaign, replay idempotent fulfillment after root cause. |
| Private catalog | Hidden plan remains hidden without scoped grant; valid preflight issues short-lived grant. | Revoke grant and rotate campaign policy version if scope is wrong. |
| Runtime risk | `checkout_eval`, `reservation`, `zero_settlement`, `benefit_fulfill`, `private_preflight`, `invite_redeem` decisions are persisted when those paths run. | Fail closed for high-risk context if model/registry unavailable. |
| FX maker-checker | Configured FX and managed XTR records stay `pending_approval` until a different admin approves. | Disable manual FX provider and use last approved snapshot. |
| Reconciliation | Provider ledger, order settlement, reservations, benefits, refunds and reversals reconcile with zero mismatches. | Freeze affected campaign and run reconciliation triage. |
| Onboarding support | Admin onboarding state exposes only hash/presence flags for idempotency material. | Re-run scrub migration and inspect serializers. |

## Zero-Gateway Provider Log Proof

For every zero-gateway rehearsal:

1. Capture order id, payment id, payment attempt id and code-set id.
2. Query payment rows:
   - `provider = internal_zero`
   - `external_id = internal_zero:<order_id>`
   - `final_amount = 0`
   - `metadata.no_external_invoice = true`
3. Query payment attempt rows:
   - `provider = internal_zero`
   - `status = succeeded`
   - `invoice_id IS NULL`
   - `provider_snapshot.invoice_created = false`
4. Query provider webhook/request logs for the same correlation window.
5. Expected result: no external payment provider request, invoice, webhook or capture exists for the zero-gateway order.
6. Store only IDs, hashes and counts in evidence. Do not copy raw customer codes, tokens, cookies, provider secrets, Telegram init data or idempotency keys.

## Reconciliation Triage

When `GrowthCodesV6ProviderReconciliationMismatch` fires:

1. Freeze campaign publish/revoke actions for affected campaign ids.
2. Export redacted snapshots for:
   - order
   - payment
   - payment_attempt
   - checkout_code_sets
   - checkout_code_applications
   - growth_code_reservation_groups
   - growth_code_reservations
   - growth_benefit_fulfillments
   - growth_reversal_events
3. For zero-gateway rows, confirm no external provider ledger item exists.
4. For paid provider rows, confirm provider amount/currency/capture/refund matches immutable order/payment snapshots.
5. For refunds, confirm benefit and reservation reversal records are idempotent and linked to the refund id.
6. Resolve the mismatch by replaying the idempotent use case or by adding a manual audited reversal. Do not edit ledger rows directly.

## Runtime Risk Triage

When `GrowthCodesV6RiskBlockedSpike` fires:

1. Open Admin `Growth -> Risk`.
2. Filter decisions by action contexts:
   - `private_preflight`
   - `checkout_eval`
   - `reservation`
   - `zero_settlement`
   - `benefit_fulfill`
   - `invite_redeem`
   - `retry_reconcile`
3. Confirm each decision references approved policy/model versions.
4. Review reason codes and feature snapshots. They must contain hashed/redacted identifiers only.
5. If model registry/checksum is unavailable for a high-risk context, keep fail-closed behavior and escalate to backend owner.
6. Do not bypass risk by changing UI visibility or client-side flow.

## FX Maker-Checker Triage

When `GrowthCodesV6FxApprovalAging` fires:

1. Open Admin `Growth -> FX`.
2. Inspect configured or managed XTR rates with `status=pending_approval`.
3. Verify the creator and checker are different admins.
4. Approve through `POST /api/v3/admin/growth/fx/rates/{rate_id}/approve`.
5. Do not enable a provider to activate pending manual rates; provider enable intentionally skips `pending_approval`.
6. Confirm simulation uses only `active` rates and returns `no_rerate=true`.

## Rollback

Rollback is controlled by state, not by direct database edits:

1. Archive or pause active campaign versions through admin APIs.
2. Revoke private grants or reservations through idempotent use cases.
3. Disable manual FX provider rows if an override is suspect.
4. Re-run quote/checkouts with previous active policy version.
5. For the onboarding idempotency scrub migration, rollback does not restore raw keys by design. Use hash/presence evidence only.
6. For schema rollback in local/staging, run Alembic downgrade to the previous head, verify application startup, then re-upgrade before release.

## Evidence Capture

For release or incident handoff, capture:

- exact git commit and branch
- migration upgrade/downgrade/re-upgrade command output
- OpenAPI/generated-client drift check
- backend targeted and affected full test output
- frontend/admin/partner lint/typecheck/test/build output
- Prometheus rule validation output for `growth_codes_v6_alerts.yml`
- Grafana dashboard JSON parse validation
- redacted database rows for order/payment/payment_attempt/reservation/risk decision
- provider-log proof showing no external call for zero-gateway

Use `docs/evidence/growth-codes-v6/local-smoke-20260626.md` as the local evidence index for this implementation.
