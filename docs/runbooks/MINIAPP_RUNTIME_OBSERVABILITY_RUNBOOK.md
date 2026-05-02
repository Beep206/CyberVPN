# Mini App Runtime Observability Runbook

## Scope

This runbook covers customer-facing Telegram Mini App runtime incidents across:

- bootstrap
- offers and checkout quote
- checkout commit
- payment status lookup
- config delivery

Primary dashboard:

- Grafana: `/d/cybervpn-miniapp-runtime/cybervpn-miniapp-runtime`

Related dashboards:

- Telegram native login: `/d/cybervpn-telegram-native-login/cybervpn-telegram-native-login`
- Task worker: `/d/cybervpn-worker/cybervpn-worker`

## Primary Signals

Prometheus metrics:

- `miniapp_runtime_requests_total`
- `miniapp_runtime_request_duration_seconds`
- `miniapp_checkout_commits_total`
- `miniapp_payment_status_checks_total`
- `miniapp_config_delivery_total`

Alert rules:

- `MiniAppBootstrapFailureRateHigh`
- `MiniAppCheckoutCommitErrorsHigh`
- `MiniAppPaymentStatusLookupFailuresSpike`
- `MiniAppConfigDeliveryFailuresHigh`
- `MiniAppRuntimeLatencyHigh`

## Triage Order

1. Confirm whether the issue is isolated to one endpoint or affects the whole Mini App path.
2. Check whether failures are `client_error`, `not_found`, or `server_error`.
3. Compare backend Mini App metrics with worker/runtime dependencies:
   - Telegram Stars flow
   - payment reconciliation
   - Remnawave config generation
4. Confirm whether the issue is surface-specific or auth-related by checking Telegram native login metrics.
5. If user impact is active, freeze risky rollout activity before deeper remediation.

## Bootstrap Incidents

Symptoms:

- bootstrap failure ratio rises
- bootstrap latency alert fires
- home screen fails before plans/config are visible

Checks:

- inspect `miniapp_runtime_requests_total{endpoint="bootstrap"}`
- inspect `miniapp_runtime_request_duration_seconds` for `endpoint="bootstrap"`
- confirm mobile user lookup, wallet lookup, entitlement lookup, and referral lookup latency
- verify Telegram-linked user exists and auth session is valid

Likely causes:

- auth/session drift
- wallet or entitlement dependency degradation
- slow DB path
- missing Telegram-linked user state

## Checkout Commit Incidents

Symptoms:

- checkout commit error ratio rises
- users open checkout but payment path fails before or during invoice creation

Checks:

- inspect `miniapp_checkout_commits_total`
- split by `flow`, `payment_rail`, and `status`
- compare `telegram_stars_xtr` against `generic_checkout`
- inspect bot/payment reconciliation dashboards if Stars commits are stuck in `pending`

Likely causes:

- quote/commit mismatch
- Telegram Stars invoice creation failure
- wallet/precondition failure
- provider or reconciliation lag

Immediate mitigation:

- keep checkout available only on the healthy payment rail if the failure is rail-specific
- if necessary, disable risky campaign traffic until commit error ratio drops

## Payment Status Lookup Incidents

Symptoms:

- repeated pending state in Mini App
- payment status lookup failures spike
- users report paid invoice but no post-payment access

Checks:

- inspect `miniapp_runtime_requests_total{endpoint="payment_status"}`
- inspect `miniapp_payment_status_checks_total`
- compare lookup volume with worker reconciliation metrics
- inspect Telegram Stars reconciliation freshness and worker failures

Likely causes:

- delayed authoritative payment confirmation
- scoping mismatch on payment ownership
- stale reconciliation worker
- provider callback/reconciliation drift

## Config Delivery Incidents

Symptoms:

- users complete payment/trial but cannot retrieve config
- config delivery failure ratio rises

Checks:

- inspect `miniapp_config_delivery_total`
- split by `source`:
  - `remnawave_generated`
  - `legacy_subscription_url`
  - `unknown`
- inspect Remnawave health and config generation path
- verify Telegram-linked user can be resolved to provisioning/config source

Likely causes:

- Remnawave generation failure
- missing subscription linkage
- fallback data absent
- post-payment entitlement not yet visible

Immediate mitigation:

- if Remnawave path is degraded but fallback exists, preserve fallback
- if both sources fail, pause customer-facing rollout and route support to `/paysupport`

## Latency Incidents

Symptoms:

- `MiniAppRuntimeLatencyHigh` fires
- UX remains available but Telegram flow feels slow

Checks:

- inspect `miniapp_runtime_request_duration_seconds` by endpoint
- confirm whether latency is concentrated in:
  - bootstrap
  - checkout quote
  - checkout commit
  - config
- compare with DB and external dependency dashboards

Likely causes:

- slow DB reads
- external provider slowness
- Remnawave latency
- accidental fan-out/regression in Mini App path

## Escalation

Escalate to:

- Backend on-call for bootstrap/checkout/config failures
- Payments owner for checkout commit or payment status incidents
- Worker/platform owner if reconciliation freshness or publish jobs are stale
- Support operations if paid users are blocked from config access

## Exit Criteria

Incident can be closed when:

- alert has cleared
- endpoint success ratio and latency returned to baseline
- no active user reports remain for the same symptom cluster
- mitigation or permanent fix is documented in the incident thread
