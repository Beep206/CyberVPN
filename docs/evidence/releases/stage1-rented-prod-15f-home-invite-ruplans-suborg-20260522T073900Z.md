# Stage 1 Rented Prod 15F - Home Invite, Hidden RU Plans, Subscription .org

Date: 2026-05-22  
Scope: direct production hotfix, no GitLab/GitHub push

## Changes

- Added the Mini App invite redemption block to Home for users without active subscription/trial.
- Added hidden admin-only plans:
  - `Россия Старт`: 1 device, 30 GiB total traffic.
  - `Россия Базовый`: 2 devices, 60 GiB total traffic, represented as 30 GiB per device in plan metadata.
- Added backend subscription URL normalization from `.net` subscription URLs to `https://cyber-vpn.org/api/sub/{short_uuid}`.
- Updated `.org` ingress contract: `cyber-vpn.org/api/sub*` routes to Remnawave subscription delivery; non-subscription `.org` routes redirect to `.net`.
- Updated Remnawave runtime `SUB_PUBLIC_DOMAIN` to `cyber-vpn.org/api/sub`.
- Added `BIGINT` migration for `subscription_plans.traffic_limit_bytes` because 30 GiB and 60 GiB exceed PostgreSQL `INTEGER`.

## Local Verification

```text
npm run test:run --workspace frontend -- \
  src/app/[locale]/miniapp/home/__tests__/page.test.tsx \
  src/app/[locale]/miniapp/home/components/__tests__/HomeClient.test.tsx

Result: 22 passed.
```

```text
PYENV_VERSION=3.13.11 pytest --no-cov \
  tests/unit/pricing/test_pricing_catalog_seed.py \
  tests/unit/infrastructure/remnawave/test_subscription_urls.py

Result: 8 passed.
```

```text
PYENV_VERSION=3.13.11 python -m ruff check ...
Result: All checks passed.
```

## Production Verification

```text
Backend health: 200
Mini App Home route: 200
cyber-vpn.org root: 301 to https://cyber-vpn.net/
cyber-vpn.org/api/sub/health-smoke: 404 from Remnawave path, no redirect to .net
Backend URL normalizer: https://cyber-vpn.org/api/sub/example
```

Runtime containers verified healthy:

```text
cybervpn-backend: healthy
cybervpn-frontend: healthy
cybervpn-remnawave: healthy
cybervpn-telegram-bot: healthy
cybervpn-worker: healthy
cybervpn-scheduler: healthy
```

Pricing seed:

```json
{
  "plans_created": 8,
  "plans_updated": 0,
  "plans_retired": 0,
  "addons_created": 0,
  "addons_updated": 1
}
```

Public catalog check:

```json
{
  "count": 16,
  "codes": ["basic", "max", "plus", "pro"],
  "has_ru": false
}
```

Hidden RU plan check:

```text
count=8
ru_start: hidden, admin-only, device_limit=1, traffic_limit_bytes=32212254720
ru_basic: hidden, admin-only, device_limit=2, traffic_limit_bytes=64424509440
```

## Remaining Item

The code and edge now support `.org` subscription delivery, but XHTTP content is still a Remnawave profile/inbound/node configuration proof item. The subscription content must be rechecked after the Remnawave profile includes the S1 XHTTP inbound; backend/frontend should not synthesize XHTTP links.
