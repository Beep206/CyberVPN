# CYBA-631 Flow Map

Дата: `2026-06-10`
Issue: [CYBA-631](/CYBA/issues/CYBA-631)
Parent: [CYBA-630](/CYBA/issues/CYBA-630)
Owner: `qa-lead-flow-mapper`

## Scope

Эта карта покрывает routes и business flows, нужные для triage 20 пунктов из [CYBA-630](/CYBA/issues/CYBA-630). Работа выполнена read-only: код, env, зависимости, API contracts, миграции и бизнес-логика не менялись.

Safety boundary:

- Использованы только repo/source review, существующие sanitized QA evidence packs и Paperclip issue context.
- Production secrets, cookies, JWT, refresh tokens, passwords, payment data, real Telegram `initData`, real customer data и real payment capture не использовались.
- P0/P1 пункты без screenshot/network/runtime proof отмечены как `needs safe runtime evidence`, а не как полностью воспроизведённые.

Context7 docs checked: N/A - QA/read-only flow map, code changes не выполнялись.

## Source Inputs

Primary route inventory:

- Client frontend routes: `frontend/src/app/[locale]/...`
- Partner portal routes: `partner/src/app/[locale]/...`
- Admin panel routes: `admin/src/app/[locale]/...`

Existing sanitized evidence:

- `client-findings.md`
- `docs/qa/manual-flow-audit/2026-06-04/admin-findings.md`
- `docs/qa/manual-flow-audit/2026-06-04/partner-findings.md`
- `evidence/a11y-i18n-responsive/manifest.md`
- `evidence/client/cyba-572/`
- `evidence/client/cyba-595/manifest.md`
- `evidence/client/cyba-608/network/settings-device-browser-qa-summary.json`
- `evidence/admin/cyba-609/notes/cyba-609-admin-sessions-browser-qa__20260609T190544Z.md`
- `evidence/partner/CYBA-610/notes/cyba-610-partner-security-sessions.md`

Primary source anchors:

- `frontend/src/features/header/user-menu.tsx`
- `frontend/src/widgets/public-terminal-header-controls.tsx`
- `frontend/src/widgets/settings-cabinet/settings-cabinet-dashboard.tsx`
- `frontend/src/widgets/settings-cabinet/settings-cabinet-model.ts`
- `frontend/src/widgets/server-access/server-access-dashboard.tsx`
- `frontend/src/widgets/server-access/server-access-model.ts`
- `frontend/src/features/messaging/components/NotificationCenterDropdown.tsx`
- `frontend/src/features/messaging/hooks/useCustomerMessaging.ts`
- `frontend/src/features/currency-selector/currency-selector.tsx`
- `frontend/src/features/customer-subscriptions/customer-subscription-switcher.tsx`
- `frontend/src/widgets/subscription-cabinet/subscription-cabinet-dashboard.tsx`
- `frontend/src/stores/auth-store.ts`

## Client Frontend Route Map

| Route group | Representative routes | Primary flows | CYBA-630 points |
|---|---|---|---|
| Public marketing | `/[locale]`, `/pricing`, `/download`, `/help`, `/contact`, `/status`, `/delete-account` | anonymous nav, pricing, language/currency/theme, login/register CTA, authenticated public header state | 13, 14, 15 |
| Auth | `/login`, `/register`, `/forgot-password`, `/reset-password`, `/magic-link`, `/magic-link/verify`, `/oauth/callback`, `/telegram-link` | password auth, 2FA boundary, OAuth/passkey/Telegram start, logout/session restoration | 7, 20 |
| Dashboard shell | `/dashboard`, dashboard layout, customer subscription switcher | selected subscription context, active status, globe/backdrop rendering, customer summary | 1, 7, 9, 12 |
| Settings cabinet | `/settings` | profile, display name, language/timezone, account ID, security, notifications, devices/sessions, Telegram linking, privacy/delete path | 1, 2, 3, 4, 5, 6, 17, 20 |
| Servers/VPN access | `/servers` | service state, provisioning state, config delivery, QR, subscription URL/copy/open, server list | 10, 12 |
| Messages/support | `/messages`, `/support` | support conversations, support replies, notification center, realtime/SSE sync | 11, 18, 19 |
| Subscriptions | `/subscriptions` | current plan, catalog, trial, checkout quote/commit, add-ons, orders, plan switcher | 16 |
| Mini App | `/miniapp/home`, `/miniapp/plans`, `/miniapp/vpn`, `/miniapp/support`, `/miniapp/profile`, `/miniapp/wallet` | Telegram-context auth, no-Telegram fallback, Mini App subscription/config empty states | related residual fixture risk only |

## Partner Portal Route Map

Partner coverage is not the primary surface for the 20 user-reported customer points, but it remains part of the full manual audit boundary.

| Route group | Representative routes | QA state |
|---|---|---|
| Auth | `/[locale]/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify` | Previous [CYBA-457](/CYBA/issues/CYBA-457) and [CYBA-573](/CYBA/issues/CYBA-573) evidence covers local/safe auth and route smoke. |
| Partner dashboard | `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` | Previous partner owner route/API failures were retested fixed in `docs/qa/manual-flow-audit/2026-06-04/partner-findings.md`. |
| Partner security sessions | `/security/sessions` | [CYBA-610](/CYBA/issues/CYBA-610) final retest passed after child fixes; synthetic stubs only. |
| Storefront | storefront home, `/checkout`, `/support`, `/legal-docs` | Not central to CYBA-630 customer header/settings issues. |

## Admin Panel Route Map

Admin is involved only where support/admin action must create customer-visible effects.

| Route group | Representative routes | Cross-surface dependency |
|---|---|---|
| Auth/RBAC | `/login`, dashboard protected routes, `/security/sessions` | Prior admin logout/session issue exists as an analogy for customer logout risk, but customer logout must be tested separately. |
| Support/messaging | `/support`, `/support/[ticketRef]`, `/messaging`, `/messaging/[conversationRef]` | Admin support reply should create customer notification/message delivery for points 11 and 18. |
| Customers | `/customers`, `/customers/[userId]` | Useful for customer identity/public UID validation once [CYBA-633](/CYBA/issues/CYBA-633) is ready. |
| Integrations/Telegram | `/integrations/telegram` | Useful for Telegram binding diagnostics, but real bot or production Telegram data is out of scope without Board approval. |

## Cross-Surface Flow Map

| Flow | Expected path | Current QA status | Owner issue |
|---|---|---|---|
| Public UID display | backend allocates non-sequential numeric public UID -> client profile/header/admin/customer surfaces display public UID -> UUID remains internal only | Source currently still shows `profile?.id` and `user?.id` on inspected customer surfaces; backend UID work appears in dirty tree but not validated end-to-end. | [CYBA-633](/CYBA/issues/CYBA-633) |
| Customer account IA | `/settings` profile is compact; security moves to clear `Security` area/route; delete-account is in-cabinet and localized | Settings source has separate cards but still one large route and delete path leaves cabinet. | [CYBA-632](/CYBA/issues/CYBA-632), [CYBA-634](/CYBA/issues/CYBA-634) |
| Header logout | user opens `UserMenu` -> `Sign out` -> server session revoked -> route leaves cabinet -> protected route redirects to login | Needs customer authenticated safe browser proof; source currently routes to `/` after clearing local state. | [CYBA-634](/CYBA/issues/CYBA-634), [CYBA-640](/CYBA/issues/CYBA-640), [CYBA-639](/CYBA/issues/CYBA-639) |
| Support reply notification | admin/support replies to customer ticket/conversation -> customer realtime sync or notification list updates -> header badge and panel show actionable item | Needs safe support fixture. Source merges notifications and conversations, but header panel can show unread badge from conversations while notifications list is empty. | [CYBA-635](/CYBA/issues/CYBA-635) |
| Provisioning correctness | active paid/trial subscription with working VPN credentials -> service state and config delivery show ready, not pending | Needs service-state fixture where VPN works and API states disagree. Source requires identity, provisioning profile, device credential, and access delivery channel to all be present/active. | [CYBA-636](/CYBA/issues/CYBA-636) |
| Telegram binding | settings Telegram link -> magic-link token generated -> bot accepts `/start auth_*` -> browser poll/confirm updates linked account | Needs approved safe Telegram bot/staging fixture. Reported bot failure is user-provided but not safely reproduced here. | [CYBA-637](/CYBA/issues/CYBA-637) |

## Status Taxonomy Used In Matrix

| Status | Meaning |
|---|---|
| `source-confirmed` | The inspected source currently implements the reported behavior or mismatch. Runtime evidence may still be required before filing as final bug. |
| `source-candidate` | Source gives a plausible cause, but browser/screenshot/network proof is needed. |
| `current-fix-candidate` | Current dirty checkout appears to already address the reported behavior; needs runtime verification before closing. |
| `previous-evidence` | Existing sanitized QA evidence covers an adjacent or historical flow. |
| `needs safe runtime evidence` | Requires local/staging/test authenticated fixture, network capture, screenshot, or event data; not safe to infer from source alone. |
| `product gap` | The request is product/UX scope, not a single broken existing behavior. |
| `blocked/not tested` | Cannot continue without named safe fixture, environment, approval, or another child issue. |
