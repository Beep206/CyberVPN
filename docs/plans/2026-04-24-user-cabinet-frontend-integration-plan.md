# CyberVPN user cabinet frontend integration plan

Date: 2026-04-24
Scope: `frontend/` personal account cabinet, menu information architecture, backend integration, UX/accessibility, observability and production readiness.

## Executive summary

The current `frontend/` protected dashboard is technically wired to authenticated backend APIs, but its IA and copy still reads like an operator command center. A production user cabinet needs a customer-first shell: subscription health, VPN readiness, traffic and device limits, wallet, payments, referrals, profile, security controls, notification health, diagnostics, and support paths.

This plan treats "100% ready" as a gated delivery program rather than a single UI patch. The first implementation slice should replace the dashboard entry point with a customer cockpit backed by existing API clients and remove admin-only navigation from the user sidebar. Remaining work is decomposed into route-by-route hardening, backend contract gaps, E2E coverage, Sentry/Web Vitals evidence, and WCAG 2.2-oriented accessibility checks.

## Current state analysis

### Frontend

- Stack is Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query, next-intl, Sentry, and motion.
- `frontend/next.config.ts` has `cacheComponents: true`, `reactCompiler: true`, Sentry config, and same-origin `/api/v1/*` rewrites to backend.
- Protected routes live under `frontend/src/app/[locale]/(dashboard)/` and are wrapped by `AuthGuard`, `QueryProvider`, Sentry-oriented `ErrorBoundary`, `CyberSidebar`, and `TerminalHeader`.
- Existing routes cover many cabinet capabilities: `dashboard`, `servers`, `subscriptions`, `wallet`, `payment-history`, `referral`, `settings`.
- Existing sidebar still exposes operator/admin IA: users, partner, analytics, monitoring/security.
- Existing dashboard title/copy emphasizes "VPN Command Center", server matrix, total users, total nodes, and ops telemetry rather than customer account health.
- i18n default locale files exist in `frontend/messages/en-EN/`; runtime fallback merges default locale messages for missing locale keys.

### Backend/API surface already available to frontend

- Session/auth: `/auth/session`, `/auth/refresh` through `AuthGuard` and `apiClient`.
- Profile: `GET/PATCH /users/me/profile` through `profileApi`.
- Usage: `GET /users/me/usage` through `vpnApi`.
- Entitlements: `GET /entitlements/current` through `entitlementsApi`.
- Service readiness: `POST /access-delivery-channels/current/service-state` through `serviceAccessApi`.
- Wallet: `GET /wallet`, transactions and withdrawals through `walletApi`.
- Payments: checkout/history clients exist through `paymentsApi` and commerce clients.
- Referral: status/code/stats/recent commissions through `referralApi`.
- Growth notifications: counters, list, detail, preferences, recovery and support escalation through `growthNotificationsApi`.
- Trial: `GET/POST /trial/*` through `trialApi`.
- Security: 2FA and anti-phishing API clients exist.

### Observability state

- Frontend Sentry config exists, but the Sentry rollout docs call out production evidence gaps: DSN/environment/release contracts, source maps/artifact validation, user context/privacy policy, smoke checks, alert routing, and rollout tracking.
- Backend and infra already contain Prometheus/Grafana and several observability plans, but the customer cabinet needs explicit frontend runtime metrics and user-flow signals.

## External implementation constraints checked

- Next.js 16 Cache Components: user-specific cabinet data must remain dynamic and must not be placed behind shared `use cache` boundaries.
- Next.js Proxy: this repo must use `src/proxy.ts`, not legacy middleware, for request interception.
- React Compiler: prefer straightforward components and avoid defensive `memo`/`useMemo`/`useCallback` unless profiling or existing patterns justify them.
- TanStack Query: use per-resource queries so one backend outage does not blank the whole cabinet.
- next-intl: all UI strings must be message-backed, with `en-EN` as the source fallback.
- Sentry Next.js: preserve client/server/edge setup and ensure environment and release are set consistently before production rollout.
- WCAG 2.2: target AA as a release gate and implement AAA-oriented improvements where feasible, especially focus visibility, contrast, target size, reduced motion, and consistent help.

## Target user cabinet IA

### Primary menu

- Dashboard: account cockpit with subscription health, connection readiness, traffic, devices, wallet, referrals, notifications, and next best actions.
- Servers: location selection, latency/load hints, supported protocols, DPI resistance and availability signals.
- Subscription: active plan, renewal date, trial status, add-ons, limits, plan upgrade/downgrade.
- Wallet: balance, frozen funds, rewards, withdrawals, top-up/credit sources.
- Payments: invoices, successful/failed attempts, receipts, refunds and dispute support.
- Referral: referral code, friend discount, pending/available rewards, reward history and rules.
- Settings: profile, language/timezone, notification preferences, security/2FA, anti-phishing, linked devices, privacy/export/delete.

### Secondary/support surfaces

- Notifications inbox: can be folded into dashboard first, then promoted to a route if volume grows.
- Diagnostics: connection checks, config status, service delivery channel, last successful connection, support handoff.
- Help/support: consistent placement across screens to satisfy WCAG 2.2 process consistency.

## UX/UI direction for 2026-grade cabinet

- Keep the CyberVPN cyberpunk identity, but shift from "admin terminal" to "private access cockpit".
- Prefer high-signal cards over decorative density: subscription health, connection readiness, next action, and risk state above the fold.
- Use progressive disclosure for advanced VPN details so non-technical customers can act without understanding backend concepts.
- Personalize responsibly: show relevant next steps from entitlement, trial, usage and notification state, but avoid dark-pattern urgency.
- Preserve tactile, expressive visuals through grids, glows, scanlines and motion, while respecting `prefers-reduced-motion`.
- Build AAA-oriented accessibility into components: visible focus rings, no hover-only actions, 44px practical tap targets where possible, semantic headings, labelled actions, no color-only state.

## Production readiness gates

### Functional

- Every primary menu item has a real route, message-backed copy, loading state, empty state, error state and authenticated backend contract.
- Dashboard degrades independently when optional APIs fail.
- Auth uses httpOnly cookie session only; no access or refresh token storage in browser JS.
- Subscription, wallet and payment actions are idempotent and show clear post-action status.

### Testing

- Unit tests for pure cabinet formatting/health logic.
- Component tests for dashboard shell, sidebar IA, focus order and route links.
- API client tests for profile, entitlements, usage, wallet, payments, referrals, notifications and security.
- E2E tests for login -> dashboard -> plan -> payment -> config -> settings -> logout.
- Accessibility checks: axe automated scan, keyboard sweep, reduced-motion sweep, screen-reader label review, color contrast review.

### Observability

- Sentry release/environment/user context wired with privacy-safe identifiers.
- Frontend Web Vitals and cabinet route timing are captured.
- API failures are tagged by endpoint family, status class and request ID, without PII payloads.
- Synthetic smoke checks cover dashboard load, subscription visibility, wallet visibility and settings load.
- Grafana/Sentry dashboards show route errors, hydration errors, API latency, Web Vitals, conversion failures and notification delivery issues.

### Security/privacy

- No secrets or tokens in client storage.
- No `dangerouslySetInnerHTML` for backend-provided content.
- Strict CSP/reporting remains enabled.
- User profile and support handoff data are treated as PII; do not send raw email/message bodies as Sentry tags.
- Financial and payment states avoid leaking provider internals in user-visible errors.

## Phased work plan

### Phase 0: IA and cockpit foundation

- Replace dashboard landing with a customer cabinet cockpit.
- Reduce sidebar to customer-safe primary routes.
- Convert operator block from admin identity to user node identity.
- Add message-backed `en-EN` and `ru-RU` strings.
- Add pure helper tests and sidebar IA tests.

### Phase 1: Backend-backed dashboard cards

- Read profile, entitlement, usage, wallet, referral, growth notification, trial and service access state through existing API clients.
- Show independent loading/error states per card.
- Add next best actions based on entitlement, trial and provisioning status.
- Add request retry/refetch behavior that pauses when the document is hidden or offline.

### Phase 2: Route completion

- Servers: show recommended location, latency/load, supported protocols and import config CTAs.
- Subscription: plan comparison, add-ons, trial activation, renewal and cancel/renewal semantics.
- Wallet/payments: transaction filters, receipts, withdrawal request status and payment retry.
- Referral: code sharing, reward lifecycle, anti-abuse rules and delivery troubleshooting.
- Settings: profile persistence, language/timezone sync, notifications, 2FA, anti-phishing and device management.

### Phase 3: Observability hardening

- Add cabinet runtime reporter for Web Vitals and route-level UX metrics.
- Add Sentry tags for route family, feature flag state, request ID and safe account realm metadata.
- Add synthetic monitoring and Sentry alert routes for dashboard, subscription, wallet and settings failures.
- Produce staging evidence: source maps uploaded, release visible, smoke errors captured, alert routing verified.

### Phase 4: AAA readiness and launch closure

- Run full keyboard and screen-reader review.
- Fix contrast/focus/reduced-motion gaps.
- Add Playwright E2E plus axe coverage for all primary flows.
- Complete Sentry and Grafana launch checklist.
- Freeze backend API contracts for all menu items.

## Immediate implementation slice

This change set should implement Phase 0 plus the first part of Phase 1:

- Add a reusable `customer-cabinet` widget.
- Render a backend-backed customer cockpit at `/dashboard`.
- Trim protected user navigation to customer routes.
- Update sidebar identity copy.
- Add tests for helper logic and navigation safety.

## Residual risks

- Some route implementations may still contain admin/platform-oriented language after dashboard IA changes.
- `ru-RU` will be updated directly, but other locales will initially rely on default `en-EN` fallback until translation pass.
- Existing dirty worktree changes make full-suite signal noisy; use targeted tests first, then schedule clean-branch full validation.
- True "100%" requires staging backend credentials, payment sandbox, Sentry DSN/release evidence and manual accessibility review.

## References

- Next.js Cache Components: https://nextjs.org/docs/app/getting-started/caching
- Next.js Proxy file convention: https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- React Compiler: https://react.dev/learn/react-compiler
- TanStack Query `useQuery`: https://tanstack.com/query/latest/docs/framework/react/reference/useQuery
- next-intl translations: https://next-intl.dev/docs/usage/translations
- Sentry Next.js setup: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
