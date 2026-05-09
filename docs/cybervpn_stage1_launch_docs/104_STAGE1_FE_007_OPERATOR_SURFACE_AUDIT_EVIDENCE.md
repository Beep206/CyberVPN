# S1-FE-007 Operator Surface Audit Evidence

> Date: 2026-05-07
> Backlog ID: `S1-FE-007`
> Scope: local/no-cost frontend route audit and implementation for hiding operator/admin surfaces from ordinary customer dashboard users.
> Result: `LOCAL_PASS`

## Purpose

`S1-FE-007` proves that the Stage 1 customer dashboard does not expose operator/admin surfaces to ordinary B2C users.

The S1 boundary is:

- customer dashboard may show subscription, wallet, payment history, settings, config delivery and customer-safe route availability;
- customer dashboard must not show analytics, monitoring, users/admin grids, partner portal or operator server matrix metrics.

## Implemented Scope

- Added `stage1-customer-surface-policy.ts` as an explicit S1 customer dashboard allowlist/denylist.
- Dashboard navigation now filters items through the S1 customer surface policy instead of ad hoc route checks.
- `/analytics`, `/monitoring`, `/users` and `/partner` now call `notFound()` and do not mount the previous operator/admin client surfaces.
- `/servers` remains available because it is the S1 config-delivery/customer route surface.
- `/servers` no longer renders operator node metrics: load, online users, traffic, inbounds or node version.
- `/servers` no longer calls `serversApi.getStats()` from the customer cabinet.
- Route audit tests prove hidden operator pages resolve to `NEXT_NOT_FOUND`.
- Customer server-access tests prove customer config delivery still works while operator metrics are absent.

## Files Touched

- `frontend/src/shared/lib/stage1-customer-surface-policy.ts`
- `frontend/src/shared/lib/__tests__/stage1-customer-surface-policy.test.ts`
- `frontend/src/widgets/dashboard-navigation.ts`
- `frontend/src/app/[locale]/(dashboard)/analytics/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/monitoring/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/users/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/partner/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/__tests__/operator-surfaces.test.tsx`
- `frontend/src/widgets/server-access/server-access-dashboard.tsx`
- `frontend/src/widgets/server-access/__tests__/server-access-dashboard.test.tsx`
- `frontend/messages/en-EN/servers.json`
- `frontend/messages/ru-RU/servers.json`
- `frontend/src/i18n/messages/generated/en-EN.json`
- `frontend/src/i18n/messages/generated/ru-RU.json`

## Surface Matrix

| Surface | S1 customer state | Evidence |
|---|---|---|
| `/dashboard` | Allowed | Customer dashboard route remains in nav policy |
| `/subscriptions` | Allowed | Subscription/billing route remains in nav policy |
| `/wallet` | Allowed | Safe wallet/payment-history work remains in nav policy |
| `/payment-history` | Allowed | Customer payment history remains in nav policy |
| `/settings` | Allowed | Customer settings/devices route remains in nav policy |
| `/servers` | Allowed, customer-safe only | Config delivery works; operator metrics and stats API call hidden |
| `/referral` | Hidden by default | Controlled by `S1-FE-006` growth gate |
| `/analytics` | Hidden | Page calls `notFound()` |
| `/monitoring` | Hidden | Page calls `notFound()` |
| `/users` | Hidden | Page calls `notFound()` |
| `/partner` | Hidden | Page calls `notFound()` |

## Server Route Safety Contract

`/servers` is not treated as the old operator server matrix in S1. It is the customer access route for QR/subscription URL/config import.

The customer server surface must not render:

- raw node load percentage;
- online user count;
- traffic used bytes;
- inbound count;
- node version;
- Xray version;
- operator restart/stop/maintenance controls;
- provider/admin-only server stats.

## Local Verification

| Check | Command | Result |
|---|---|---|
| Focused frontend route and server-surface tests | `npm --prefix frontend run test:run -- src/shared/lib/__tests__/stage1-customer-surface-policy.test.ts src/widgets/__tests__/dashboard-navigation.test.ts src/app/'[locale]'/'(dashboard)'/__tests__/operator-surfaces.test.tsx src/widgets/server-access/__tests__/server-access-dashboard.test.tsx src/widgets/server-access/__tests__/server-access-model.test.ts` | `PASS`: 5 files, 16 tests |
| Focused lint | `npm --prefix frontend run lint -- src/shared/lib/stage1-customer-surface-policy.ts src/shared/lib/__tests__/stage1-customer-surface-policy.test.ts src/widgets/dashboard-navigation.ts src/widgets/__tests__/dashboard-navigation.test.ts src/app/'[locale]'/'(dashboard)'/analytics/page.tsx src/app/'[locale]'/'(dashboard)'/monitoring/page.tsx src/app/'[locale]'/'(dashboard)'/users/page.tsx src/app/'[locale]'/'(dashboard)'/partner/page.tsx src/app/'[locale]'/'(dashboard)'/__tests__/operator-surfaces.test.tsx src/widgets/server-access/server-access-dashboard.tsx src/widgets/server-access/__tests__/server-access-dashboard.test.tsx` | `PASS` |
| Production build | `npm --prefix frontend run build` | `PASS`: Next.js 16.2.4, Cache Components enabled, 2684 static pages generated |
| Production dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | `PASS` for high/critical. Low/moderate audit findings remain tracked for dependency work: `icu-minify`, `next-intl` and `postcss` through `next`. |
| Secret scan | `rg` high-confidence secret patterns over touched frontend/docs files | `PASS`: no matches |
| Static dangerous-pattern scan | `rg` for `dangerouslySetInnerHTML`, `eval`, `new Function`, `document.write`, shell/process and obvious SQL template patterns over touched runtime files | `PASS`: no matches |
| Whitespace/diff check | `git diff --check` over touched runtime/docs files | `PASS` |
| Running containers | `docker ps --format '{{.Names}}\t{{.Status}}'` | `PASS`: no running containers reported |

## Library Documentation Checked

- Official Next.js project structure docs were checked for App Router route organization.
- Official Next.js `proxy.js` docs were checked because this project uses `src/proxy.ts`, not middleware.
- Official Next.js `notFound()` docs were checked for route hiding behavior.
- Official Vitest `vi` docs were checked for `vi.mock` / `vi.hoisted` usage in route tests.

## Remaining Go-Live Evidence

This local evidence does not clear go-live by itself. Before S1 go-live, attach:

1. Deployed staging/RC screenshots or browser transcripts proving `/analytics`, `/monitoring`, `/users` and `/partner` do not render customer-visible operator content.
2. Deployed customer `/servers` screenshots proving config delivery remains usable while operator metrics stay hidden.
3. Final RC route audit proving customer nav contains only allowed S1 customer routes.
4. Admin app persona evidence remains covered separately by S1-ADM tasks and is not satisfied by this customer frontend audit.

## Acceptance Result

`S1-FE-007` is **completed locally** for customer route policy, direct route hiding, customer-safe `/servers` surface, focused tests, lint and production frontend build.

This closes the no-cost/local operator-surface hiding step. Deployed staging/RC browser evidence remains an open go-live requirement.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-008` is completed locally in `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
