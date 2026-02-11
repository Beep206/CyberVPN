# CyberVPN MVP — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context (file paths, constraints, done criteria). Project architecture is NOT repeated here.

---

## Goal

Close all gaps between backend (fully implemented) and clients (frontend web + Flutter mobile).
**MVP done** = every backend endpoint has a working frontend page AND mobile screen, all tests pass, `npm run build` succeeds.

---

## Feature Gaps (compact)

| Area | Gap | IDs |
|------|-----|-----|
| **Backend missing** | VPN usage stats, trial activate/status, password change, antiphishing CRUD, subscription active/cancel | BF-2..6 |
| **API misalignment** | 2FA DELETE vs POST, payments path, OAuth GET vs POST, account deletion | BF-1, MF-4 |
| **Frontend missing pages** | Subscriptions, Wallet, Payment History, Referral, full Settings | FF-3..6 |
| **Frontend missing API clients** | wallet, payments, subscriptions, 2FA, referral, codes, vpn, security, profile | FF-1 |
| **Frontend hardcoded** | Dashboard stats (mock data, no API calls) | FF-2 |
| **Invite/Promo codes UI** | No redeem/validate UI on frontend or mobile | FF-3, MF-7 |
| **Partner codes UI** | No partner dashboard on either client | FF-7, MF-8 |
| **Trial UI** | BF-3 backend only, no client UI | FF-3, MF-7 |
| **Subscription cancel mobile** | Purchase flow only, no cancel | MF-7 |
| **Mobile missing screens** | OTP verification, Wallet, Payment History, Password Change, Antiphishing | MF-1..3, MF-5..6 |
| **Telegram bot verification** | Bot implemented, needs endpoint alignment tests | TE-8 |
| **Tests** | Integration (auth, wallet, payments, codes, 2FA), widget, frontend unit, E2E | TE-1..7 |

---

## Team

| Role | Agent name | Model | Working directory | subagent_type |
|------|-----------|-------|-------------------|---------------|
| Lead (you) | — | opus | all (read-only coordination) | — |
| Backend | `backend-dev` | sonnet | `backend/`, `services/` | backend-dev |
| Frontend | `frontend-dev` | sonnet | `frontend/` | general-purpose |
| Mobile | `mobile-dev` | sonnet | `cybervpn_mobile/` | general-purpose |
| Tests | `test-eng` | sonnet | `backend/tests/`, `frontend/`, `cybervpn_mobile/test/` | test-runner |

---

## Spawn Prompts

### backend-dev

```
You are backend-dev on the CyberVPN team. You work ONLY in backend/ and services/.
Stack: FastAPI, Clean Architecture + DDD, Python 3.13, SQLAlchemy, Alembic.

RULES:
- Backend is SOURCE OF TRUTH for API paths. Add alias routes for backward compat, never break existing endpoints.
- Read cybervpn_mobile/lib/core/constants/api_constants.dart and frontend/src/lib/api/auth.ts to understand what clients expect.
- Follow existing DDD patterns: use case -> repository -> model.
- Use Context7 MCP to look up library docs before using any library.
- New DB fields require Alembic migrations.

Your tasks (in priority order):
BF-1: API alignment — add alias routes for mismatches (2FA DELETE, payments path, OAuth methods)
BF-2: GET /api/v1/vpn/usage — real stats from Remnawave
BF-3: POST /api/v1/trial/activate + GET /api/v1/trial/status
BF-4: POST /api/v1/auth/change-password (verify old, set new, rate limit 3/hr)
BF-5: Antiphishing CRUD (POST/GET/DELETE /api/v1/security/antiphishing) + migration
BF-6: GET /api/v1/subscriptions/active + POST /api/v1/subscriptions/cancel

Done = each endpoint returns correct response, backend tests pass.
Test: cd backend && python -m pytest tests/ -v --tb=short
```

### frontend-dev

```
You are frontend-dev on the CyberVPN team. You work ONLY in frontend/.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Motion 12, Zustand 5, TanStack Query 5.

Key files:
- Types: frontend/src/lib/api/generated/types.ts (OpenAPI-generated, do NOT duplicate)
- API pattern: frontend/src/lib/api/auth.ts, frontend/src/lib/api/client.ts
- Sidebar: frontend/src/widgets/cyber-sidebar.tsx
- Design tokens: --color-matrix-green, --color-neon-cyan, --color-neon-pink, Orbitron font

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Import types from generated/types.ts, never duplicate type definitions.

Your tasks (in priority order):
FF-1: Create API client modules (wallet, payments, subscriptions, twofa, referral, codes, vpn, security, profile) — types from generated/types.ts
FF-2: Dashboard — replace hardcoded mock data with real API calls via TanStack Query
FF-3: Subscriptions page — plans, current sub, cancel, invite code redeem form, promo code input at checkout, trial activation ('Start Free Trial' button). API: subscriptions, trial, invites, promo.
FF-4: Settings page — add ProfileSection, SecuritySection (2FA, password, antiphishing), DevicesSection
FF-5: Wallet page + add to sidebar in cyber-sidebar.tsx
FF-6: Payment History + Referral pages + add to sidebar
FF-7: Partner Dashboard page — /partner route, partner codes CRUD, client list, earnings table, bind code. Uses TanStack Table. Add to sidebar in cyber-sidebar.tsx.

Done = page renders, API calls fire, lint + build pass.
Test: cd frontend && npm run test
Lint: cd frontend && npm run lint
Build: cd frontend && npm run build
```

### mobile-dev

```
You are mobile-dev on the CyberVPN team. You work ONLY in cybervpn_mobile/.
Stack: Flutter, Riverpod 3.x, GoRouter, Clean Architecture + DDD, 27 locales.

Key files:
- API paths: cybervpn_mobile/lib/core/constants/api_constants.dart
- Router: cybervpn_mobile/lib/app/router/app_router.dart
- Feature structure: data/ (datasources, models, repos) -> domain/ (entities, repos) -> presentation/ (screens, notifiers, widgets)

RULES:
- Copy patterns from existing features (e.g., referral/ for Wallet, reset_password_screen for OTP)
- Use Context7 MCP to look up library docs before using any library.
- Provider scoping: autoDispose for screen-scoped, plain for app-scoped
- Update api_constants.dart when backend-dev reports path changes

Your tasks (in priority order):
MF-1: OTP Verification Screen (6-digit input, resend timer, auto-login on success) — wire after register
MF-2: Wallet Screen (balance card, transaction list, withdraw button) — new feature folder
MF-3: Payment History Screen — add to subscription feature, API already in subscription_remote_ds
MF-4: API Constants Alignment — sync api_constants.dart with actual backend paths (coordinate with backend-dev)
MF-5: Password Change Screen (current + new + confirm) — add to profile feature
MF-6: Antiphishing Code Screen (view masked, edit, delete) — add to profile -> security
MF-7: Codes + Trial + Subscription Cancel — invite redeem in subscription section, promo code in purchase flow, trial activation button, subscription cancel UI. Update api_constants.dart for trial/invite/promo paths.
MF-8: Partner Dashboard Screen — new feature folder cybervpn_mobile/lib/features/partner/, copy structure from referral/. Dashboard with codes, clients, earnings.

Done = screen renders, API calls fire, flutter analyze clean.
Test: cd cybervpn_mobile && flutter test
Analyze: cd cybervpn_mobile && flutter analyze
```

### test-eng

```
You are test-eng on the CyberVPN team. You write tests ONLY — no production code changes.
You work in backend/tests/, cybervpn_mobile/test/, and frontend/src/**/__tests__/.

Key files:
- Backend fixtures: backend/tests/conftest.py
- Frontend mocks: frontend/src/test/mocks/
- Frontend test pattern: frontend/src/lib/api/__tests__/auth.test.ts
- Telegram handlers: services/telegram-bot/src/handlers/

RULES:
- Backend: httpx.AsyncClient + test database, pytest fixtures
- Frontend: vitest + MSW
- Mobile: flutter_test + mocktail for provider mocking
- Use Context7 MCP to look up test library docs.
- Wait for implementation tasks to finish before writing tests for new features.

Your tasks (in priority order):
TE-1: Backend auth flow tests (register -> OTP -> verify -> login -> refresh -> logout, magic link, password reset, brute force)
TE-2: Backend wallet+payment tests (topup -> balance -> withdraw -> approve, checkout -> invoice -> webhook)
TE-3: Backend codes tests (invite create->redeem, promo validate->apply, referral commission, partner flow)
TE-4: Backend 2FA cycle (reauth -> setup -> verify -> login+TOTP -> disable, rate limiting)
TE-5: Mobile widget tests for new screens (OTP, wallet, payment history, password change, antiphishing)
TE-6: Frontend unit tests for new API clients + component tests for new pages
TE-7: E2E verification script — hit every endpoint, report status + response time
TE-8: Telegram bot integration tests — verify bot handlers call correct backend endpoints. Test promo entry, referral sharing, trial activation, payment flows.

Done = all tests pass in their respective runners.
Backend test: cd backend && python -m pytest tests/ -v --tb=short
Frontend test: cd frontend && npm run test
Mobile test: cd cybervpn_mobile && flutter test
```

---

## Task Registry & Dependencies

### Dependency Graph

```
BF-1 ──→ FF-1 ──→ FF-2, FF-3, FF-4, FF-5, FF-6
BF-1 ──→ MF-4
FF-7 ──→ depends on FF-1
MF-7 ──→ depends on BF-1 (aligned paths) + BF-3 (trial endpoint)
MF-8 ──→ depends on MF-4 (aligned api_constants)
TE-8 ──→ independent (tests existing bot)
BF-2..6 (independent, parallel)
MF-1, MF-2 (independent, start immediately)
MF-3, MF-5, MF-6 (after MF-1/MF-2 patterns established)
TE-1..4, TE-8 (start immediately — test existing code)
TE-5 ──→ waits for MF-1..8
TE-6 ──→ waits for FF-1..7
TE-7 ──→ waits for all BF + FF + MF
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| BF-1 | API alignment (alias routes) | backend-dev | — | P0 |
| BF-2 | VPN usage stats endpoint | backend-dev | — | P1 |
| BF-3 | Trial activate/status | backend-dev | — | P1 |
| BF-4 | Password change endpoint | backend-dev | — | P1 |
| BF-5 | Antiphishing CRUD + migration | backend-dev | — | P2 |
| BF-6 | Subscription active/cancel | backend-dev | — | P2 |
| FF-1 | API client modules (9 files) | frontend-dev | BF-1 | P0 |
| FF-2 | Dashboard real data | frontend-dev | FF-1 | P1 |
| FF-3 | Subscriptions + codes + trial UI | frontend-dev | FF-1 | P1 |
| FF-4 | Settings full page | frontend-dev | FF-1 | P1 |
| FF-5 | Wallet page + sidebar | frontend-dev | FF-1 | P2 |
| FF-6 | Payment History + Referral | frontend-dev | FF-1 | P2 |
| FF-7 | Partner Dashboard page | frontend-dev | FF-1 | P2 |
| MF-1 | OTP Verification Screen | mobile-dev | — | P0 |
| MF-2 | Wallet Screen | mobile-dev | — | P1 |
| MF-3 | Payment History Screen | mobile-dev | — | P1 |
| MF-4 | API Constants Alignment | mobile-dev | BF-1 | P1 |
| MF-5 | Password Change Screen | mobile-dev | BF-4 | P2 |
| MF-6 | Antiphishing Screen | mobile-dev | BF-5 | P2 |
| MF-7 | Codes + Trial + Sub cancel | mobile-dev | BF-1, BF-3 | P2 |
| MF-8 | Partner Dashboard Screen | mobile-dev | MF-4 | P2 |
| TE-1 | Auth flow tests | test-eng | — | P1 |
| TE-2 | Wallet + payment tests | test-eng | — | P1 |
| TE-3 | Codes system tests | test-eng | — | P1 |
| TE-4 | 2FA cycle tests | test-eng | — | P1 |
| TE-5 | Mobile widget tests | test-eng | MF-1..8 | P2 |
| TE-6 | Frontend unit tests | test-eng | FF-1..7 | P2 |
| TE-7 | E2E verification | test-eng | ALL | P3 |
| TE-8 | Telegram bot tests | test-eng | — | P2 |

### Task Counts

| Agent | Tasks | Count |
|-------|-------|-------|
| backend-dev | BF-1..6 | 6 |
| frontend-dev | FF-1..7 | 7 |
| mobile-dev | MF-1..8 | 8 |
| test-eng | TE-1..8 | 8 |

---

## Lead Coordination Rules

1. **Spawn all 4 agents immediately.** Assign first tasks: backend-dev gets BF-1 (P0), frontend-dev gets FF-1 (blocked on BF-1, can start optimistically), mobile-dev gets MF-1 (independent), test-eng gets TE-1..4 + TE-8 (test existing code). As agents finish, assign the next unblocked task from their list.

2. **5-6 tasks per teammate is optimal.** If an agent finishes early, assign the next unblocked task. Don't batch into rigid phases.

3. **API path conflicts.** If backend-dev changes a path, immediately notify frontend-dev and mobile-dev. Backend is source of truth.

4. **Plan approval is for risky changes only.** Use plan approval for DB migrations and breaking changes. Agents work autonomously on all other tasks.

5. **If you (lead) start implementing instead of delegating — stop.** Use delegate mode. Your job is coordination.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — it causes SQLite lock conflicts with parallel agents.

7. **Completion check.** After all tasks are done, run the verification checklist below.

---

## Hooks (optional)

- `TeammateIdle`: exit code 2 → sends feedback, keeps teammate working
- `TaskCompleted`: exit code 2 → rejects completion with feedback
- Configure in `.claude/hooks/` to enforce quality gates.

---

## Prohibitions

- Do NOT downgrade library versions
- Do NOT break existing working endpoints — only add new ones or alias routes
- Do NOT manually edit `tasks.json` or `generated/types.ts`
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 doc lookup when using a library

---

## Final Verification (Lead runs after all tasks)

```bash
# Backend
cd backend && python -m pytest tests/ -v --tb=short

# Frontend
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run build

# Mobile
cd cybervpn_mobile && flutter analyze
cd cybervpn_mobile && flutter test

# Final
git status  # commit all changes
```

All 6 commands must pass with zero errors. If any fail, assign fix to the responsible agent.
