# MSUB-08 Selected Subscription Service Identity Evidence

Date: `2026-05-27`

## Scope

MSUB-08 closes the selected-subscription runtime gap for customer cabinet flows:

- each entitlement grant/trial can have its own subscription-scoped VPN identity;
- selected subscription config/service-state endpoints no longer depend on account-wide `current`;
- selected subscription upgrade and add-on checkout writes target the chosen grant;
- dashboard/server/subscription cabinet frontend calls use the selected subscription key.

## Local Verification

Executed from repo root before deploy:

```text
cd backend && uv run ruff check src/application/use_cases/customer_subscriptions src/application/use_cases/payments/post_payment.py src/presentation/api/v1/customer_subscriptions src/presentation/api/v1/service_identities src/infrastructure/database/repositories/service_access_repo.py src/infrastructure/database/models/service_identity_model.py tests/integration/test_customer_subscriptions.py tests/helpers/realm_auth.py
Result: PASS

cd backend && uv run pytest tests/integration/test_customer_subscriptions.py -q --no-cov
Result: 2 passed

npm --workspace frontend run test -- customer-subscription server-access subscription-cabinet --run
Result: 4 files passed, 24 tests passed

npm --workspace frontend run lint
Result: PASS

npm --workspace frontend run build
Result: PASS

cd backend && uv run alembic heads
Result: 20260527_msub08_service_identity (head)
```

## Production Backup

Pre-migration PostgreSQL backup was created on `prod-app-1`:

```text
/srv/cybervpn/backups/msub08-20260527T060900Z/cybervpn.sql.gz
sha256: c89f84432cc7f04ff6cc81e0773861243e208ebf14a233fad3c40edbd8cfd57c
size: 137K
```

## Production Deploy

Final runtime tag:

```text
main-07fd7871-msub08-20260527T061828Z
```

Detailed deploy transcript:

```text
docs/evidence/releases/msub08-deploy-20260527T061828Z/stage1-gitlab-deploy-main-07fd7871-msub08-20260527T061828Z.md
```

Runtime containers after deployment:

```text
cybervpn-backend:   cybervpn/cybervpn-backend:main-07fd7871-msub08-20260527T061828Z healthy
cybervpn-frontend:  cybervpn/cybervpn-frontend:main-07fd7871-msub08-20260527T061828Z healthy
cybervpn-worker:    cybervpn/cybervpn-task-worker:main-07fd7871-msub08-20260527T061828Z healthy
cybervpn-scheduler: cybervpn/cybervpn-task-worker:main-07fd7871-msub08-20260527T061828Z healthy
```

## Migration Evidence

Alembic state after migration:

```text
20260527_msub08_service_identity (head)
```

New `service_identities` columns:

```text
identity_scope:character varying
subscription_key:character varying
```

New indexes/constraints observed:

```text
ix_service_identities_identity_scope
uq_service_identities_account_scope_provider
uq_service_identities_scope_subscription
```

## Public Smoke

Post-migration public route smoke:

```text
200 https://api.cyber-vpn.net/healthz
200 https://cyber-vpn.net/ru-RU
200 https://my.cyber-vpn.net/ru-RU/dashboard
302 https://cyber-vpn.net/ru-RU/subscriptions
302 https://cyber-vpn.net/ru-RU/servers
```

HTTP/3/QUIC advertisement remained enabled:

```text
alt-svc: h3=":443"; ma=86400
```

Selected-subscription protected route existence smoke:

```text
GET  /api/v1/customer-subscriptions/{subscription_key}/config        -> 401 INVALID_TOKEN
POST /api/v1/customer-subscriptions/{subscription_key}/service-state -> 401 INVALID_TOKEN
```

This proves the routes are registered and protected; authenticated owner/user flow validation remains the next manual UI check.

