# CyberVPN Gap Closure — Agent Team Prompt (Phase 2)

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close ALL remaining gaps between backend and clients. Telegram Bot is OUT OF SCOPE.

---

## Goal

Close every remaining gap so that **every backend endpoint has a working frontend page, mobile screen, AND Telegram Mini App view**.

**Done criteria:**
1. Zero `alert('...')` or `throw new Error('Not implemented')` stubs in frontend
2. Zero `_kEnable*=false` feature flags in mobile
3. Telegram Mini App renders all user-facing features
4. `npm run build` (frontend), `flutter analyze` (mobile), `pytest` (backend) all pass
5. Every page/screen makes real API calls — no mock data

---

## Current State (Phase 1 completed)

### Already Done on Backend (9 new endpoints)
- `POST /auth/change-password` (rate limit 3/hr) ✅
- `POST/GET/DELETE /security/antiphishing` ✅
- `GET /subscriptions/active` (Redis 5min cache) ✅
- `POST /subscriptions/cancel` (idempotent) ✅
- `POST /trial/activate` + `GET /trial/status` (real logic, 7-day, one-time) ✅
- `GET /users/me/usage` (real Remnawave data) ✅
- DB migration: `trial_activated_at`, `trial_expires_at` ✅
- 4 integration test suites (auth, wallet, codes, 2FA) ✅

### Already Done on Frontend (45+ new files)
- 11 API client modules in `frontend/src/lib/api/` ✅
- Wallet page (`/wallet`) + sidebar ✅
- Payment History page (`/payment-history`) + sidebar ✅
- Referral page (`/referral`) + sidebar ✅
- Dashboard with real API data (DashboardStats, ServerGrid) ✅
- Settings page with ProfileSection + SecuritySection (placeholders) ✅
- SubscriptionsClient component (partial) ✅
- 11 test files for API clients ✅

### Already Done on Mobile (5 new screens, 2064 LOC)
- OTP Verification Screen (509 LOC, feature flag disabled) ✅
- Wallet Screen (298 LOC, graceful degradation) ✅
- Antiphishing Screen (503 LOC) ✅
- Change Password Screen (512 LOC) ✅
- Payment History Screen (242 LOC) ✅
- Full clean architecture for wallet/ and security/ features ✅
- 5 widget test files ✅

### Already Done on Telegram
- `TelegramMiniAppAuthProvider` — auto-auth via initData ✅
- `MiniAppNavGuard` — navigation guard for Mini App context ✅
- Backend `POST /auth/telegram/miniapp` — validates initData HMAC ✅
- Auth store `isMiniApp` detection + `telegramMiniAppAuth()` method ✅

---

## Remaining Gaps

### Backend Gaps (BF2-*)

| ID | Gap | Endpoint | Details |
|----|-----|----------|---------|
| BF2-1 | Wallet path aliases for mobile | `GET /wallet/balance` → alias to `GET /wallet` | Mobile uses `/wallet/balance`, backend serves `/wallet`. Add alias route returning same data |
| BF2-2 | OTP path alias for mobile | `POST /auth/verify-email` → alias to `POST /auth/verify-otp` | Mobile uses `verify-email`, backend uses `verify-otp`. Add alias |
| BF2-3 | Profile persistence | `GET/PATCH /users/me/profile` | Currently placeholder (doesn't persist). Add `display_name`, `language`, `timezone` columns to `admin_users`. Alembic migration required |
| BF2-4 | Devices/sessions list | `GET /auth/devices` | New endpoint. Query `refresh_tokens` table for active sessions. Return device_id, ip, last_used, user_agent. Allow `DELETE /auth/devices/{device_id}` for remote logout |
| BF2-5 | Notification preferences | `GET/PATCH /users/me/notifications` | New endpoint. Store email_marketing, email_security, push_connection, push_payment as JSON in `admin_users.notification_prefs` column. Migration required |

### Frontend Gaps (FF2-*)

| ID | Gap | Current state | Target |
|----|-----|---------------|--------|
| FF2-1 | `security.ts` API client | Throws `Error('Not implemented')` | Real Axios calls to `/auth/change-password`, `/security/antiphishing` CRUD |
| FF2-2 | SecuritySection — 2FA flow | `alert('2FA setup flow')` | Real modal: reauth → setup (show QR) → verify code → show backup codes → enable. Disable flow with password + TOTP. Uses `twofaApi` |
| FF2-3 | SecuritySection — Password change | `alert('Password change')` | Real modal/form: current password + new + confirm. Strength meter. Rate limit feedback (429 → cooldown timer). Uses `securityApi.changePassword()` |
| FF2-4 | SecuritySection — Antiphishing | `alert('Antiphishing')` | Real form: show current (masked), set/edit (1-50 chars), delete with confirm. Uses `securityApi` CRUD |
| FF2-5 | SubscriptionsClient — Cancel | `alert('Cancel subscription')` | Confirmation modal with warning text → `POST /subscriptions/cancel` → refresh data. Cyberpunk-styled danger modal |
| FF2-6 | SubscriptionsClient — Plans | `'Plans API integration pending'` | Fetch `GET /plans` → render plan cards with pricing, duration, features. Highlight current plan. Buy button → checkout flow |
| FF2-7 | Subscriptions — Trial | No UI | "Start Free Trial" button (visible if `trial/status` → `is_eligible`). Click → `POST /trial/activate`. Show trial status badge |
| FF2-8 | Subscriptions — Invite codes | No UI | Redeem form (input + button → `POST /invites/redeem`). "My Codes" section → `GET /invites/my` list |
| FF2-9 | Subscriptions — Promo codes | No UI | Input field in checkout/purchase area → `POST /promo/validate` → show discount preview. Apply to checkout |
| FF2-10 | Partner Dashboard page | No page | New `/partner` route. Dashboard: tier, total clients, total earned. Codes table (TanStack Table): create, edit markup, delete. Earnings history. Bind code section. Add to sidebar with `Handshake` icon |
| FF2-11 | Devices/Sessions page | No page | New `/devices` route or section in Settings. List active sessions → `GET /auth/devices`. Remote logout button per device → `DELETE /auth/devices/{id}`. Current device highlighted. Add to sidebar or Settings |
| FF2-12 | VPN Usage real data | `vpn.ts` returns mock | Wire `GET /users/me/usage` response into Dashboard stats (bandwidth gauge, connections count). Show in Settings or dedicated section |

### Mobile Gaps (MF2-*)

| ID | Gap | Current state | Target |
|----|-----|---------------|--------|
| MF2-1 | API constants alignment | `/wallet/balance` → backend gives `/wallet`; `/auth/verify-email` → backend gives `/auth/verify-otp` | Fix `api_constants.dart` to match backend OR wait for BF2-1/BF2-2 aliases. Coordinate with backend-dev |
| MF2-2 | Enable OTP feature flag | `_kEnableOtpVerification = false` in `register_screen.dart:32` | Set to `true`. Verify OTP screen works end-to-end with backend `POST /auth/verify-otp` + `POST /auth/resend-otp` |
| MF2-3 | Invite code redeem UI | None | Add to subscription feature: text input + "Redeem" button → `POST /invites/redeem`. Show result (free days granted). Add "My Codes" tab → `GET /invites/my` |
| MF2-4 | Promo code in purchase flow | None | Add promo code input to `purchase_screen.dart` → `POST /promo/validate` → show discount, apply to price |
| MF2-5 | Trial activation | None | Add "Start Free Trial" card on `plans_screen.dart` (visible if `GET /trial/status` → `is_eligible`). Tap → `POST /trial/activate`. Show active trial badge on profile |
| MF2-6 | Subscription cancel | Only purchase flow exists | Add "Cancel Subscription" button to subscription detail or profile. Confirmation dialog → `POST /subscriptions/cancel`. Update UI state |
| MF2-7 | Partner Dashboard screen | None | New feature folder `cybervpn_mobile/lib/features/partner/`. Copy structure from `referral/`. Screens: dashboard (tier, clients, earned), codes list (create, edit markup), earnings history, bind code. Wire in router at `/partner` |
| MF2-8 | Active subscription display | Uses Remnawave directly | Wire `GET /subscriptions/active` into profile dashboard subscription cards. Show plan_name, expires_at, traffic used/limit, auto_renew status |

### Telegram Mini App Gaps (TMA-*)

| ID | Feature | API endpoints | Details |
|----|---------|---------------|---------|
| TMA-1 | Mini App layout & routing | — | Create route group `frontend/src/app/[locale]/(miniapp)/` with mobile-first layout (NO sidebar, NO 3D globe, NO TerminalHeader). Use Telegram WebApp theme colors. Bottom tab bar: Home, Plans, Wallet, Profile. Detect Mini App via `window.Telegram?.WebApp` |
| TMA-2 | Home / Dashboard | `GET /subscriptions/active`, `GET /users/me/usage`, `GET /trial/status` | Subscription status card (plan, expiry, traffic gauge). Usage stats (bandwidth, connections). Trial status or "Start Trial" button. Quick action buttons (Plans, Wallet, Referral) |
| TMA-3 | Plans & Purchase | `GET /plans`, `POST /payments/crypto/invoice`, `GET /payments/crypto/invoice/{id}`, `POST /promo/validate`, `POST /invites/redeem` | Plan cards grid. Purchase via CryptoBot (opens Telegram payment). Promo code input. Invite code redeem. Trial activation button |
| TMA-4 | Wallet | `GET /wallet`, `GET /wallet/transactions`, `POST /wallet/withdraw` | Balance card. Transaction list with pagination. Withdrawal request form |
| TMA-5 | Referral | `GET /referral/code`, `GET /referral/stats`, `GET /referral/recent` | Referral code + Telegram share button (using WebApp.shareUrl). Stats cards. Commission history |
| TMA-6 | Profile & Security | `GET /auth/me`, `PATCH /users/me/profile`, `GET /2fa/status`, `POST /auth/change-password`, `GET/POST/DELETE /security/antiphishing` | User info card. Edit display name. 2FA status badge. Password change form. Antiphishing code management |
| TMA-7 | Payment History | `GET /payments/history` | Payment list with status badges, dates, amounts |
| TMA-8 | VPN Config | `GET /subscriptions/config/{user_uuid}` | Download/copy VPN config. QR code display for easy scanning. Deep link to mobile app |
| TMA-9 | Settings | `PATCH /users/me/profile`, `GET/PATCH /users/me/notifications` | Language selector (27 locales). Notification preferences. Theme toggle (use Telegram theme by default) |
| TMA-10 | Partner section | `GET /partner/dashboard`, `POST /partner/codes`, `GET /partner/earnings`, `POST /partner/bind` | Partner dashboard (if user is partner). Bind to partner code (for regular users) |

### Test Gaps (TE2-*)

| ID | Scope | Runner | Depends on |
|----|-------|--------|------------|
| TE2-1 | Frontend: SecuritySection real flows (2FA modal, password form, antiphishing form) | vitest | FF2-1..4 |
| TE2-2 | Frontend: SubscriptionsClient real flows (cancel, plans, trial, codes) | vitest | FF2-5..9 |
| TE2-3 | Frontend: Partner Dashboard page | vitest | FF2-10 |
| TE2-4 | Frontend: Devices/Sessions tests | vitest | FF2-11 |
| TE2-5 | Mobile: partner, codes, trial, cancel widget tests | flutter_test | MF2-3..7 |
| TE2-6 | Mobile: API alignment smoke tests | flutter_test | MF2-1 |
| TE2-7 | Mini App: component tests for all TMA pages | vitest | TMA-1..10 |
| TE2-8 | E2E: hit every user-facing endpoint, verify 200 | pytest / script | ALL |
| TE2-9 | Backend: devices list + notification prefs tests | pytest | BF2-4, BF2-5 |

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Max tasks |
|------|-----------|-------|-------------------|---------------|-----------|
| Lead (you) | — | opus | all (coordination only) | — | 0 |
| Backend | `backend-dev` | sonnet | `backend/` | backend-dev | 5 |
| Frontend | `frontend-dev` | sonnet | `frontend/` | general-purpose | 12 |
| Mobile | `mobile-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 8 |
| Mini App | `miniapp-dev` | sonnet | `frontend/` (miniapp routes) | general-purpose | 10 |
| Tests | `test-eng` | sonnet | `*/tests/`, `*/test/`, `*/__tests__/` | test-runner | 9 |

---

## Spawn Prompts

### backend-dev

```
You are backend-dev on the CyberVPN team (Phase 2). You work ONLY in backend/ and services/.
Stack: FastAPI, Clean Architecture + DDD, Python 3.13, SQLAlchemy 2, Alembic, Redis.

CONTEXT — What's already done:
- POST /auth/change-password, POST/GET/DELETE /security/antiphishing — DONE
- GET /subscriptions/active, POST /subscriptions/cancel — DONE
- POST /trial/activate, GET /trial/status — DONE (with DB migration for trial fields)
- GET /users/me/usage — DONE (real Remnawave data)
- 4 integration test suites — DONE

KEY FILES:
- Router registration: backend/src/presentation/api/v1/router.py
- Auth routes: backend/src/presentation/api/v1/auth/routes.py
- User model: backend/src/infrastructure/database/models/admin_user_model.py
- Existing aliases pattern: see how trial/routes.py and security/routes.py were added
- Mobile API paths: cybervpn_mobile/lib/core/constants/api_constants.dart (READ ONLY)
- Frontend API clients: frontend/src/lib/api/ (READ ONLY)

RULES:
- Backend is SOURCE OF TRUTH for API paths. Add alias routes for backward compat.
- Follow existing DDD patterns: use case → repository → model.
- Use Context7 MCP to look up library docs before using any library.
- New DB fields require Alembic migrations. One migration per task.
- Do NOT break existing working endpoints.

YOUR TASKS (priority order):

BF2-1: Wallet path aliases for mobile compatibility
  - Add GET /api/v1/wallet/balance → returns same response as GET /api/v1/wallet
  - Add GET /api/v1/wallet/transactions (already exists, verify path)
  - Add POST /api/v1/wallet/withdraw (already exists, verify path)
  - Purpose: mobile uses /wallet/balance, backend serves /wallet
  - File: backend/src/presentation/api/v1/wallet/routes.py

BF2-2: OTP endpoint alias for mobile
  - Add POST /api/v1/auth/verify-email → alias to POST /api/v1/auth/verify-otp
  - Add POST /api/v1/auth/resend-verification → alias to POST /api/v1/auth/resend-otp
  - Mobile app uses these paths. Backend uses verify-otp/resend-otp.
  - File: backend/src/presentation/api/v1/auth/routes.py

BF2-3: Profile persistence (currently placeholder)
  - Alembic migration: add display_name (String 100, nullable), language (String 10, default 'en'), timezone (String 50, default 'UTC') to admin_users
  - Update AdminUserModel with new columns
  - Implement real GET /users/me/profile — read from DB
  - Implement real PATCH /users/me/profile — persist to DB
  - File: backend/src/presentation/api/v1/profile/routes.py, backend/src/application/use_cases/profile/

BF2-4: Devices/sessions list + remote logout
  - GET /api/v1/auth/devices — list active sessions from refresh_tokens table
    - Return: device_id, ip_address, user_agent, last_used_at, is_current (compare with request device)
  - DELETE /api/v1/auth/devices/{device_id} — revoke specific refresh token (remote logout)
  - File: new use case + add routes to auth/routes.py
  - Use existing refresh_tokens table structure

BF2-5: Notification preferences CRUD
  - Alembic migration: add notification_prefs (JSON, default {}) to admin_users
  - GET /api/v1/users/me/notifications — return prefs object
  - PATCH /api/v1/users/me/notifications — partial update prefs
  - Schema: { email_security: bool, email_marketing: bool, push_connection: bool, push_payment: bool, push_subscription: bool }
  - File: new routes file + register in router.py

DONE CRITERIA: Each new endpoint returns correct response. python -m pytest tests/ -v passes.
NOTIFY: When BF2-1 and BF2-2 are done, message mobile-dev immediately — they need the path aliases.
When BF2-4 is done, message frontend-dev — they need devices endpoint for FF2-11.
```

### frontend-dev

```
You are frontend-dev on the CyberVPN team (Phase 2). You work ONLY in frontend/.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Motion 12, Zustand 5, TanStack Query 5, TanStack Table 8.

CONTEXT — What's already done:
- 11 API client modules in frontend/src/lib/api/ — all working EXCEPT security.ts (stubs)
- Wallet, Payment History, Referral pages — DONE with real API
- Dashboard with DashboardStats + ServerGrid — DONE with real API (10-30s polling)
- Settings page with ProfileSection, SecuritySection, LinkedAccountsSection — DONE but SecuritySection has alert() stubs
- SubscriptionsClient — partially done (cancel = alert, plans = placeholder text)
- Sidebar (cyber-sidebar.tsx) — has Wallet, Payment History, Referral added
- 11 API test files — DONE

KEY FILES (read these first):
- Placeholder stubs: frontend/src/lib/api/security.ts (throws Error — MUST replace)
- SecuritySection: frontend/src/app/[locale]/(dashboard)/settings/sections/SecuritySection.tsx (3 alert() calls)
- SubscriptionsClient: frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx (cancel alert, plans placeholder)
- Sidebar: frontend/src/widgets/cyber-sidebar.tsx (add new items here)
- Settings hooks: frontend/src/app/[locale]/(dashboard)/settings/hooks/useSettings.ts
- API clients pattern: frontend/src/lib/api/wallet.ts, frontend/src/lib/api/twofa.ts
- Design: Orbitron (display), JetBrains Mono (code), --color-matrix-green, --color-neon-cyan, --color-neon-pink, --color-neon-purple
- Types: frontend/src/lib/api/generated/types.ts (OpenAPI-generated, use when available)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- All components must be cyberpunk-themed (use existing design tokens and patterns).
- Import types from generated/types.ts when available. Create local types only if API not in OpenAPI spec yet.
- Server components (pages) are async. Client components use 'use client' + hooks.
- i18n: use useTranslations('Namespace') in client components, getTranslations() in server components.
- Do NOT downgrade any library version.

YOUR TASKS (priority order):

FF2-1: Implement security.ts API client (CRITICAL — unblocks FF2-2..4)
  - Replace ALL throw stubs with real Axios calls
  - changePassword: POST /api/v1/auth/change-password { current_password, new_password }
  - getAntiphishingCode: GET /api/v1/security/antiphishing → { code: string | null }
  - setAntiphishingCode: POST /api/v1/security/antiphishing { code: string }
  - deleteAntiphishingCode: DELETE /api/v1/security/antiphishing
  - Follow same pattern as frontend/src/lib/api/wallet.ts (apiClient, error handling)
  - File: frontend/src/lib/api/security.ts

FF2-2: SecuritySection — 2FA real flow (replace alert)
  - Enable button → modal: Step 1: reauth (password) → POST /2fa/reauth.
    Step 2: show QR code + secret → POST /2fa/setup.
    Step 3: verify 6-digit TOTP → POST /2fa/verify.
    Step 4: show backup codes → done.
  - Disable button → modal: enter password + TOTP code → POST /2fa/disable
  - Create frontend/src/app/[locale]/(dashboard)/settings/components/TwoFactorModal.tsx
  - Use twofaApi from frontend/src/lib/api/twofa.ts (already implemented!)
  - File: modify SecuritySection.tsx, create TwoFactorModal.tsx

FF2-3: SecuritySection — Password change real flow (replace alert)
  - Click "Change" → modal/form: current password, new password (with strength meter), confirm.
  - Submit → securityApi.changePassword(). Handle 429 (show cooldown timer, 3/hr limit).
  - Create frontend/src/app/[locale]/(dashboard)/settings/components/ChangePasswordModal.tsx
  - Reuse PasswordStrengthMeter from frontend/src/features/auth/components/PasswordStrengthMeter.tsx if it exists
  - File: modify SecuritySection.tsx, create ChangePasswordModal.tsx

FF2-4: SecuritySection — Antiphishing real flow (replace alert)
  - Click "Manage" → modal: show current code (masked), edit/set new (1-50 chars), delete with confirm
  - Submit → securityApi.setAntiphishingCode() / deleteAntiphishingCode()
  - Create frontend/src/app/[locale]/(dashboard)/settings/components/AntiphishingModal.tsx
  - File: modify SecuritySection.tsx, create AntiphishingModal.tsx

FF2-5: SubscriptionsClient — Cancel real flow (replace alert)
  - Click "Cancel Subscription" → danger confirmation modal (red-themed, cyberpunk)
  - Confirm → POST /subscriptions/cancel → show success → invalidate query → refresh
  - Create frontend/src/app/[locale]/(dashboard)/subscriptions/components/CancelSubscriptionModal.tsx
  - File: modify SubscriptionsClient.tsx

FF2-6: SubscriptionsClient — Plans section (replace placeholder)
  - Fetch GET /plans → render plan cards (name, price, duration, traffic limit, features)
  - Highlight current plan (match with /subscriptions/active)
  - Buy button → create crypto invoice → redirect to CryptoBot payment URL
  - Create useSubscriptionPlans() hook in subscriptions/hooks/
  - File: modify SubscriptionsClient.tsx, create PlanCard.tsx component

FF2-7: Subscriptions — Trial activation
  - Fetch GET /trial/status → if is_eligible, show "Start Free Trial (7 days)" button
  - Click → POST /trial/activate → show success with trial_end date
  - If trial active, show status badge with days_remaining
  - Create frontend/src/app/[locale]/(dashboard)/subscriptions/components/TrialSection.tsx
  - Wire into SubscriptionsClient.tsx or subscriptions/page.tsx

FF2-8: Subscriptions — Invite + Promo codes
  - Invite: Input field + "Redeem" button → POST /invites/redeem → show result (free days granted)
  - "My Codes" expandable section → GET /invites/my → list with code, status, created_at
  - Promo: Input field + "Validate" → POST /promo/validate → show discount preview
  - Create CodesSection.tsx component, wire into subscriptions page
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx

FF2-9: Partner Dashboard page (new route)
  - Create frontend/src/app/[locale]/(dashboard)/partner/page.tsx (server component)
  - Create PartnerClient.tsx (client component)
  - Fetch GET /partner/dashboard → display tier, total clients, total earned
  - Partner codes table (TanStack Table): code, markup %, clients, earned, created_at
  - Create code: POST /partner/codes { code, markup_percentage }
  - Edit markup: PUT /partner/codes/{id} { markup_percentage }
  - Earnings history: GET /partner/earnings → list
  - For non-partners: show "Enter Partner Code" form → POST /partner/bind { code }
  - Add to sidebar: { icon: Handshake, labelKey: 'partner', href: '/partner' }
  - Import Handshake from lucide-react in cyber-sidebar.tsx
  - Files: partner/page.tsx, partner/components/PartnerClient.tsx, partner/hooks/usePartner.ts

FF2-10: Devices/Sessions section in Settings (after BF2-4)
  - Fetch GET /auth/devices → list sessions
  - Each row: device name (parse user_agent), IP, last used, "current" badge
  - "Logout" button per device → DELETE /auth/devices/{id} → refresh list
  - "Logout All Other Devices" button → POST /auth/logout-all
  - Add as section in Settings page below LinkedAccountsSection
  - Create frontend/src/app/[locale]/(dashboard)/settings/sections/DevicesSection.tsx
  - Create useDevices() hook in settings/hooks/

FF2-11: VPN Usage real data in Dashboard
  - Fetch GET /users/me/usage → bandwidth_used/limit, connections_active/limit, period dates
  - Integrate into DashboardStats component or add UsageSection
  - Show bandwidth progress bar (used/limit), connection count
  - File: modify frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardStats.tsx or create UsageCard.tsx

DONE CRITERIA: All pages render, all API calls fire correctly, npm run lint && npm run build pass. Zero alert() stubs remain.
```

### mobile-dev

```
You are mobile-dev on the CyberVPN team (Phase 2). You work ONLY in cybervpn_mobile/.
Stack: Flutter, Riverpod 3.x, GoRouter 17, Clean Architecture + DDD, 27 locales.

CONTEXT — What's already done:
- OTP Verification Screen (509 LOC) — feature flag disabled ✅
- Wallet Screen (298 LOC) — graceful degradation on unavailable ✅
- Antiphishing Screen (503 LOC) ✅
- Change Password Screen (512 LOC) ✅
- Payment History Screen (242 LOC) ✅
- All have tests, router wiring, and localization ✅

KEY FILES (read these first):
- API constants: cybervpn_mobile/lib/core/constants/api_constants.dart
- Router: cybervpn_mobile/lib/app/router/app_router.dart
- Register screen (OTP flag): cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart (line 32: _kEnableOtpVerification = false)
- Existing referral feature (copy for partner): cybervpn_mobile/lib/features/referral/
- Existing subscription screens: cybervpn_mobile/lib/features/subscription/presentation/screens/
- Localization source: cybervpn_mobile/lib/core/l10n/arb/app_en.arb
- Cache constants: cybervpn_mobile/lib/core/constants/cache_constants.dart

RULES:
- Copy patterns from existing features (referral/ for partner, subscription/ for codes/trial)
- Use Context7 MCP to look up library docs before using any library.
- Provider scoping: autoDispose for screen-scoped, plain NotifierProvider for app-scoped
- AnimDurations tokens: fast=150ms, medium=200ms, normal=300ms, slow=500ms
- Update api_constants.dart when path changes are confirmed
- Add i18n strings to app_en.arb (generated files auto-update)
- Do NOT downgrade any package version

YOUR TASKS (priority order):

MF2-1: API constants alignment (COORDINATE with backend-dev)
  - Option A (if BF2-1/BF2-2 done): Keep current paths, backend has aliases
  - Option B (if not done yet): Update api_constants.dart to match actual backend paths:
    - /wallet/balance → /wallet
    - /auth/verify-email → /auth/verify-otp
    - /auth/resend-verification → /auth/resend-otp
  - Update wallet_remote_ds.dart if paths change
  - Wait for backend-dev message before starting. Ask lead if unclear.
  - File: cybervpn_mobile/lib/core/constants/api_constants.dart

MF2-2: Enable OTP feature flag + end-to-end verification
  - Set _kEnableOtpVerification = true in register_screen.dart
  - Verify register → OTP screen → verify → auto-login flow works
  - Ensure api_constants.dart path matches backend (verify-otp or verify-email depending on MF2-1)
  - Test resend OTP cooldown (60 seconds)
  - File: cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart

MF2-3: Invite code redeem UI
  - Add to subscription feature (not new feature folder)
  - New screen: InviteCodeScreen with:
    - Text input + "Redeem" button → POST /invites/redeem
    - Success: show "You got X free days!" with confetti/glow animation
    - "My Invite Codes" section → GET /invites/my → list codes with status
  - Add api_constants: inviteRedeem, invitesMy
  - Wire in router as nested route under subscription
  - Files: subscription/presentation/screens/invite_code_screen.dart, update router, update api_constants

MF2-4: Promo code in purchase flow
  - Add promo code input to purchase_screen.dart (expandable section)
  - Validate button → POST /promo/validate → show discount (percentage or fixed)
  - Apply to displayed price (strikethrough original, show discounted)
  - Add api_constants: promoValidate
  - File: modify cybervpn_mobile/lib/features/subscription/presentation/screens/purchase_screen.dart

MF2-5: Trial activation
  - Add TrialCard widget to plans_screen.dart (shown if GET /trial/status → is_eligible)
  - Card shows: "7-Day Free Trial", "No payment required", "Start Trial" button
  - Tap → POST /trial/activate → success animation → refresh plans screen
  - If trial active: show "Trial Active — X days remaining" badge
  - Add api_constants: trialActivate, trialStatus
  - File: modify plans_screen.dart, create trial_card_widget.dart

MF2-6: Subscription cancel UI
  - Add "Cancel Subscription" button to profile_dashboard_screen.dart (in subscription card area)
  - Only visible if subscription is active
  - Tap → confirmation bottom sheet (red-themed): "Are you sure? You will lose access on {expiry_date}"
  - Confirm → POST /subscriptions/cancel → refresh → show "Subscription canceled"
  - Add api_constants: subscriptionCancel
  - File: modify profile_dashboard_screen.dart, create cancel_subscription_sheet.dart

MF2-7: Partner Dashboard screen (new feature folder)
  - Create cybervpn_mobile/lib/features/partner/ — copy structure from referral/:
    domain/ (entities: partner_dashboard, partner_code, partner_earning; repositories: partner_repository)
    data/ (datasources: partner_remote_ds; repositories: partner_repository_impl)
    presentation/ (screens: partner_dashboard_screen; providers: partner_provider)
  - Dashboard screen shows: tier badge, total clients, total earned, commission rate
  - Codes tab: list of partner codes with markup %. Create code (FAB). Edit markup (tap row)
  - Earnings tab: list of recent earnings
  - For non-partners: "Enter Partner Code" input → POST /partner/bind
  - Add api_constants: partnerDashboard, partnerCodes, partnerCodeCreate, partnerCodeUpdate, partnerEarnings, partnerBind
  - Wire in router at /partner, add to bottom nav or profile quick actions
  - Add 20+ localization strings to app_en.arb
  - Files: entire partner/ feature folder (8-10 files)

MF2-8: Wire active subscription from new endpoint
  - Update profile_dashboard_screen.dart subscription card to use GET /subscriptions/active
  - Show: plan_name, status, expires_at, traffic used vs limit (progress bar), auto_renew badge
  - Add api_constants: subscriptionActive
  - File: modify profile_dashboard_screen.dart, update subscription data source

DONE CRITERIA: All screens render, API calls fire, flutter analyze shows zero issues. _kEnableOtpVerification = true.
COORDINATE: Wait for backend-dev on MF2-1 (path aliases). Message lead when MF2-7 is done.
```

### miniapp-dev

```
You are miniapp-dev on the CyberVPN team (Phase 2). You build the Telegram Mini App.
You work in frontend/src/app/[locale]/(miniapp)/ — a NEW route group in the existing Next.js 16 project.

Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Motion 12, TanStack Query 5.
Additional: Telegram WebApp SDK (@twa-dev/sdk or window.Telegram.WebApp)

CONTEXT — What already exists:
- TelegramMiniAppAuthProvider: frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx
  → Auto-authenticates via initData, redirects to /dashboard on success
- MiniAppNavGuard: frontend/src/features/auth/components/MiniAppNavGuard.tsx
- Auth store: useAuthStore().isMiniApp, telegramMiniAppAuth() — already implemented
- Backend: POST /auth/telegram/miniapp — validates initData HMAC-SHA256
- All API clients: frontend/src/lib/api/ (wallet, payments, subscriptions, twofa, referral, codes, security, profile, vpn)
- Cyberpunk design tokens: --color-matrix-green, --color-neon-cyan, --color-neon-pink, Orbitron font

KEY DESIGN DIFFERENCES (Mini App vs Dashboard):
- NO sidebar — use bottom tab bar (4-5 tabs)
- NO 3D globe or heavy Three.js — keep it lightweight for mobile WebView
- NO TerminalHeader — use Telegram's native header (WebApp.BackButton, WebApp.MainButton)
- Mobile-first: full-width cards, touch-friendly targets (min 44px)
- Theme: Use Telegram theme colors (WebApp.themeParams) with cyberpunk accents
- Animations: minimal (fast transitions, no complex 3D)

KEY FILES TO READ:
- Existing auth provider: frontend/src/features/auth/components/TelegramMiniAppAuthProvider.tsx
- API clients: frontend/src/lib/api/index.ts (all exports)
- Auth store: frontend/src/stores/auth-store.ts (isMiniApp detection)
- Dashboard layout: frontend/src/app/[locale]/(dashboard)/layout.tsx (DON'T copy sidebar, DO copy providers)

RULES:
- Use Context7 MCP to look up library docs (especially Telegram WebApp SDK).
- Reuse existing API clients from frontend/src/lib/api/ — do NOT duplicate.
- All pages must work inside Telegram WebView (320-428px width).
- Use TelegramMiniAppAuthProvider as auth wrapper in the miniapp layout.
- i18n: use existing next-intl setup with useTranslations().
- Do NOT import from (dashboard) route group components — create miniapp-specific components.
- Do NOT downgrade any library version.
- WebApp.ready() must be called on mount. WebApp.expand() for full height.

YOUR TASKS (priority order):

TMA-1: Mini App scaffold — layout, routing, bottom tabs
  - Create frontend/src/app/[locale]/(miniapp)/layout.tsx:
    - Wrap with TelegramMiniAppAuthProvider
    - Call WebApp.ready() + WebApp.expand() on mount
    - Bottom tab bar: Home, Plans, Wallet, Profile (4 tabs)
    - Use Telegram theme colors (WebApp.themeParams.bg_color etc.)
    - No sidebar, no 3D, minimal bundle
  - Create frontend/src/app/[locale]/(miniapp)/page.tsx → redirect to /home
  - Create shared MiniAppBottomNav component
  - Create useTelegramWebApp() hook for SDK methods
  - Files: (miniapp)/layout.tsx, components/MiniAppBottomNav.tsx, hooks/useTelegramWebApp.ts

TMA-2: Home / Dashboard page
  - Route: (miniapp)/home/page.tsx
  - Subscription status card: plan name, expiry, traffic gauge (used/limit)
  - Usage stats: bandwidth, connections
  - Trial section: "Start Trial" if eligible, "Trial Active (X days)" if active
  - Quick action grid: Plans, Wallet, Referral, Settings (4 cards)
  - API: GET /subscriptions/active, GET /users/me/usage, GET /trial/status
  - File: (miniapp)/home/page.tsx, (miniapp)/home/components/

TMA-3: Plans & Purchase page
  - Route: (miniapp)/plans/page.tsx
  - Plan cards (vertical scroll): name, price, duration, traffic, features
  - Highlight current plan with glow border
  - Purchase flow: select plan → promo code input (optional) → create crypto invoice → open CryptoBot via Telegram WebApp.openInvoice() or external link
  - Invite code redeem form (expandable section)
  - Trial activation button (if eligible)
  - API: GET /plans, POST /payments/crypto/invoice, POST /promo/validate, POST /invites/redeem, POST /trial/activate
  - File: (miniapp)/plans/page.tsx, (miniapp)/plans/components/

TMA-4: Wallet page
  - Route: (miniapp)/wallet/page.tsx
  - Balance card (large, prominent): amount + currency
  - Transaction list with infinite scroll (GET /wallet/transactions, offset+limit pagination)
  - Each transaction: type icon, description, amount (+/-), date, status badge
  - Withdraw button → bottom sheet form → POST /wallet/withdraw
  - API: GET /wallet, GET /wallet/transactions, POST /wallet/withdraw
  - File: (miniapp)/wallet/page.tsx, (miniapp)/wallet/components/

TMA-5: Profile page (tab in bottom nav)
  - Route: (miniapp)/profile/page.tsx
  - User info header: email, display name, member since
  - Sections (collapsible cards):
    1. Referral: code + "Share" button (WebApp.shareUrl()), stats
    2. Security: 2FA status badge, password change, antiphishing code
    3. Payment History: recent 5 payments, "See All" link
    4. Settings: language selector, notification prefs
    5. Partner section (if partner): dashboard mini-view, bind code
    6. Account: delete account link
  - API: GET /auth/me, GET /referral/code, GET /referral/stats, GET /2fa/status, GET /payments/history, PATCH /users/me/profile
  - File: (miniapp)/profile/page.tsx, (miniapp)/profile/components/

TMA-6: Referral sharing with Telegram native
  - In Profile → Referral section: show referral code + link
  - "Share with Friends" button → WebApp.shareUrl(referralLink) or WebApp.switchInlineQuery(code)
  - QR code for referral link (use qrcode library, already available?)
  - Stats: total referrals, total earned, commission rate
  - Recent commissions list
  - API: GET /referral/code, GET /referral/stats, GET /referral/recent
  - Can be inline in Profile or separate sheet

TMA-7: Security flows (modals/sheets)
  - Password change: bottom sheet with current + new + confirm fields
  - Antiphishing: bottom sheet showing current code, edit/delete options
  - 2FA: show status only (setup requires QR scan → redirect to mobile app or show QR in-app)
  - API: POST /auth/change-password, GET/POST/DELETE /security/antiphishing, GET /2fa/status
  - Create reusable MiniAppBottomSheet component

TMA-8: VPN Config access
  - Section on Home or Profile: "Get VPN Config" card
  - Tap → fetch GET /subscriptions/config/{user_uuid} → display config as copyable text
  - "Copy to Clipboard" button (WebApp.clipboard or navigator.clipboard)
  - "Open in CyberVPN App" deep link → cybervpn:// scheme
  - QR code with config URL for scanning with mobile app
  - File: (miniapp)/home/components/VpnConfigCard.tsx

TMA-9: Partner section
  - If user is partner (check GET /partner/dashboard — 200 vs 403/404):
    Show mini dashboard: tier, total clients, earned
    Codes list (view only in Mini App — create/edit via main app)
  - If not partner: "Have a partner code?" input → POST /partner/bind
  - File: (miniapp)/profile/components/PartnerSection.tsx

TMA-10: Payment History page (linked from Profile)
  - Route: (miniapp)/payments/page.tsx (or sheet from Profile)
  - List all payments with status badges (pending/completed/failed)
  - Amount, currency, date, plan name
  - API: GET /payments/history
  - File: (miniapp)/payments/page.tsx

DONE CRITERIA: All Mini App pages render inside Telegram WebApp context. WebApp.ready() fires. Bottom tabs work. All API calls use real endpoints. npm run build succeeds.
IMPORTANT: Test with ?tgWebAppPlatform=tdesktop query param for development.
```

### test-eng

```
You are test-eng on the CyberVPN team (Phase 2). You write tests ONLY — no production code.
You work across: backend/tests/, frontend/src/**/__tests__/, cybervpn_mobile/test/.

CONTEXT — What's already done:
- Backend: 4 integration test suites (auth flows, wallet+payments, codes, 2FA cycle) ✅
- Frontend: 11 API client test files ✅
- Mobile: 5 widget test files (OTP, wallet, antiphishing, change password, payment history) ✅

KEY FILES:
- Backend fixtures: backend/tests/conftest.py
- Backend test pattern: backend/tests/integration/api/v1/auth/test_auth_flows.py
- Frontend test pattern: frontend/src/lib/api/__tests__/wallet.test.ts
- Frontend mocks: frontend/src/test/mocks/handlers.ts
- Mobile test pattern: cybervpn_mobile/test/features/wallet/presentation/screens/wallet_screen_test.dart

RULES:
- Backend: httpx.AsyncClient + pytest-asyncio + test DB
- Frontend: vitest + MSW for API mocking + React Testing Library
- Mobile: flutter_test + mocktail + ProviderScope overrides
- Use Context7 MCP to look up testing library docs.
- Wait for implementation tasks to finish before testing new features.
- Follow existing test patterns exactly.

YOUR TASKS (priority order):

TE2-1: Frontend SecuritySection tests (after FF2-1..4 done)
  - Test TwoFactorModal: reauth step, QR display, verify step, disable flow
  - Test ChangePasswordModal: form validation, submit, 429 rate limit handling
  - Test AntiphishingModal: show current, edit, delete confirmation
  - Mock securityApi and twofaApi with MSW handlers
  - File: frontend/src/app/[locale]/(dashboard)/settings/__tests__/

TE2-2: Frontend Subscriptions tests (after FF2-5..8 done)
  - Test CancelSubscriptionModal: confirm, API call, success refresh
  - Test plan cards: render plans from API, highlight current
  - Test TrialSection: eligible state → button → activate → active state
  - Test CodesSection: invite redeem, promo validate
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/__tests__/

TE2-3: Frontend Partner Dashboard tests (after FF2-9 done)
  - Test PartnerClient: dashboard stats render, codes table CRUD, earnings list
  - Test non-partner view: bind code form
  - File: frontend/src/app/[locale]/(dashboard)/partner/__tests__/

TE2-4: Frontend Devices section tests (after FF2-10 done)
  - Test DevicesSection: list sessions, remote logout, current device badge
  - File: frontend/src/app/[locale]/(dashboard)/settings/__tests__/

TE2-5: Mobile widget tests for new screens (after MF2-3..7 done)
  - InviteCodeScreen: input, redeem, code list
  - Purchase screen with promo code
  - Trial card: eligible → activate → active
  - Subscription cancel confirmation
  - Partner dashboard: codes, earnings, bind
  - File: cybervpn_mobile/test/features/*/

TE2-6: Mobile API alignment smoke tests
  - Verify api_constants.dart paths match actual backend endpoints
  - Script that checks each constant URL returns valid response shape
  - File: cybervpn_mobile/test/core/constants/api_constants_test.dart

TE2-7: Mini App component tests (after TMA-1..10 done)
  - Test MiniAppBottomNav: tab switching, active state
  - Test Home page: subscription card, usage stats, trial section
  - Test Plans page: plan cards render, purchase flow
  - Test Wallet page: balance, transactions, withdraw
  - Test Profile sections: user info, referral, security
  - Mock Telegram WebApp SDK (window.Telegram.WebApp)
  - File: frontend/src/app/[locale]/(miniapp)/__tests__/

TE2-8: E2E verification script — hit every user-facing endpoint
  - Create backend/tests/e2e/test_all_endpoints.py
  - Register user → verify OTP → login → hit EVERY user endpoint → verify 200/201
  - Endpoints to test: /auth/me, /users/me/profile, /users/me/usage, /wallet, /wallet/transactions,
    /subscriptions/active, /trial/status, /referral/status, /referral/code, /referral/stats,
    /2fa/status, /security/antiphishing, /payments/history, /plans, /invites/my,
    /auth/devices, /users/me/notifications
  - Report: endpoint, status_code, response_time_ms, pass/fail
  - File: backend/tests/e2e/test_all_endpoints.py

TE2-9: Backend tests for new endpoints (after BF2-3..5 done)
  - Profile: GET returns defaults → PATCH updates → GET confirms persistence
  - Devices: GET lists sessions → DELETE specific → verify removed
  - Notifications: GET defaults → PATCH partial update → GET confirms
  - File: backend/tests/integration/api/v1/profile/, backend/tests/integration/api/v1/devices/

DONE CRITERIA: All tests pass in their runners.
Backend: cd backend && python -m pytest tests/ -v --tb=short
Frontend: cd frontend && npm run test
Mobile: cd cybervpn_mobile && flutter test
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    ┌─── BF2-1,2 ───→ MF2-1 ───→ MF2-2
                    │
PHASE 2 START ──────┤─── BF2-3 (profile persist) ───→ FF2-11 (VPN usage)
                    │
                    ├─── BF2-4 (devices endpoint) ───→ FF2-10 (devices UI)
                    │
                    ├─── BF2-5 (notifications) ───→ TMA-9 (settings)
                    │
                    ├─── FF2-1 (security.ts) ───→ FF2-2, FF2-3, FF2-4
                    │
                    ├─── FF2-5,6,7,8 (subscriptions full) ── independent after FF2-1
                    │
                    ├─── FF2-9 (partner page) ── independent
                    │
                    ├─── TMA-1 (scaffold) ───→ TMA-2..10 (can be parallel after scaffold)
                    │
                    ├─── MF2-3..8 (independent, start after MF2-1)
                    │
                    └─── TE2-8 (E2E) ───→ waits for ALL
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| BF2-1 | Wallet path aliases | backend-dev | — | P0 |
| BF2-2 | OTP path alias | backend-dev | — | P0 |
| BF2-3 | Profile persistence + migration | backend-dev | — | P1 |
| BF2-4 | Devices/sessions list + remote logout | backend-dev | — | P1 |
| BF2-5 | Notification preferences CRUD | backend-dev | — | P2 |
| FF2-1 | security.ts real API client | frontend-dev | — | P0 |
| FF2-2 | 2FA modal (real flow) | frontend-dev | FF2-1 | P0 |
| FF2-3 | Password change modal | frontend-dev | FF2-1 | P0 |
| FF2-4 | Antiphishing modal | frontend-dev | FF2-1 | P1 |
| FF2-5 | Subscription cancel modal | frontend-dev | — | P1 |
| FF2-6 | Plans section (real data) | frontend-dev | — | P1 |
| FF2-7 | Trial activation UI | frontend-dev | — | P1 |
| FF2-8 | Invite + Promo codes UI | frontend-dev | — | P1 |
| FF2-9 | Partner Dashboard page | frontend-dev | — | P2 |
| FF2-10 | Devices section in Settings | frontend-dev | BF2-4 | P2 |
| FF2-11 | VPN Usage real data | frontend-dev | — | P2 |
| MF2-1 | API constants alignment | mobile-dev | BF2-1, BF2-2 | P0 |
| MF2-2 | Enable OTP flag | mobile-dev | MF2-1 | P0 |
| MF2-3 | Invite code redeem UI | mobile-dev | MF2-1 | P1 |
| MF2-4 | Promo code in purchase | mobile-dev | MF2-1 | P1 |
| MF2-5 | Trial activation | mobile-dev | MF2-1 | P1 |
| MF2-6 | Subscription cancel | mobile-dev | MF2-1 | P1 |
| MF2-7 | Partner Dashboard screen | mobile-dev | MF2-1 | P2 |
| MF2-8 | Active subscription display | mobile-dev | MF2-1 | P1 |
| TMA-1 | Mini App scaffold + layout | miniapp-dev | — | P0 |
| TMA-2 | Home / Dashboard | miniapp-dev | TMA-1 | P0 |
| TMA-3 | Plans & Purchase | miniapp-dev | TMA-1 | P1 |
| TMA-4 | Wallet | miniapp-dev | TMA-1 | P1 |
| TMA-5 | Profile page | miniapp-dev | TMA-1 | P1 |
| TMA-6 | Referral sharing | miniapp-dev | TMA-5 | P2 |
| TMA-7 | Security flows | miniapp-dev | TMA-5 | P2 |
| TMA-8 | VPN Config access | miniapp-dev | TMA-2 | P2 |
| TMA-9 | Partner section | miniapp-dev | TMA-5 | P2 |
| TMA-10 | Payment History | miniapp-dev | TMA-1 | P2 |
| TE2-1 | Frontend security tests | test-eng | FF2-1..4 | P2 |
| TE2-2 | Frontend subscriptions tests | test-eng | FF2-5..8 | P2 |
| TE2-3 | Frontend partner tests | test-eng | FF2-9 | P2 |
| TE2-4 | Frontend devices tests | test-eng | FF2-10 | P2 |
| TE2-5 | Mobile widget tests (new) | test-eng | MF2-3..7 | P2 |
| TE2-6 | Mobile API alignment smoke | test-eng | MF2-1 | P1 |
| TE2-7 | Mini App component tests | test-eng | TMA-1..10 | P2 |
| TE2-8 | E2E all endpoints | test-eng | ALL | P3 |
| TE2-9 | Backend new endpoint tests | test-eng | BF2-3..5 | P2 |

### Task Counts

| Agent | Tasks | Count |
|-------|-------|-------|
| backend-dev | BF2-1..5 | 5 |
| frontend-dev | FF2-1..11 | 11 |
| mobile-dev | MF2-1..8 | 8 |
| miniapp-dev | TMA-1..10 | 10 |
| test-eng | TE2-1..9 | 9 |
| **TOTAL** | | **43** |

---

## Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `backend-dev` → BF2-1, BF2-2 (P0 — unblock mobile)
   - `frontend-dev` → FF2-1 (P0 — unblock FF2-2..4)
   - `mobile-dev` → WAIT for BF2-1/BF2-2 notification, meanwhile read codebase and plan MF2-3..8
   - `miniapp-dev` → TMA-1 (independent — scaffold can start immediately)
   - `test-eng` → TE2-6 (API alignment smoke test — can run against existing backend)

2. **Communication protocol:**
   - backend-dev finishes BF2-1+BF2-2 → messages mobile-dev ("aliases ready, paths: ...")
   - backend-dev finishes BF2-4 → messages frontend-dev ("devices endpoint ready at /auth/devices")
   - frontend-dev finishes FF2-1 → messages test-eng ("security.ts implemented, ready for TE2-1")
   - miniapp-dev finishes TMA-1 → starts TMA-2..5 in parallel (they're independent after scaffold)

3. **Parallel execution strategy:**
   - Wave 1 (immediate): BF2-1+2, FF2-1, TMA-1, TE2-6
   - Wave 2 (after wave 1): BF2-3..5, FF2-2..4+5..8, MF2-1..2, TMA-2..5
   - Wave 3 (after wave 2): FF2-9..11, MF2-3..8, TMA-6..10, TE2-1..5
   - Wave 4 (final): TE2-7..9, then TE2-8 (E2E)

4. **File conflict prevention:**
   - frontend-dev owns `frontend/src/app/[locale]/(dashboard)/` and `frontend/src/lib/api/`
   - miniapp-dev owns `frontend/src/app/[locale]/(miniapp)/` — NO overlap with frontend-dev
   - mobile-dev owns `cybervpn_mobile/` exclusively
   - backend-dev owns `backend/` exclusively
   - test-eng writes ONLY in test directories
   - cyber-sidebar.tsx: ONLY frontend-dev modifies this file

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task and come back to the blocked one later.

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Flutter Riverpod 3.x, etc.)
- Do NOT break existing working endpoints or pages
- Do NOT modify generated/types.ts manually (auto-generated from OpenAPI)
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT import (dashboard) components into (miniapp) — create miniapp-specific components
- Do NOT touch Telegram bot code (services/telegram-bot/) — OUT OF SCOPE

---

## Final Verification (Lead runs after ALL tasks complete)

```bash
# Backend
cd backend && python -m pytest tests/ -v --tb=short

# Frontend (includes Mini App)
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run build

# Mobile
cd cybervpn_mobile && flutter analyze
cd cybervpn_mobile && flutter test

# Verify zero stubs
grep -r "alert(" frontend/src/app/[locale]/(dashboard)/ --include="*.tsx" | grep -v node_modules
# Must return ZERO results

grep -r "throw new Error.*Not implemented" frontend/src/lib/api/ --include="*.ts"
# Must return ZERO results

grep -r "_kEnable.*false" cybervpn_mobile/lib/ --include="*.dart"
# Must return ZERO results

# Verify Mini App builds
grep -r "(miniapp)" frontend/src/app/ --include="*.tsx" -l | wc -l
# Must be >= 10 files
```

All commands must pass with zero errors. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

- [ ] Backend: 5 new endpoints/aliases working (BF2-1..5)
- [ ] Frontend: 0 alert() stubs, 0 throw stubs, 11 new/updated components
- [ ] Frontend: Partner page in sidebar, Devices section in settings
- [ ] Mobile: OTP enabled, 6 new screens, partner feature folder
- [ ] Mini App: 10 pages, bottom tabs, Telegram WebApp integration
- [ ] Tests: All runners green (pytest, vitest, flutter test)
- [ ] E2E: Every user endpoint returns 200
- [ ] Build: npm run build + flutter analyze pass clean
