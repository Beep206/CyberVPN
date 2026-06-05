# CYBA-452 Готовность доступа

Дата: 2026-06-04
Владелец: `qa-lead-flow-mapper`
Родительская задача: [CYBA-451](/CYBA/issues/CYBA-451)
Статус gate: `GO - local-stage synthetic QA`

## Область

Этот gate покрывает безопасный non-production доступ, который нужен до старта manual QA:

- client frontend;
- partner portal и storefront;
- admin panel;
- backend/API, который используют все три web surfaces.

Manual QA по [CYBA-456](/CYBA/issues/CYBA-456), [CYBA-457](/CYBA/issues/CYBA-457), [CYBA-458](/CYBA/issues/CYBA-458), [CYBA-459](/CYBA/issues/CYBA-459), [CYBA-460](/CYBA/issues/CYBA-460) и [CYBA-461](/CYBA/issues/CYBA-461) может идти только в approved local-stage synthetic scope ниже. Authenticated/RBAC/payment/VPN/OAuth/email/Telegram areas остаются `blocked/not-tested`, если конкретный child issue не может использовать synthetic fixtures без раскрытия secrets.

## Граница безопасности

- Использовать только local, staging или dedicated QA environment.
- Не использовать production secrets, production Remnawave, реальные customer data, real payment capture, real payout execution или real Telegram `initData`.
- Evidence должен редактировать JWT, cookies, refresh tokens, passwords, `.env` values, customer PII, payment secrets, OAuth codes и Telegram tokens.
- QA может проверять только UI behavior, redirects, read-only state, sandbox/mock payment paths и non-destructive RBAC boundaries.

## Цели доступа

| Поверхность | Ожидаемый local URL | Ожидаемый non-production URL | Текущий статус | Owner/action |
| --- | --- | --- | --- | --- |
| Client frontend | `http://localhost:3000` | `http://127.0.0.1:13000` | Ready | Operator smoke: `/en-EN/login` returns 200. |
| Partner portal/storefront | `http://localhost:3002` | `http://127.0.0.1:3002` only if local-dev server is started safely | Partial | No stage1 partner container is deployed; partner QA is local-dev/source-level unless a safe preview is started. |
| Admin panel | `http://localhost:3001` | `http://127.0.0.1:13001` | Ready | Operator smoke: `/en-EN/login` returns 200. |
| Backend/API | `http://localhost:8000` из `backend/.env.example` | `http://127.0.0.1:18080` | Ready | Operator smoke: `/health` returns non-production health OK. |
| Remnawave integration | `http://localhost:3000` из `backend/.env.example` | Not approved | Not-tested | Remnawave/provisioning remains out of scope unless explicitly approved separately. |

## Доказательства по карте маршрутов

Route discovery выполнен по repo-local Next.js App Router files в `frontend/src/app`, `partner/src/app` и `admin/src/app`.

Context7 docs checked: `/vercel/next.js/v16.2.2` через `ctx7 docs`; проверены Next.js 16 `proxy.ts` convention и App Router dynamic segments. MCP Context7 недоступен из-за monthly quota exceeded.

### Client Frontend

Основные группы маршрутов:

- Marketing: `/:locale`, `/:locale/pricing`, `/:locale/features`, `/:locale/network`, `/:locale/status`, `/:locale/trust`, `/:locale/security`, `/:locale/contact`, legal/policy pages, comparison/device/guide dynamic pages.
- Auth: `/:locale/login`, `/:locale/register`, `/:locale/forgot-password`, `/:locale/reset-password`, `/:locale/verify`, `/:locale/magic-link`, `/:locale/magic-link/verify`, `/:locale/oauth/callback`, `/:locale/telegram-link`.
- Client dashboard: `/:locale/dashboard`, `/:locale/servers`, `/:locale/subscriptions`, `/:locale/wallet`, `/:locale/payment-history`, `/:locale/referral`, `/:locale/partner`, `/:locale/messages`, `/:locale/support`, `/:locale/settings`, `/:locale/users`, `/:locale/analytics`, `/:locale/monitoring`.
- Mini App: `/:locale/miniapp`, `/:locale/miniapp/home`, `/:locale/miniapp/plans`, `/:locale/miniapp/payments`, `/:locale/miniapp/wallet`, `/:locale/miniapp/devices`, `/:locale/miniapp/profile`, `/:locale/miniapp/referral`, `/:locale/miniapp/support`.
- Same-origin API routes: `/api/auth/2fa/*`, `/api/oauth/*`, `/api/analytics/*`, `/api/observability/sentry-contract`.

### Partner Surface

Основные группы маршрутов:

- Storefront: `/:locale`, `/:locale/checkout`, `/:locale/support`, `/:locale/legal-docs`.
- Auth: `/:locale/login`, `/:locale/register`, `/:locale/forgot-password`, `/:locale/reset-password`, `/:locale/verify`.
- Partner dashboard: `/:locale/dashboard`, `/:locale/application`, `/:locale/programs`, `/:locale/campaigns`, `/:locale/codes`, `/:locale/conversions`, `/:locale/analytics`, `/:locale/finance`, `/:locale/cases`, `/:locale/compliance`, `/:locale/reseller`, `/:locale/team`, `/:locale/organization`, `/:locale/integrations`, `/:locale/notifications`, `/:locale/legal`, `/:locale/settings`.
- Legacy/admin-route bridge в partner workspace: commerce, customers, governance, growth, infrastructure, integrations и security route families под `_legacy-admin-routes`.
- Same-origin API routes: `/api/auth/2fa/*`, `/api/integrations/telegram/bot/*`, `/api/analytics/*`, `/api/observability/sentry-contract`.

### Admin Surface

Основные группы маршрутов:

- Auth: `/:locale/login`.
- Admin dashboard: `/:locale/dashboard`.
- Commerce: `/:locale/commerce`, plans, addons, subscription templates, wallets, payments, withdrawals.
- Customers: `/:locale/customers`, `/:locale/customers/:userId`.
- Governance: admin invites, audit log, policy, webhook log.
- Growth: partners, referrals, invite codes, promo codes, gift codes, notifications, reporting, risk.
- Infrastructure: servers, hosts, inbounds, config profiles, snippets, squads, node plugins, xray, helix.
- Integrations: Telegram, realtime, push.
- Security: posture, sessions, two-factor, passkeys, anti-phishing, review queue.
- Support/messaging: `/:locale/support`, `/:locale/support/:ticketRef`, `/:locale/messaging`, `/:locale/messaging/:conversationRef`.
- Same-origin API routes: `/api/auth/2fa/*`, `/api/integrations/telegram/bot/*`, `/api/analytics/*`, `/api/observability/sentry-contract`.

## Проверки доступа перед `GO`

| Проверка | Обязательное evidence | Статус |
| --- | --- | --- |
| Каждый web origin загружается без production data | Sanitized screenshot landing/login или health page по каждой surface | Ready for client/admin; partner partial local-dev/source-level |
| API base reachable и non-production | Sanitized health/status response или approved backend owner statement | Ready |
| Auth redirect boundaries видимы | Sanitized screenshots/trace для unauthenticated access к dashboard routes | Ready for public/read-only/redirect QA |
| Admin и partner domains не cross-wired | URL bar + page identity evidence для admin и partner | Ready for admin; partner partial local-dev/source-level |
| `src/proxy.ts` присутствует в web workspaces | Repo inspection only, secret не нужен | Ready |

## Текущее решение

`GO - local-stage synthetic QA`.

Operator handoff от `2026-06-04T16:11:05Z` supersedes earlier `NO-GO`: approved local-stage endpoints and synthetic QA package are available. Scope remains restricted to local-stage/synthetic data, no production customer/payment data, no real payment or Telegram operations, no destructive admin operations, and no Remnawave/provisioning without separate approval.
