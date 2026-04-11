# Admin Workspace Implementation Plan

**Goal:** Create a separate `admin` Next.js workspace by cloning the current `frontend`, then reducing it to a role-protected admin panel with only `login` and `dashboard`, only `ru-RU` and `en-EN`, and only `admin` / `super_admin` access.

**Architecture:** Start from the existing `frontend` app to preserve the current visual system, auth integration, and dashboard shell. Then isolate the new app as `admin`, remove consumer flows and routes, keep the existing dashboard as a temporary shell, and add strict RBAC around the existing session-based auth flow.

**Tech Stack:** Next.js 16.2, React 19, TypeScript 5.9, next-intl 4.x, Zustand, Tailwind CSS 4, existing backend auth/session API.

---

## Scope Decisions

- New app lives in `/admin` at repo root.
- Production app origin: `https://admin.ozoxy.ru`.
- Development app runs locally as a separate app.
- Recommended local port assumption: `http://localhost:3001`.
- Backend remains shared with the current frontend.
- Auth flow: `email/password + 2FA`.
- Allowed roles: `admin`, `super_admin`.
- Denied roles: `viewer`, `user`.
- Denied-role behavior: clear session and redirect to `/login?error=access_denied`.
- Locales: `ru-RU` and `en-EN` only.
- Default locale: `ru-RU`.
- Kept routes: `/{locale}/login`, `/{locale}/dashboard`.
- Current dashboard UI remains as a temporary admin dashboard shell for iteration one.

## Phase 1: Create The `admin` Workspace

**Goal:** Stand up a separate Next.js app without changing the existing `frontend` behavior.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/package.json`
- Create: `/home/beep/projects/VPNBussiness/admin/**`

**Work**
- Copy `/frontend` to `/admin`.
- Rename workspace package metadata for clarity.
- Add `admin` to root npm workspaces.
- Add root helper scripts if useful, for example `dev:admin`, `build:admin`, `lint:admin`.
- Verify `admin` can install and boot as an independent app.

**Validation**
- `npm run dev -w admin`
- `npm run build -w admin`
- `npm run lint -w admin`

## Phase 2: Isolate Runtime Configuration For Admin Origin

**Goal:** Make `admin` safe to run on `admin.ozoxy.ru` and locally.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/next.config.ts`
- Review: `/home/beep/projects/VPNBussiness/backend/.env.example`
- Review or modify if needed: `/home/beep/projects/VPNBussiness/backend/src/config/settings.py`

**Work**
- Update `serverActions.allowedOrigins` and `allowedDevOrigins` for the admin origin.
- Keep API rewrites pointing to the shared backend.
- Validate backend-origin compatibility for:
  - `CORS_ORIGINS`
  - cookie security in local HTTP development
  - session cookies through proxied `/api` routes
- Confirm current backend env supports local admin origin `http://localhost:3001`.

**Notes**
- Backend already exposes configurable CORS and cookie settings in:
  - `/home/beep/projects/VPNBussiness/backend/src/config/settings.py`
  - `/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/auth/cookies.py`

## Phase 3: Reduce Routing To Login And Dashboard Only

**Goal:** Strip the app down to the minimum route surface.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/layout.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/(auth)/layout.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/(dashboard)/layout.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/proxy.ts`
- Remove: unused routes under `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/`

**Work**
- Keep only:
  - `/{locale}/login`
  - `/{locale}/dashboard`
- Remove or disable route groups and pages for:
  - marketing
  - miniapp
  - register
  - forgot/reset password
  - magic link
  - oauth callback pages
  - telegram-link
  - extra dashboard sections
- Set root flow to land on the localized login path.

**Validation**
- Direct visit to `/ru-RU/login`
- Direct visit to `/ru-RU/dashboard`
- Root visit redirects to login

## Phase 4: Simplify Auth To Admin Login + Session + 2FA

**Goal:** Preserve only the auth pieces required for admin sign-in.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/(auth)/login/login-client.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/features/auth/components/AuthGuard.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/features/auth/lib/redirect-path.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/features/auth/lib/session.ts`
- Review: `/home/beep/projects/VPNBussiness/admin/src/stores/auth-store.ts`
- Review: `/home/beep/projects/VPNBussiness/admin/src/lib/api/auth.ts`
- Remove or stop using related UI/helpers for OAuth, Telegram, magic-link, register, forgot/reset

**Work**
- Keep:
  - login form
  - 2FA continuation flow
  - session bootstrap
  - logout
  - dashboard guard
- Remove from login UI:
  - social auth buttons
  - registration links
  - magic-link links
  - forgot password links
  - success states tied to registration
- Keep redirects centered on `/dashboard`.

## Phase 5: Add RBAC For `admin` And `super_admin`

**Goal:** Prevent non-admin roles from entering the panel even with valid credentials.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/src/features/auth/components/AuthGuard.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/stores/auth-store.ts`
- Possibly modify: `/home/beep/projects/VPNBussiness/admin/src/app/[locale]/(auth)/login/login-client.tsx`

**Work**
- After session fetch, allow only:
  - `admin`
  - `super_admin`
- If role is `viewer` or `user`:
  - clear auth state
  - call logout if needed
  - redirect to `/login?error=access_denied`
- Add UI message on login page for `access_denied`.

**Validation**
- Admin role reaches dashboard.
- Super admin role reaches dashboard.
- User or viewer role is rejected and returned to login.

## Phase 6: Reduce i18n To `ru-RU` And `en-EN`

**Goal:** Remove all other locales and keep localization maintainable.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/src/i18n/config.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/i18n/languages.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/i18n/navigation.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/i18n/request.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/scripts/generate-message-bundles.mjs`
- Remove: extra locale folders under `/home/beep/projects/VPNBussiness/admin/messages/`
- Regenerate: `/home/beep/projects/VPNBussiness/admin/src/i18n/messages.generated.ts`
- Regenerate: `/home/beep/projects/VPNBussiness/admin/src/i18n/messages/generated/*.json`

**Work**
- Make `ru-RU` the default locale.
- Keep only `ru-RU` and `en-EN` in config and language selector.
- Remove the full multilingual search grid behavior if it becomes unnecessary overhead.
- Regenerate translation bundles.

## Phase 7: Simplify The Admin Shell

**Goal:** Keep the cyberpunk style but remove consumer-product navigation and controls.

**Likely files**
- Modify: `/home/beep/projects/VPNBussiness/admin/src/widgets/dashboard-navigation.ts`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/widgets/cyber-sidebar.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/widgets/terminal-header.tsx`
- Modify: `/home/beep/projects/VPNBussiness/admin/src/widgets/terminal-header-controls.tsx`
- Possibly modify: `/home/beep/projects/VPNBussiness/admin/src/features/language-selector/language-selector.tsx`

**Work**
- Keep one sidebar item: `Dashboard`.
- Remove links/buttons leading to deleted flows.
- Keep language switcher and theme toggle.
- Remove consumer-only controls if they no longer make sense in admin.

## Phase 8: Remove Dead Code And Validate The App

**Goal:** Leave `admin` in a maintainable state after route and auth reduction.

**Likely files**
- Broad cleanup across `/home/beep/projects/VPNBussiness/admin/src/**`
- Broad cleanup across `/home/beep/projects/VPNBussiness/admin/messages/**`
- Review: `/home/beep/projects/VPNBussiness/admin/package.json`

**Work**
- Delete dead tests, components, hooks, translations, and helper files no longer referenced.
- Remove or keep dependencies based on actual usage after cleanup.
- Re-run lint and build until clean.

**Validation Checklist**
- App boots locally on the admin workspace.
- Root route resolves to `ru-RU` login flow.
- Login works with `email/password`.
- 2FA flow still works.
- Dashboard requires an authenticated admin role.
- Non-admin authenticated users are denied.
- Logout works.
- `ru-RU` and `en-EN` both render.
- No remaining links route to deleted pages.

## Main Risks To Check During Implementation

- Local cookie behavior if backend is using `secure` cookies during HTTP development.
- Admin origin allowlists in Next.js config and backend CORS config.
- Hidden imports from removed auth flows causing build failures.
- Translation bundle generator still expecting namespaces that were deleted.
- Header/sidebar controls importing deleted components.

## Suggested Execution Order

1. Create `admin` workspace and get it running.
2. Fix admin runtime config for local and production origins.
3. Remove routes and extra auth flows.
4. Add role gate for admin-only access.
5. Reduce i18n to two locales.
6. Simplify shell and remove dead code.
7. Run lint/build and smoke test auth scenarios.
