# Multi-Subscription Cabinet Post-Deploy Smoke

Checked at: `2026-05-27T05:20:00Z`

Runtime tag: `main-d0695d9a-multi-subscriptions-20260527T051139Z`

Commit: `d0695d9a`

## Scope

This deploy introduced the first safe multi-subscription cabinet contract:

- customer subscription list API;
- selected subscription read model;
- selected subscription selector in the shared customer cabinet layout;
- selected entitlement snapshot on dashboard, subscriptions, servers, wallet and settings surfaces;
- write-action guard for plan/add-on changes when the selected subscription is not the backend current/default subscription.

## Local Verification Before Deploy

```text
python -m compileall -q backend/src/application/services/entitlements_service.py backend/src/application/use_cases/customer_subscriptions backend/src/presentation/api/v1/customer_subscriptions backend/src/presentation/api/v1/router.py
backend/.venv/bin/ruff check backend/src/application/services/entitlements_service.py backend/src/application/use_cases/customer_subscriptions backend/src/presentation/api/v1/customer_subscriptions backend/src/presentation/api/v1/router.py backend/tests/integration/test_customer_subscriptions.py
env REMNAWAVE_TOKEN=test-remnawave-token JWT_SECRET=test-jwt-secret-value-for-local-tests-only-123456 CRYPTOBOT_TOKEN=test-cryptobot-token backend/.venv/bin/pytest backend/tests/integration/test_customer_subscriptions.py -q --no-cov
npm --workspace frontend run lint
npm --workspace frontend run build
git diff --check
```

Result: pass.

Note: the targeted backend test was run with `--no-cov` because the repository global coverage gate is not meaningful for a single integration file. The test itself passed.

## Deploy Verification

Deploy evidence:

- `docs/evidence/releases/multi-subscription-cabinet-20260527T051139Z/stage1-gitlab-deploy-main-d0695d9a-multi-subscriptions-20260527T051139Z.md`

Public smoke:

```text
https://api.cyber-vpn.net/health -> 200
https://my.cyber-vpn.net/ru-RU/dashboard -> 200
https://my.cyber-vpn.net/ru-RU/subscriptions -> 200
https://my.cyber-vpn.net/ru-RU/settings -> 200
https://cyber-vpn.net/ru-RU/pricing -> 200
```

Runtime containers:

```text
cybervpn-backend   image=cybervpn/cybervpn-backend:main-d0695d9a-multi-subscriptions-20260527T051139Z   healthy
cybervpn-frontend  image=cybervpn/cybervpn-frontend:main-d0695d9a-multi-subscriptions-20260527T051139Z  healthy
```

## Authenticated Customer API Smoke

The smoke used a short-lived customer-scope access token generated inside the production backend container. Token values were not stored.

```text
GET /api/v1/customer-subscriptions/ -> 200
items=1 selected=True default=True
GET /api/v1/customer-subscriptions/<selected>/entitlements -> 200
entitlements_status=trial plan=trial
GET /api/v1/customer-subscriptions/<foreign-or-missing> -> 404
```

## Known Contract Limitation

The current production VPN identity is still account-scoped through `service_identities`. This batch intentionally keeps per-subscription writes guarded until a follow-up migration introduces per-subscription VPN identity/config delivery.

Follow-up stage from the plan:

- `MSUB-08`: per-subscription VPN identity/provisioning migration, selected config delivery and selected write contract.
