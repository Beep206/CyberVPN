# Subscription Cabinet Hotfix Post-Deploy Smoke

Checked at: `2026-05-26T19:35:00Z`

Runtime tag: `main-6e0adc3e-subscription-fixes-20260526T191950Z`

Commit: `6e0adc3e`

## Scope

This smoke covers the fast production fixes for:

- trial/invite users using purchase quote instead of an invalid upgrade quote;
- customer cabinet config link visibility when service-state is still partial;
- customer-scoped API route authentication for cabinet pages;
- `.org` subscription delivery route reachability through Cloudflare.

## Local Verification Before Deploy

```text
python -m compileall -q backend/src/application/use_cases/subscriptions/upgrade_subscription.py
backend/.venv/bin/ruff check backend/src/application/use_cases/subscriptions/upgrade_subscription.py
npm --prefix frontend run test -- --run src/widgets/server-access/__tests__/server-access-model.test.ts src/widgets/subscription-cabinet/__tests__/subscription-cabinet-model.test.ts
cd frontend && npm exec eslint -- src/widgets/server-access/server-access-model.ts src/widgets/server-access/__tests__/server-access-model.test.ts src/widgets/subscription-cabinet/subscription-cabinet-model.ts src/widgets/subscription-cabinet/__tests__/subscription-cabinet-model.test.ts
git diff --check
```

Result: pass.

## Deploy Verification

```text
https://api.cyber-vpn.net/health -> 200
https://my.cyber-vpn.net/ru-RU/subscriptions -> 200
https://my.cyber-vpn.net/ru-RU/servers -> 200
https://cyber-vpn.net/ru-RU/pricing -> 200
```

Deploy evidence:

- `docs/evidence/releases/subscription-cabinet-hotfix-main-6e0adc3e-subscription-fixes-20260526T191950Z/stage1-gitlab-deploy-main-6e0adc3e-subscription-fixes-20260526T191950Z.md`

## Authenticated Customer API Smoke

The smoke used a short-lived customer access token generated inside the production backend container. Token values are intentionally not recorded.

```text
GET  /api/v1/entitlements/current -> 200
GET  /api/v1/orders/?limit=20&offset=0 -> 200
POST /api/v1/access-delivery-channels/current/service-state -> 200
GET  /api/v1/servers/ -> 200
GET  /api/v1/subscriptions/config/<customer_id> -> 200
POST /api/v1/subscriptions/current/upgrade/quote -> 200
```

Observed response contract:

```text
entitlements: status=trial, plan_code=trial
orders: list_count=0
servers: list_count=1
config: subscriptionUrl_present=true, links_count=2, isFound=true
quote: checkout quote object returned; no 400 for trial/no-paid-plan state
```

## Subscription Delivery Route

User-reported issue:

```text
Subscription URL on cyber-vpn.org timed out in a VPN client after trial activation.
```

Action taken:

- `cyber-vpn.org` apex A record was switched from DNS-only to Cloudflare-proxied.
- VPN node records remain DNS-only:
  - `de-1.cyber-vpn.org`
  - `de-1.node.cyber-vpn.org`

Verification:

```text
GET https://cyber-vpn.org/api/sub/<redacted> -> 200
HTTP version: 2
remote IP: Cloudflare edge
body size: 744 bytes
```

Reasoning:

- The subscription endpoint is HTTP(S) content delivery and is safe to route through Cloudflare.
- The VPN data-plane node records must remain DNS-only because normal Cloudflare HTTP proxy is not the VPN transport.

## Admin 2FA QR

Generated private QR file for re-enrolling the owner admin 2FA app:

```text
.private/admin-cybervpn-net-owner-2fa-qr.png
```

The QR file is intentionally kept under `.private/` and is not committed.

## Remaining Follow-Up

Multiple active subscriptions still need a dedicated cabinet model: selected subscription state should be propagated across dashboard, servers, wallet, payment history, settings and import kit views. This is larger than the fast hotfix because it changes frontend state ownership and backend selection semantics.
