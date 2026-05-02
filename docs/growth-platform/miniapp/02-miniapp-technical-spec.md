# Mini App Technical Spec

## Routing Policy

Canonical route map:

- `/[locale]/miniapp`
- `/[locale]/miniapp/home`
- `/[locale]/miniapp/servers`
- `/[locale]/miniapp/plans`
- `/[locale]/miniapp/checkout`
- `/[locale]/miniapp/wallet`
- `/[locale]/miniapp/devices`
- `/[locale]/miniapp/referral`
- `/[locale]/miniapp/profile`
- `/[locale]/miniapp/support`
- `/[locale]/miniapp/payments`

Required rule:

- any user already inside `/miniapp/*` must stay inside `/miniapp/*` after auth, 2FA return, purchase refresh, and error recovery.

## Frontend Structure

Recommended feature structure:

- `features/miniapp-runtime`
- `features/miniapp-auth`
- `features/miniapp-checkout`
- `features/miniapp-servers`
- `features/miniapp-support`
- `features/miniapp-referral`

## Telegram Lifecycle Layer

Required hooks:

- `useTelegramWebAppRuntime`
- `useMiniAppViewport`
- `useMiniAppBackButton`
- `useMiniAppMainButton`
- `useMiniAppInvoice`
- `useMiniAppStartParam`
- `useMiniAppTheme`
- `useMiniAppHaptics`
- `useMiniAppAnalytics`

## Backend Namespace

New namespace:

- `backend/src/presentation/api/v1/miniapp/`

This namespace should aggregate existing use cases into Telegram-optimized read models instead of duplicating business logic.

The payment side of this namespace must integrate cleanly with Telegram bot payment events, including explicit pre-checkout validation and authoritative successful payment handling.

## Bootstrap Model

`GET /api/v1/miniapp/bootstrap` should return:

- session state
- runtime commercial context
- user profile hints
- subscription and trial state
- wallet state
- device summary
- recommended server
- primary CTA
- referral share context
- unresolved payment state
- support routes
- feature flags
- freshness timestamp

## Session Model

- Telegram raw init data validated by backend;
- platform session issued or resumed server-side;
- runtime tenant context resolved during bootstrap;
- no trust decisions based on `initDataUnsafe`.

## Tenant Context

Mini App must support:

- `platform` mode;
- `partner` mode.

Tenant context affects:

- branding;
- support links;
- plan visibility;
- pricing and discounts;
- attribution;
- analytics surface metadata.

## Error States

Required user-visible states:

- invalid Telegram session;
- bootstrap unavailable;
- stale runtime data;
- payment pending;
- no eligible offers;
- service degraded;
- support required.

## Caching

- bootstrap payload should be short-lived;
- payment state must refresh server-authoritatively;
- server list should prefer platform snapshot data over direct client recomputation;
- locale and brand assets may use stronger caching if versioned safely.

## i18n and RTL

- use existing locale infrastructure;
- preserve RTL layout integrity;
- support tenant-aware copy overlays only where explicitly allowed;
- support partner branding without fragmenting the translation model.

## Accessibility and Mobile UX Constraints

- large tap targets;
- reduced reliance on hover or precision gestures;
- safe area awareness;
- explicit loading, stale, and degraded states;
- avoid deep, modal-heavy nesting that conflicts with Telegram navigation.

## Baseline Corrections Required Before Feature Expansion

- fix root redirect into `/miniapp/home`;
- keep auth return path inside Mini App;
- replace generic page fan-out with bootstrap-oriented model;
- add full server picker surface;
- complete Stars-based invoice lifecycle.
