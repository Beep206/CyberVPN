# CyberVPN Phase 8 — Production Hardening & Platform Sync — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Fix ALL remaining ESLint errors, harden backend exception handling and metrics, fix Dart analysis, sync locales across platforms, upgrade Telegram bot to aiogram 3.25 with new UI features, and secure infrastructure.
> **Out of scope**: Certificate pinning SHA-256 values (require real production certs), TanStack Table `react-hooks/incompatible-library` warning (upstream library issue, acceptable tradeoff), `@next/next/no-assign-module-variable` in test performance baselines (testing concern only).

---

## Goal

This is **Phase 8 — Production Hardening**. Phases 1-7 built, polished, and gap-closed the CyberVPN platform. Phase 8 hardens code quality, syncs locale coverage across all platforms, upgrades the Telegram bot with aiogram 3.25 features, and secures infrastructure for production deployment.

### Task Summary

| # | Task | Platform | Severity | Files |
|---|------|----------|----------|-------|
| 1 | Fix React Compiler purity violations — Math.random() in 3D render paths | Frontend | P0 | 4 files, 47 calls |
| 2 | Fix ESLint unused imports/variables — 74 warnings | Frontend | P1 | ~20 files |
| 3 | Replace console.warn with console.error or remove | Frontend | P2 | 3 files |
| 4 | Fix triple-slash reference + delete orphaned backup file | Frontend | P2 | 2 files |
| 5 | Add Prometheus metrics to 20 uninstrumented route files | Backend | P0 | 20 files |
| 6 | Narrow `except Exception` to specific types + add logging | Backend | P1 | ~50 blocks across backend |
| 7 | Fix Dart import ambiguity in oauth_login.dart | Mobile | P0 | 1 file |
| 8 | Run `dart fix --apply` for style lints (prefer_const, unnecessary_lambdas) | Mobile | P1 | ~100 files |
| 9 | Document certificate pinning for pre-production | Mobile | P2 | 1 file |
| 10 | Remove REMNASHOP variables from .env files | Infra | P1 | 2 files |
| 11 | Add Docker network segmentation (1 flat → 4 tiered networks) | Infra | P1 | 1 file |
| 12 | Add monitoring volume backup cron + Prometheus auth from env | Infra | P2 | 2 files |
| 13 | Upgrade aiogram to 3.25 + colored buttons + custom emoji + expand locales (2→38) | Telegram Bot | P0 | ~40 new files |

**Done criteria:**
1. `cd frontend && npx eslint src/ 2>&1 | tail -1` shows < 30 problems (down from 449) — remaining are TanStack/test-only
2. `cd frontend && npm run build` passes
3. `cd frontend && npm run lint` passes
4. `grep -rn "except Exception:" backend/src/ | grep -v "as e" | wc -l` returns 0 — all broad catches have `as e` + logging
5. `grep -rl "track_\|\.inc()\|\.labels(" backend/src/presentation/api/v1/ --include="*.py" | wc -l` >= 30 (was 15)
6. `cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | grep "error" | wc -l` returns 0
7. `cd cybervpn_mobile && dart fix --dry-run 2>&1 | tail -3` shows "Nothing to fix"
8. `grep "REMNASHOP" infra/.env infra/.env.example | wc -l` returns 0
9. `ls services/telegram-bot/src/locales/ | wc -l` >= 38 (was 2)
10. `grep "aiogram>=3.25" services/telegram-bot/pyproject.toml` matches
11. `docker compose -f infra/docker-compose.yml config -q` passes

---

## Current State Audit (Phase 8 starting point)

### What's DONE (from Phases 1-7)

| Component | Status | Detail |
|-----------|--------|--------|
| Frontend TypeScript `any` | **0 in production** | All eliminated in Phases 6-7 |
| Frontend route boundaries | **36/36 (100%)** | error.tsx + loading.tsx + not-found.tsx in all routes |
| Frontend SEO | Complete | robots.ts, sitemap.ts, opengraph-image.tsx, JSON-LD |
| Frontend i18n | **38 locales** | All synced in messages/ and config.ts |
| Frontend Sentry | Wired | client, server, edge configs |
| Frontend 3D scenes | Working | AuthScene3D, FeaturesScene3D, GlobalNetwork, speed-tunnel |
| Backend endpoints | **156 across 34 routes** | Full API coverage |
| Backend FCM | **Real DDD stack** | Entity + repo + model + migration + routes |
| Backend tests | **842 real tests** | Zero pass-only stubs |
| Backend metrics | **15/34 routes** | Phase 7 added 10 modules (was 5) |
| Backend TODO/FIXME | **0** | Clean |
| Mobile features | **20 features, 46 screens** | All wired |
| Mobile tests | **184 test files** | Comprehensive coverage |
| Mobile locales | **38 ARB files** | Full i18n |
| Mobile TODO/FIXME | **0** | Phase 7 cleaned all |
| Infra services | **23 with 100% healthchecks** | remnashop dir deleted |
| Infra monitoring | **75 alert rules, 11 dashboards** | Full Prometheus + Grafana + Loki |
| Telegram bot | Working | aiogram 3.24, 2 locales (en, ru) |

### What REMAINS (Phase 8 must fix ALL)

#### ISSUE-1: Frontend — 449 ESLint problems (370 errors, 79 warnings)

**Breakdown:**

| Category | Count | Rule | Severity |
|----------|-------|------|----------|
| React Compiler purity violations | ~57 | `react-hooks/purity` | Error |
| Array mutation in render | 1 | `react-hooks/immutability` | Error |
| Unused imports/variables | 74 | `@typescript-eslint/no-unused-vars` | Warning |
| console.warn in production | 3 | — | Medium |
| Triple-slash reference | 1 | `@typescript-eslint/triple-slash-reference` | Error |
| TanStack Table incompatible | 1 | `react-hooks/incompatible-library` | Warning (OUT OF SCOPE) |
| Test file errors | ~310 | `no-assign-module-variable`, `no-require-imports` | Error |
| Orphaned backup file | 1 | `GlobalNetwork.backup.tsx` (341 lines, unreferenced) | Cleanup |

**Files with Math.random() purity violations:**

| File | Math.random() calls | Location |
|------|---------------------|----------|
| `3d/scenes/AuthScene3D.tsx` | 16 | Lines 147-158 (useMemo), 210-214 (useMemo), 227 (useFrame) |
| `3d/scenes/FeaturesScene3D.tsx` | 12 | Lines 18-28 (useMemo), 183-187 (useMemo), 198-199 (useFrame) |
| `3d/scenes/GlobalNetwork.tsx` | 9 | Lines 30-43 (useMemo), 234-235 (JSX) |
| `widgets/speed-tunnel.tsx` | 5 | Lines 97-99 (useMemo), 119-120 (useFrame) |
| `3d/scenes/GlobalNetwork.backup.tsx` | 8 | Unreferenced backup — DELETE |

**CRITICAL CONSTRAINT**: Fixing Math.random() MUST NOT change visual appearance. Particles must still look random and animated. The 3D scenes must render identically.

**Root cause**: Math.random() inside `useMemo` callbacks violates React Compiler purity rules. The compiler expects useMemo callbacks to be deterministic (same inputs → same output).

**Fix pattern**: Move random data generation to module-level factory functions (outside React component tree). Module-level code is NOT analyzed by the React Compiler:

```tsx
// BEFORE (inside component — impure useMemo):
const particles = useMemo(() => {
    return Array.from({ length: count }, () => ({
        position: new THREE.Vector3(
            (Math.random() - 0.5) * 12, // ERROR: impure
        ),
    }));
}, [count]);

// AFTER (module-level factory — pure component):
function generateParticles(count: number) {
    return Array.from({ length: count }, () => ({
        position: new THREE.Vector3(
            (Math.random() - 0.5) * 12, // OK: not in React tree
        ),
    }));
}

// Inside component:
const [particles] = useState(() => generateParticles(count));
```

**Why `useState(() => ...)` instead of `useMemo`**: The lazy initializer in `useState` runs once on mount. Since the particle data doesn't need to recompute when deps change (count is constant), `useState` with lazy init is correct and compiler-pure. `useMemo` would be wrong because the compiler might skip it if it determines the deps haven't changed.

**For Math.random() in `useFrame` callbacks**: These are NOT in React's render path — they execute in Three.js's animation loop. The compiler doesn't analyze them. Leave them as-is.

**Array mutation fix** (speed-tunnel.tsx line 113): Replace direct array mutation with a new array (spread + modify pattern).

#### ISSUE-2: Frontend — Unused imports/variables (74 warnings)

Most common patterns:
- `const t = useTranslations('...')` — imported but `t` never used in JSX
- Unused icon imports from `lucide-react` (Bell, Search, AlertCircle, etc.)
- Unused hooks (useEffect, useState, useRef) imported but not called
- Dashboard page components importing `useTranslations` for future i18n but not yet using it

Fix: Remove all unused imports. For pages with `const t = useTranslations()` where `t` is unused, remove the line entirely (i18n can be added when needed).

#### ISSUE-3: Frontend — console.warn in production (3 occurrences)

| File | Line | Statement | Action |
|------|------|-----------|--------|
| `shared/lib/web-vitals.ts` | 61 | `console.warn('Failed to create performance mark:', ...)` | Change to `console.error` |
| `shared/lib/web-vitals.ts` | 92 | `console.warn('Failed to measure performance:', ...)` | Change to `console.error` |
| `miniapp/hooks/useTelegramWebApp.ts` | 97 | `console.warn('Telegram WebApp not available...')` | Remove (expected in dev) |

#### ISSUE-4: Backend — Prometheus metrics coverage only 15/34 route files

**Currently instrumented (15):** auth, 2fa, invites, promo_codes, plans, oauth, wallet, servers, payments, profile, partners, trial, referral, subscriptions, ws/auth

**NOT instrumented (20 files):** admin, billing, config_profiles, fcm, hosts, inbounds, keygen, mobile_auth, monitoring, notifications, security, settings, snippets, squads, status, telegram, usage, users, webhooks, xray

**Existing metrics module**: `backend/src/infrastructure/monitoring/metrics.py` (147 lines) defines 20 counter/gauge/histogram objects. Route files import and call `.labels(...).inc()`.

**Pattern to follow** (from auth/routes.py):
```python
from src.infrastructure.monitoring.metrics import auth_attempts_total

# Inside route handler, after successful operation:
auth_attempts_total.labels(method="password", status="success").inc()
```

#### ISSUE-5: Backend — 72 broad `except Exception` blocks

**Distribution:**
- 14 in `application/use_cases/auth/` — OTP, register, OAuth, magic link
- 8 in `application/use_cases/payments/` — post-payment processing
- 6 in `application/use_cases/mobile_auth/` — refresh, logout
- 6 in `infrastructure/` — repositories, clients
- 38 across other use cases, shared, and presentation layers

**Problem**: ~50 of 72 use bare `except Exception:` without `as e`, silently catching and discarding errors. This masks bugs and prevents debugging.

**Fix strategy**:
1. Add `as e` to ALL `except Exception` blocks
2. Add `logger.exception("...", exc_info=True)` or `logger.warning("...")` to each
3. Where the specific exception type is known (e.g., `httpx.HTTPError`, `sqlalchemy.exc.SQLAlchemyError`, `redis.RedisError`), narrow the catch
4. Keep `except Exception as e` only where truly catching "anything" is intentional (e.g., background task error handling)

#### ISSUE-6: Mobile — 1,159 Dart analysis issues (483 errors, 181 warnings, 495 info)

**All 483 errors come from ONE file**: `lib/features/auth/domain/usecases/oauth_login.dart`
- **Cause**: Ambiguous import of `Failure` from two packages:
  1. `package:cybervpn_mobile/core/errors/failures.dart`
  2. `package:cybervpn_mobile/core/types/result.dart`
- **Fix**: Add `show` clause: `import '...failures.dart' show AuthFailure, ServerFailure, NetworkFailure;`

**181 warnings + 495 info** are style lints:
- `prefer_const_constructors` — ~200+
- `unnecessary_lambdas` — ~50+
- `prefer_const_literals_to_create_immutables` — ~15+
- `discarded_futures` — 1
- `unused_local_variable` — ~5

**Fix**: `dart fix --apply` handles most automatically. Remaining manual fixes for ~5 items.

#### ISSUE-7: Mobile — Certificate pinning empty

File: `cybervpn_mobile/lib/core/security/cert_pins.dart`
- `production = ''`, `productionBackup = ''`, `staging = ''`
- Infrastructure ready (dart-define injection, debug bypass, Android network_security_config.xml, tests)
- Need: Clear pre-production documentation with exact commands to generate SHA-256 fingerprints

#### ISSUE-8: Infrastructure — REMNASHOP variables in .env

```
infra/.env:36:### REMNASHOP ###
infra/.env:37:REMNASHOP_REDIS_PASSWORD=Nd9gvHwjFU6Cs_oWCczraQ
infra/.env.example:36:### REMNASHOP ###
infra/.env.example:37:REMNASHOP_REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD
```

#### ISSUE-9: Infrastructure — Single flat Docker network

All 23 services share one network (`remnawave-network`). No tier isolation — any compromised container can reach all others.

#### ISSUE-10: Infrastructure — No monitoring volume backup + hardcoded Prometheus auth

- Volumes `grafana_data`, `prometheus_data`, `loki_data`, `tempo_data` have no backup
- `infra/prometheus/prometheus.yml` line 30-32: `password: metrics_local_password` hardcoded

#### ISSUE-11: Telegram Bot — aiogram 3.24 (needs 3.25), only 2 locales

- Current: `aiogram>=3.24,<4.0` in pyproject.toml
- Need: `aiogram>=3.25,<4.0` for colored buttons, custom emoji, icon buttons
- Locales: 2 (en, ru) — frontend and mobile have 38

---

## Team

| Role | Agent name | Model | subagent_type | Working directory | Tasks |
|------|-----------|-------|---------------|-------------------|-------|
| Lead (you) | -- | opus | -- | all (coordination) | 0 |
| Frontend 3D Purity | `frontend-3d` | sonnet | 3d-engineer | `frontend/` | 2 |
| Frontend Lint Cleanup | `frontend-lint` | sonnet | ui-engineer | `frontend/` | 3 |
| Backend Hardening | `backend-harden` | sonnet | backend-dev | `backend/` | 2 |
| Mobile Dart Fix | `mobile-dart` | sonnet | flutter-code-reviewer | `cybervpn_mobile/` | 3 |
| Infrastructure Security | `infra-secure` | sonnet | devops-engineer | `infra/` | 4 |
| Telegram Bot Upgrade | `telegram-bot` | sonnet | telegram-bot-dev | `services/telegram-bot/` | 3 |
| Build Verification | `verify` | sonnet | general-purpose | all | 6 |

---

## Spawn Prompts

### frontend-3d

```
You are frontend-3d on the CyberVPN team (Phase 8). You fix React Compiler purity violations caused by Math.random() in 3D scene components. You also delete the orphaned backup file.
Stack: Next.js 16, React 19, TypeScript 5.9, React Three Fiber 9, Drei 10, Three.js 0.174.
You work ONLY in frontend/src/3d/ and frontend/src/widgets/speed-tunnel.tsx. Do NOT touch test files, other widgets, or pages.

CRITICAL VISUAL CONSTRAINT: The 3D scenes MUST look IDENTICAL after your changes — same particle count, same random distributions, same animation behavior, same colors. Your changes are code-level refactoring ONLY. If you're unsure about a change, err on the side of NOT changing it.

CONTEXT — Why Math.random() is flagged:
- React Compiler (enabled via reactCompiler: true in next.config.ts) auto-memoizes components
- The compiler's ESLint plugin (react-hooks/purity) requires useMemo/useCallback/component bodies to be PURE (deterministic)
- Math.random() is non-deterministic → flagged as purity violation
- Math.random() inside useFrame() callbacks is NOT flagged — it's not in React's render path

CONTEXT — What's already working:
- AuthScene3D: 200 floating particles + 30 data streams, cyan/purple colors, animated
- FeaturesScene3D: 100 particles + 25 data streams, animated
- GlobalNetwork: Spherical shell particles + orbit animations + data packets
- speed-tunnel: 500 tunnel particles flowing toward camera

KEY FILES TO READ FIRST (read ALL before writing any code):
1. frontend/src/3d/scenes/AuthScene3D.tsx — 16 Math.random() calls (14 in useMemo, 2 in useFrame)
2. frontend/src/3d/scenes/FeaturesScene3D.tsx — 12 Math.random() calls (10 in useMemo, 2 in useFrame)
3. frontend/src/3d/scenes/GlobalNetwork.tsx — 9 Math.random() calls (7 in useMemo, 2 in JSX)
4. frontend/src/widgets/speed-tunnel.tsx — 5 Math.random() calls (3 in useMemo, 2 in useFrame) + 1 array mutation
5. frontend/src/3d/scenes/GlobalNetwork.backup.tsx — orphaned backup, DELETE

RULES:
- Use Context7 MCP to look up React Three Fiber 9 docs and Three.js docs if needed.
- Do NOT downgrade any library version.
- Do NOT change particle counts, color distributions, animation speeds, or spatial distributions.
- Do NOT modify useFrame() callbacks that use Math.random() for animation — they are NOT in render path.
- Do NOT modify any component's visual output or props interface.
- Do NOT add "use no memo" directive — fix the actual purity issue instead.
- Do NOT use a seeded PRNG (that would make scenes deterministic across page loads — user wants randomness).
- Test: After changes, `npx eslint src/3d/ src/widgets/speed-tunnel.tsx 2>&1 | grep "react-hooks" | wc -l` should be 0 (or only TanStack-related).

YOUR TASKS:

FE3D-1: Fix Math.random() purity violations in 4 files (P0)

  THE FIX PATTERN — for each file, apply this transformation:

  STEP 1: Identify all useMemo blocks that contain Math.random()
  STEP 2: Extract the random generation into a module-level factory function
  STEP 3: Replace useMemo with useState lazy initializer

  === AuthScene3D.tsx (16 calls → 0 in render) ===

  BEFORE (current code, approximately):
  ```tsx
  function FloatingParticles({ count = 200 }) {
      const particles = useMemo(() => {
          return Array.from({ length: count }, () => ({
              position: new THREE.Vector3(
                  (Math.random() - 0.5) * 12,  // FLAGGED
                  (Math.random() - 0.5) * 8,
                  (Math.random() - 0.5) * 6
              ),
              velocity: new THREE.Vector3(
                  (Math.random() - 0.5) * 0.01,
                  (Math.random() - 0.5) * 0.01,
                  (Math.random() - 0.5) * 0.005
              ),
              scale: Math.random() * 0.4 + 0.1,
              phase: Math.random() * Math.PI * 2,
              color: Math.random() > 0.7 ? 1 : 0,
          }));
      }, [count]);

      const streams = useMemo(() => {
          return Array.from({ length: count }, () => ({
              x: (Math.random() - 0.5) * 10,
              z: (Math.random() - 0.5) * 4 - 2,
              speed: Math.random() * 0.03 + 0.02,
              length: Math.random() * 1.5 + 0.5,
              y: Math.random() * 8 - 4,
          }));
      }, [count]);
  ```

  AFTER:
  ```tsx
  // Module-level factory — outside React component tree, NOT analyzed by compiler
  function generateParticles(count: number) {
      return Array.from({ length: count }, () => ({
          position: new THREE.Vector3(
              (Math.random() - 0.5) * 12,
              (Math.random() - 0.5) * 8,
              (Math.random() - 0.5) * 6
          ),
          velocity: new THREE.Vector3(
              (Math.random() - 0.5) * 0.01,
              (Math.random() - 0.5) * 0.01,
              (Math.random() - 0.5) * 0.005
          ),
          scale: Math.random() * 0.4 + 0.1,
          phase: Math.random() * Math.PI * 2,
          color: Math.random() > 0.7 ? 1 : 0,
      }));
  }

  function generateStreams(count: number) {
      return Array.from({ length: count }, () => ({
          x: (Math.random() - 0.5) * 10,
          z: (Math.random() - 0.5) * 4 - 2,
          speed: Math.random() * 0.03 + 0.02,
          length: Math.random() * 1.5 + 0.5,
          y: Math.random() * 8 - 4,
      }));
  }

  function FloatingParticles({ count = 200 }) {
      // useState lazy initializer — runs once on mount, pure from compiler's view
      const [particles] = useState(() => generateParticles(count));
      const [streams] = useState(() => generateStreams(count));
  ```

  IMPORTANT: Keep useFrame callbacks UNTOUCHED. The Math.random() at line ~227:
  ```tsx
  child.position.x = (Math.random() - 0.5) * 10;
  ```
  This is inside useFrame (animation loop), NOT in render path. Leave it as-is.

  === FeaturesScene3D.tsx (12 calls → 0 in render) ===

  Same pattern: Extract the two useMemo blocks (particles ~lines 18-28, streams ~lines 183-187) into module-level factory functions. Replace useMemo with useState lazy init.

  Keep useFrame Math.random() (lines 198-199) untouched.

  === GlobalNetwork.tsx (9 calls → 0 in render) ===

  Same pattern: Extract the useMemo block (spherical shell particles ~lines 30-43) into a module-level factory. Replace useMemo with useState lazy init.

  SPECIAL CASE: Lines 234-235 have Math.random() in JSX (DataPacket component render). If these are inside a map or direct render, extract to a module-level generated array or use useState.

  Read the file carefully to understand the DataPacket pattern before changing.

  === speed-tunnel.tsx (5 calls + 1 mutation → 0 violations) ===

  Same pattern for useMemo particle generation.

  ADDITIONAL FIX — Array mutation at line ~113:
  The `positions` typed array is being modified directly (immutability violation).
  This is inside a useFrame callback, which should be fine. If ESLint still flags it,
  the issue is that the positions array was created in render scope and mutated in useFrame.
  Fix: Create the positions buffer in a ref:
  ```tsx
  const positionsRef = useRef<Float32Array | null>(null);
  if (!positionsRef.current) {
      positionsRef.current = new Float32Array(count * 3);
      // ... initialize
  }
  ```

FE3D-2: Delete orphaned backup file (P0)

  File: frontend/src/3d/scenes/GlobalNetwork.backup.tsx (341 lines, 13KB)
  - NOT imported anywhere (verified: grep returns 0 references)
  - Stale backup from before Phase 6 refactoring
  - Delete it: rm frontend/src/3d/scenes/GlobalNetwork.backup.tsx
  - Verify: ls frontend/src/3d/scenes/GlobalNetwork.backup.tsx returns "No such file"

VERIFICATION after all changes:
  cd frontend
  npx eslint src/3d/ src/widgets/speed-tunnel.tsx 2>&1 | grep -c "react-hooks/purity\|react-hooks/immutability"
  # Must be 0

  npm run build 2>&1 | tail -5
  # Must pass (no TypeScript errors)

DONE CRITERIA: All Math.random() moved out of render path. Zero react-hooks/purity errors in 3D files. GlobalNetwork.backup.tsx deleted. Build passes. Visual appearance UNCHANGED.
```

### frontend-lint

```
You are frontend-lint on the CyberVPN team (Phase 8). You clean up ESLint warnings: unused imports, console.warn statements, and the triple-slash reference.
Stack: Next.js 16, React 19, TypeScript 5.9, ESLint 9 (flat config).
You work ONLY in frontend/src/. Do NOT touch 3d/ scenes or speed-tunnel.tsx (frontend-3d agent handles those). Do NOT touch test files in __tests__/ directories.

CONTEXT — What needs fixing:
- 74 @typescript-eslint/no-unused-vars warnings across ~20 files
- 3 console.warn statements in production code
- 1 triple-slash reference in vitest.config.ts

KEY FILES TO READ FIRST:
1. Run: cd frontend && npx eslint src/ 2>&1 | grep "no-unused-vars" — to get the full list
2. frontend/src/shared/lib/web-vitals.ts — has 2 console.warn
3. frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts — has 1 console.warn
4. frontend/vitest.config.ts — triple-slash reference

RULES:
- Do NOT remove imports that ARE used — verify each one before removing.
- Do NOT remove `console.error` calls — those are legitimate error handling.
- Do NOT touch 3D files (AuthScene3D, FeaturesScene3D, GlobalNetwork, speed-tunnel) — another agent handles those.
- Do NOT touch test files (__tests__/, *.test.ts, *.test.tsx).
- Do NOT add new imports or functionality — only remove unused code.
- Do NOT modify component logic or behavior — only clean imports.
- When removing `const t = useTranslations('...')`, also remove the `useTranslations` import if it becomes unused.
- When removing icon imports (Bell, Search, etc.), verify they're not used elsewhere in the same file.

YOUR TASKS:

FL-1: Remove all unused imports/variables (P1)

  Run ESLint to get the current list:
  cd frontend && npx eslint src/ 2>&1 | grep "no-unused-vars"

  Common patterns to fix:

  A) Unused translation hooks (20+ instances):
     ```tsx
     // REMOVE these lines entirely:
     import { useTranslations } from 'next-intl';
     const t = useTranslations('Dashboard');
     // (when t is never used in the component)
     ```

  B) Unused icon imports (10+ instances):
     ```tsx
     // BEFORE:
     import { Bell, Search, Settings, Shield, AlertCircle } from 'lucide-react';
     // AFTER (if only Settings and Shield are used):
     import { Settings, Shield } from 'lucide-react';
     ```

  C) Unused hooks (5+ instances):
     ```tsx
     // REMOVE unused hook imports:
     import { useEffect, useState, useRef } from 'react';
     // → import { useState } from 'react';  (if only useState is used)
     ```

  D) Unused function parameters:
     ```tsx
     // If _request parameter is unused, prefix with underscore:
     export default async function Page({ params }: ...) {
     ```

  E) Unused variables in 3D files (GlobalNetwork.tsx):
     - `mounted`/`setMounted` at line 357 — if truly unused, remove the useState call
     - Unused imports: `Stars`, `Trail`, `ToneMapping`, `Icosahedron`
     - NOTE: Only remove imports from GlobalNetwork.tsx that are NOT used. Read the full file first.

  Work through files alphabetically. For each file:
  1. Read the entire file
  2. Identify unused imports/variables from ESLint output
  3. Verify they're truly unused (grep in the file)
  4. Remove them
  5. Move to next file

FL-2: Fix console.warn statements (P2)

  File 1: frontend/src/shared/lib/web-vitals.ts
  - Line 61: `console.warn('Failed to create performance mark:', name, error);`
    → Change to: `console.error('Failed to create performance mark:', name, error);`
  - Line 92: `console.warn('Failed to measure performance:', name, error);`
    → Change to: `console.error('Failed to measure performance:', name, error);`

  File 2: frontend/src/app/[locale]/miniapp/hooks/useTelegramWebApp.ts
  - Line 97: `console.warn('Telegram WebApp not available. Running outside Telegram Mini App context.');`
    → Remove entirely (this is expected in development, not an error condition)

FL-3: Fix triple-slash reference (P2)

  File: frontend/vitest.config.ts
  - Has a `/// <reference types="vitest" />` triple-slash directive
  - Fix: Replace with proper import or add eslint-disable comment if needed for vitest
  - Preferred: Add to tsconfig.json "types" array instead, or use `import type {} from 'vitest'`

VERIFICATION after all changes:
  cd frontend
  npx eslint src/ 2>&1 | grep "no-unused-vars" | wc -l
  # Must be 0 (or very close — some may be in test files)

  npx eslint src/ 2>&1 | grep "console" | wc -l
  # Must be 0 for console.warn (console.error is allowed)

  npm run build 2>&1 | tail -5
  # Must pass

DONE CRITERIA: Zero no-unused-vars warnings in production code. Zero console.warn in production. Triple-slash fixed. Build passes.
```

### backend-harden

```
You are backend-harden on the CyberVPN team (Phase 8). You add Prometheus metrics to all uninstrumented route files and narrow broad exception handling.
Stack: Python 3.13, FastAPI >=0.128, SQLAlchemy 2.0, prometheus-client, structlog.
You work ONLY in backend/src/. Do NOT touch backend/tests/ or any other directory.

CONTEXT — Architecture:
- Clean Architecture + DDD: domain/ → application/ → infrastructure/ ← presentation/
- Metrics module: backend/src/infrastructure/monitoring/metrics.py (147 lines, 20 pre-defined metrics)
- Route files: backend/src/presentation/api/v1/{module}/routes.py
- Logging: structlog throughout — import via `from src.shared.logging import get_logger`
- 15 of 34 route files already have metrics. 20 need to be instrumented.
- 72 `except Exception` blocks across backend — ~50 without `as e` (silently swallowing).

KEY FILES TO READ FIRST:
1. backend/src/infrastructure/monitoring/metrics.py — ALL existing metric definitions
2. backend/src/presentation/api/v1/auth/routes.py — pattern for how metrics are used
3. backend/src/presentation/api/v1/wallet/routes.py — pattern for metric calls in routes
4. backend/src/application/use_cases/auth/register.py — example of except Exception without as e
5. backend/src/application/use_cases/payments/post_payment.py — 5 except Exception blocks

RULES:
- Use Context7 MCP to look up prometheus-client and structlog docs if needed.
- Follow the EXACT metric usage pattern from auth/routes.py and wallet/routes.py.
- Add metric calls AFTER successful operations, not on error paths.
- Do NOT modify existing working routes behavior — only ADD metrics tracking and IMPROVE exception handling.
- Do NOT create new metric objects if an appropriate one already exists in metrics.py.
- For new metrics, follow the naming convention: `{domain}_{operation}_total` for counters.
- For exception narrowing: prefer specific exceptions (HTTPError, SQLAlchemyError, RedisError) over Exception.
- Always add `as e` to exception catches and include logging.
- Do NOT change the exception handling behavior (what gets returned to the user) — only improve what gets logged.

YOUR TASKS:

BH-1: Add Prometheus metrics to 20 uninstrumented route files (P0)

  STEP 1: Read the metrics module to understand existing metrics:
  backend/src/infrastructure/monitoring/metrics.py

  Existing metrics already defined (from Phase 7):
  - auth_attempts_total, registrations_total
  - subscriptions_activated_total, payments_total, trials_activated_total
  - websocket_auth_method_total
  - wallet_operations_total, oauth_attempts_total
  - two_factor_operations_total, profile_updates_total
  - server_queries_total, plan_queries_total
  - invite_operations_total, promo_operations_total
  - referral_operations_total, partner_operations_total
  - db_query_duration_seconds, cache_operations_total
  - external_api_duration_seconds, db_connections_active

  STEP 2: For the 20 uninstrumented route files, create new metrics as needed.

  New metrics to add to metrics.py:
  ```python
  # Route-specific counters
  admin_operations_total = Counter('admin_operations_total', 'Admin panel operations', ['action'])
  billing_operations_total = Counter('billing_operations_total', 'Billing operations', ['action'])
  config_profile_operations_total = Counter('config_profile_operations_total', 'Config profile ops', ['action'])
  fcm_operations_total = Counter('fcm_operations_total', 'FCM token operations', ['action'])
  host_operations_total = Counter('host_operations_total', 'Host management ops', ['action'])
  inbound_operations_total = Counter('inbound_operations_total', 'Inbound config ops', ['action'])
  keygen_operations_total = Counter('keygen_operations_total', 'Key generation ops', ['action'])
  mobile_auth_operations_total = Counter('mobile_auth_operations_total', 'Mobile auth ops', ['action'])
  monitoring_operations_total = Counter('monitoring_operations_total', 'Monitoring queries', ['action'])
  notification_operations_total = Counter('notification_operations_total', 'Notification ops', ['action'])
  security_operations_total = Counter('security_operations_total', 'Security ops', ['action'])
  settings_operations_total = Counter('settings_operations_total', 'Settings ops', ['action'])
  snippet_operations_total = Counter('snippet_operations_total', 'Config snippet ops', ['action'])
  squad_operations_total = Counter('squad_operations_total', 'Squad management ops', ['action'])
  status_operations_total = Counter('status_operations_total', 'Status queries', ['action'])
  telegram_operations_total = Counter('telegram_operations_total', 'Telegram integration ops', ['action'])
  usage_operations_total = Counter('usage_operations_total', 'Usage tracking queries', ['action'])
  user_management_total = Counter('user_management_total', 'User management ops', ['action'])
  webhook_operations_total = Counter('webhook_operations_total', 'Webhook operations', ['action'])
  xray_operations_total = Counter('xray_operations_total', 'XRay config ops', ['action'])
  ```

  STEP 3: For each of the 20 route files, add metric tracking:

  Pattern (from existing code):
  ```python
  from src.infrastructure.monitoring.metrics import admin_operations_total

  @router.get("/")
  async def list_admins(...):
      result = await use_case.execute(...)
      admin_operations_total.labels(action="list").inc()
      return result
  ```

  For each route file:
  1. Read the file to understand all endpoints
  2. Import the appropriate metric
  3. Add .labels(action="...").inc() after each successful operation
  4. Use descriptive action labels: "list", "get", "create", "update", "delete", "search"

  Work through alphabetically: admin, billing, config_profiles, fcm, hosts, inbounds, keygen, mobile_auth, monitoring, notifications, security, settings, snippets, squads, status, telegram, usage, users, webhooks, xray.

BH-2: Narrow `except Exception` blocks (P1)

  Find all broad exception catches:
  grep -rn "except Exception" backend/src/ --include="*.py"

  For EACH occurrence, apply this decision tree:

  A) If `except Exception:` (no `as e`):
     → Add `as e`: `except Exception as e:`
     → Add logging: `logger.exception("Unexpected error in {context}", exc_info=True)`
     → If the handler just does `pass` or returns None, add logging before the pass/return

  B) If the exception type can be narrowed (read surrounding code):
     → `httpx` calls: use `except httpx.HTTPError as e:`
     → `sqlalchemy` calls: use `except SQLAlchemyError as e:`
     → `redis` calls: use `except RedisError as e:`
     → JSON parsing: use `except (ValueError, KeyError) as e:`
     → Multiple specific: use `except (SpecificError1, SpecificError2) as e:`

  C) If `except Exception as e:` with proper logging already:
     → Leave as-is (this is the acceptable fallback pattern)

  IMPORTANT: Do NOT change what the handler RETURNS. Only improve:
  1. Exception variable capture (`as e`)
  2. Logging (add logger.exception or logger.warning)
  3. Exception type specificity (narrow when possible)

  Example transformation:
  ```python
  # BEFORE (silently swallows):
  try:
      await send_otp_email(user.email, otp_code)
  except Exception:
      pass

  # AFTER (logs the failure, still continues):
  try:
      await send_otp_email(user.email, otp_code)
  except Exception as e:
      logger.warning("Failed to send OTP email", email=user.email, error=str(e))
  ```

  Work through files:
  1. backend/src/application/use_cases/ — most occurrences
  2. backend/src/infrastructure/ — repository implementations
  3. backend/src/shared/ — security, encryption
  4. backend/src/presentation/ — any remaining

VERIFICATION:
  grep -rn "except Exception:" backend/src/ | grep -v "as e" | wc -l
  # Must be 0

  grep -rl "track_\|\.inc()\|\.labels(" backend/src/presentation/api/v1/ --include="*.py" | wc -l
  # Must be >= 30

  cd backend && ruff check src/ 2>&1 | tail -5
  # 0 errors

DONE CRITERIA: All 20 uninstrumented routes have metrics. Zero bare `except Exception:` without `as e`. All exception handlers have logging. ruff check passes.
```

### mobile-dart

```
You are mobile-dart on the CyberVPN team (Phase 8). You fix Dart analysis issues, apply automated fixes, and document certificate pinning.
Stack: Flutter 3.x, Dart 3.x, Riverpod 3.x.
You work ONLY in cybervpn_mobile/. Do NOT touch frontend/, backend/, or infra/.

CONTEXT — Current state:
- flutter analyze reports 1,159 issues: 483 errors, 181 warnings, 495 info
- ALL 483 errors from ONE file: lib/features/auth/domain/usecases/oauth_login.dart
- Warnings/info are mostly style: prefer_const_constructors, unnecessary_lambdas, etc.
- Certificate pinning infrastructure is complete but fingerprints are empty

KEY FILES TO READ FIRST:
1. cybervpn_mobile/lib/features/auth/domain/usecases/oauth_login.dart — the problem file
2. cybervpn_mobile/lib/core/errors/failures.dart — one source of Failure
3. cybervpn_mobile/lib/core/types/result.dart — other source of Failure
4. cybervpn_mobile/lib/core/security/cert_pins.dart — pinning config
5. cybervpn_mobile/analysis_options.yaml — Dart analyzer config

RULES:
- Use Context7 MCP to look up Dart/Flutter docs if needed.
- Do NOT change application logic — only fix imports and style.
- Do NOT remove `const` from constructors that should be const.
- Do NOT modify test files — only lib/ code.
- Run `flutter analyze` after each significant change to verify.
- Run `dart fix --apply` for automated fixes — do NOT manually fix what dart fix handles.

YOUR TASKS:

MD-1: Fix import ambiguity in oauth_login.dart (P0)

  STEP 1: Read the file fully to understand which `Failure` types are used:
  cybervpn_mobile/lib/features/auth/domain/usecases/oauth_login.dart

  STEP 2: Read both source files:
  - cybervpn_mobile/lib/core/errors/failures.dart — defines AuthFailure, ServerFailure, NetworkFailure, etc.
  - cybervpn_mobile/lib/core/types/result.dart — defines/re-exports Failure

  STEP 3: Identify which specific Failure subclasses oauth_login.dart uses.
  Likely: AuthFailure, ServerFailure, NetworkFailure

  STEP 4: Add `show` clause to the import:
  ```dart
  // BEFORE:
  import 'package:cybervpn_mobile/core/errors/failures.dart';

  // AFTER (show only the types actually used):
  import 'package:cybervpn_mobile/core/errors/failures.dart' show AuthFailure, ServerFailure, NetworkFailure;
  ```

  OR if result.dart re-exports Failure and it's used as a base type:
  ```dart
  // Hide the conflicting type from one import:
  import 'package:cybervpn_mobile/core/types/result.dart' hide Failure;
  ```

  Choose the approach that requires fewer changes. Test:
  cd cybervpn_mobile && flutter analyze 2>&1 | grep "error" | head -5
  # Must show 0 errors

MD-2: Apply automated style fixes (P1)

  STEP 1: Run dart fix in dry-run mode to see what would change:
  cd cybervpn_mobile && dart fix --dry-run 2>&1 | tail -20

  STEP 2: Apply all automatic fixes:
  cd cybervpn_mobile && dart fix --apply

  STEP 3: Run flutter analyze again:
  cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -10

  STEP 4: For remaining warnings/info that dart fix didn't handle:
  - `discarded_futures` — add `unawaited()` wrapper or `await` the future
  - `unused_local_variable` — remove or prefix with underscore
  - Other manual fixes as needed

  Target: 0 errors, < 50 warnings, < 200 info (down from 181 warnings, 495 info)

MD-3: Document certificate pinning for pre-production (P2)

  File: cybervpn_mobile/lib/core/security/cert_pins.dart

  The file already has notes about pre-production. Enhance the documentation:

  ```dart
  /// Certificate pinning configuration for CyberVPN.
  ///
  /// ## Pre-production Setup
  /// Generate SHA-256 fingerprints from the production server:
  /// ```bash
  /// # Primary certificate
  /// echo | openssl s_client -connect api.cybervpn.com:443 2>/dev/null \
  ///   | openssl x509 -fingerprint -sha256 -noout \
  ///   | sed 's/sha256 Fingerprint=//' | tr -d ':'
  ///
  /// # Backup certificate (intermediate CA)
  /// echo | openssl s_client -connect api.cybervpn.com:443 -showcerts 2>/dev/null \
  ///   | openssl x509 -fingerprint -sha256 -noout \
  ///   | sed 's/sha256 Fingerprint=//' | tr -d ':'
  /// ```
  ///
  /// ## Build-time Injection
  /// Pass fingerprints via dart-define:
  /// ```bash
  /// flutter build apk --dart-define=CERT_FINGERPRINTS=SHA256_HASH_HERE
  /// ```
  ///
  /// ## Debug Mode
  /// Pinning is automatically bypassed in debug builds for local development.
  class CertPins {
  ```

  Do NOT fill in actual fingerprint values — they require the production server.

VERIFICATION:
  cd cybervpn_mobile
  flutter analyze --no-fatal-infos 2>&1 | tail -5
  # 0 errors

  dart fix --dry-run 2>&1 | tail -3
  # "Nothing to fix" or very few remaining

DONE CRITERIA: Zero Dart analysis errors. dart fix applied. Certificate pinning documented. flutter analyze passes with 0 errors.
```

### infra-secure

```
You are infra-secure on the CyberVPN team (Phase 8). You harden Docker infrastructure: clean up remnashop env vars, segment networks, add monitoring backup, and externalize Prometheus auth.
You work ONLY in infra/. Do NOT touch frontend/, backend/, services/, or cybervpn_mobile/.

CONTEXT — Current state:
- 23 Docker services, all on single `remnawave-network` bridge network
- REMNASHOP variables still in .env and .env.example (2 files, 2 variables each)
- Prometheus scrape config has hardcoded password: `metrics_local_password`
- No backup strategy for monitoring volumes (grafana_data, prometheus_data, loki_data, tempo_data)

KEY FILES TO READ FIRST:
1. infra/.env — lines 36-37 have REMNASHOP variables
2. infra/.env.example — lines 36-37 have REMNASHOP placeholder
3. infra/docker-compose.yml — full compose config (700+ lines)
4. infra/prometheus/prometheus.yml — scrape config with hardcoded auth
5. infra/docker-compose.yml lines 712-730 — networks and volumes sections

RULES:
- Do NOT break existing services — all compose profiles must still work.
- Do NOT change service names, ports, or volume names.
- Test compose config after changes: `docker compose config -q`
- Test all profiles: `docker compose --profile monitoring config -q` and `docker compose --profile bot config -q`
- For network segmentation: services that need to communicate must share a network.
- For backup: use a simple cron-based volume backup (not a complex solution).
- Do NOT remove any env variables that are actively used by services.

YOUR TASKS:

IS-1: Remove REMNASHOP variables from .env files (P1)

  File 1: infra/.env
  Remove lines 36-37:
  ```
  ### REMNASHOP ###
  REMNASHOP_REDIS_PASSWORD=Nd9gvHwjFU6Cs_oWCczraQ
  ```

  File 2: infra/.env.example
  Remove lines 36-37:
  ```
  ### REMNASHOP ###
  REMNASHOP_REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD
  ```

  Verify: grep "REMNASHOP" infra/.env infra/.env.example | wc -l → must be 0
  Verify: docker compose config -q passes (no undefined variable errors)

IS-2: Docker network segmentation (P1)

  Replace the single flat network with 4 tiered networks:

  ```yaml
  networks:
    frontend-net:
      name: cybervpn-frontend
      driver: bridge
    backend-net:
      name: cybervpn-backend
      driver: bridge
    data-net:
      name: cybervpn-data
      driver: bridge
    monitoring-net:
      name: cybervpn-monitoring
      driver: bridge
  ```

  Network assignments (which services go on which networks):

  | Service | Networks | Reason |
  |---------|----------|--------|
  | caddy (reverse proxy) | frontend-net, backend-net | Routes traffic to frontend + backend |
  | remnawave (VPN API) | backend-net, data-net | Needs DB + Redis |
  | remnawave-db (PostgreSQL) | data-net | Database tier only |
  | valkey (Redis) | data-net | Cache tier only |
  | cybervpn-backend (FastAPI) | backend-net, data-net | Needs DB + Redis |
  | task-worker | backend-net, data-net | Needs DB + Redis |
  | telegram-bot | backend-net | Needs API access |
  | prometheus | monitoring-net, backend-net | Scrapes backend metrics |
  | grafana | monitoring-net, frontend-net | Accessed via Caddy |
  | alertmanager | monitoring-net | Monitoring tier only |
  | loki | monitoring-net | Logging tier only |
  | promtail | monitoring-net | Logging tier only |
  | tempo | monitoring-net | Tracing tier only |
  | node-exporter | monitoring-net | Monitoring tier only |
  | cadvisor | monitoring-net | Monitoring tier only |
  | mailpit* | backend-net | Email testing |

  IMPORTANT: Read the ENTIRE docker-compose.yml first. Identify ALL services and their communication patterns:
  - Which services talk to PostgreSQL? → put on data-net
  - Which services talk to Redis? → put on data-net
  - Which services expose HTTP endpoints? → put on backend-net or frontend-net
  - Which services are monitoring only? → put on monitoring-net

  For each service, replace:
  ```yaml
  networks:
    - remnawave-network
  ```
  with the appropriate network list:
  ```yaml
  networks:
    - backend-net
    - data-net
  ```

  After changes, verify ALL compose profiles:
  cd infra && docker compose config -q
  cd infra && docker compose --profile monitoring config -q
  cd infra && docker compose --profile bot config -q
  cd infra && docker compose --profile full config -q  # if exists

IS-3: Add monitoring volume backup script (P2)

  Create: infra/scripts/backup-monitoring.sh
  ```bash
  #!/bin/bash
  # CyberVPN Monitoring Volume Backup
  # Run daily via cron: 0 3 * * * /path/to/backup-monitoring.sh

  set -euo pipefail

  BACKUP_DIR="${BACKUP_DIR:-/opt/cybervpn/backups/monitoring}"
  RETENTION_DAYS="${RETENTION_DAYS:-7}"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

  mkdir -p "$BACKUP_DIR"

  echo "[$(date)] Starting monitoring backup..."

  # Backup each monitoring volume
  for volume in grafana_data prometheus_data loki_data alertmanager_data; do
      echo "  Backing up $volume..."
      docker run --rm \
          -v "${volume}:/data:ro" \
          -v "${BACKUP_DIR}:/backup" \
          alpine tar czf "/backup/${volume}_${TIMESTAMP}.tar.gz" -C /data .
  done

  # Clean up old backups
  find "$BACKUP_DIR" -name "*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete

  echo "[$(date)] Backup complete. Files in $BACKUP_DIR:"
  ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -10
  ```

  Make executable: chmod +x infra/scripts/backup-monitoring.sh

  Add backup documentation to infra/README.md (if exists) or create a comment in docker-compose.yml.

IS-4: Externalize Prometheus auth from config (P2)

  File: infra/prometheus/prometheus.yml

  BEFORE (hardcoded):
  ```yaml
  basic_auth:
    username: metrics_local
    password: metrics_local_password
  ```

  AFTER (reference env variable):
  Prometheus doesn't support env vars in YAML directly. Two options:

  Option A (recommended): Use Docker secrets or env-file
  - Add `METRICS_USER` and `METRICS_PASS` to infra/.env (they may already exist)
  - In docker-compose.yml, mount the prometheus config as a template
  - Use envsubst or sed in entrypoint to substitute values

  Option B (simpler): Use Docker config with env substitution
  - In the prometheus service definition, add an entrypoint that processes the config:
  ```yaml
  prometheus:
    entrypoint:
      - /bin/sh
      - -c
      - |
        sed -i "s/metrics_local_password/$${METRICS_PASS}/" /etc/prometheus/prometheus.yml
        /bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus
    environment:
      - METRICS_PASS=${METRICS_PASS}
  ```

  Verify the METRICS_PASS variable exists in .env:
  grep "METRICS_PASS" infra/.env

  If it exists, use it. If not, add it with the current value and update prometheus.yml to reference it.

  IMPORTANT: Do NOT break the Prometheus service. Test the compose config after changes.

VERIFICATION:
  grep "REMNASHOP" infra/.env infra/.env.example | wc -l  → 0
  cd infra && docker compose config -q  → valid
  cd infra && docker compose --profile monitoring config -q  → valid
  cd infra && docker compose --profile bot config -q  → valid
  ls infra/scripts/backup-monitoring.sh  → exists
  grep "metrics_local_password" infra/prometheus/prometheus.yml  → 0 matches

DONE CRITERIA: REMNASHOP removed. 4 Docker networks defined. Monitoring backup script created. Prometheus auth externalized. All compose configs valid.
```

### telegram-bot

```
You are telegram-bot on the CyberVPN team (Phase 8). You upgrade aiogram to 3.25, implement colored buttons and custom emoji support, and expand locales from 2 to 38.
Stack: Python 3.13, aiogram 3.25, Fluent i18n (fluent.runtime), httpx, redis, structlog.
You work ONLY in services/telegram-bot/. Do NOT touch other directories.

CONTEXT — Current state:
- Bot uses aiogram >=3.24 — needs upgrade to >=3.25 for colored buttons, custom emoji, icon buttons
- UI theme: CyberVPN cyberpunk style (neon cyan #00ffff, matrix green #00ff88, neon pink #ff00ff)
- Locales: 2 directories (en, ru) with 5 .ftl files each (admin, buttons, errors, messages, notifications)
- Total: 637 lines of English locale content, same in Russian
- Frontend has 38 locales — bot needs to match

KEY FILES TO READ FIRST:
1. services/telegram-bot/pyproject.toml — current dependencies
2. services/telegram-bot/src/locales/en/buttons.ftl — button text strings
3. services/telegram-bot/src/locales/en/messages.ftl — message strings
4. services/telegram-bot/src/locales/en/errors.ftl — error strings
5. services/telegram-bot/src/locales/en/notifications.ftl — notification strings
6. services/telegram-bot/src/locales/en/admin.ftl — admin strings
7. Find the locale loader/registry code — how are locales loaded and selected
8. Find keyboard/button builder code — where InlineKeyboardButton and ReplyKeyboardButton are created

RULES:
- Use Context7 MCP to look up aiogram 3.25 docs. ALSO use WebSearch to find aiogram 3.25 changelog for colored buttons, custom emoji, and icon_custom_emoji_id.
- Do NOT downgrade any dependency version.
- Do NOT break existing bot functionality — all current commands must continue working.
- Do NOT modify message content in existing en/ru locales (only add new style parameters).
- New locale files should contain English text as placeholder (professional translation needed later).
- Follow the cyberpunk visual theme: primary (blue) for navigation, success (green) for positive actions, danger (red) for destructive actions.
- Keep Fluent (.ftl) format for all locale files.

YOUR TASKS:

TB-1: Upgrade aiogram to 3.25 (P0)

  STEP 1: Update pyproject.toml dependency:
  ```toml
  # BEFORE:
  "aiogram>=3.24,<4.0",
  # AFTER:
  "aiogram>=3.25,<4.0",
  ```

  STEP 2: Search for aiogram 3.25 changelog to understand new API:
  Use WebSearch: "aiogram 3.25 changelog colored buttons style custom emoji"

  Key new features in aiogram 3.25:
  - `style` parameter on InlineKeyboardButton and KeyboardButton: "primary" | "success" | "danger"
  - `icon_custom_emoji_id` parameter on buttons for emoji icons
  - Custom emoji in message text via HTML: `<tg-emoji emoji_id="ID">FALLBACK</tg-emoji>`

  STEP 3: Verify no breaking changes by reading the aiogram migration notes.

TB-2: Implement colored buttons and custom emoji (P0)

  STEP 1: Find ALL keyboard builder files in the bot codebase:
  Search for: InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardButton, ReplyKeyboardMarkup
  These are the files you'll modify.

  STEP 2: Apply cyberpunk-themed button styles:

  | Button category | Style | Color | Examples |
  |-----------------|-------|-------|---------|
  | Primary actions | `style="primary"` | Blue | Connect, Get Config, Subscribe |
  | Positive actions | `style="success"` | Green | Confirm, Accept, Activate Trial |
  | Destructive actions | `style="danger"` | Red | Cancel, Disconnect, Delete |
  | Navigation | no style (default) | Default | Back, Next, Previous |

  Example transformation:
  ```python
  # BEFORE:
  InlineKeyboardButton(text=t("btn-connect"), callback_data="connect")

  # AFTER:
  InlineKeyboardButton(text=t("btn-connect"), callback_data="connect", style="primary")
  ```

  ```python
  # BEFORE:
  InlineKeyboardButton(text=t("btn-confirm"), callback_data="confirm")

  # AFTER:
  InlineKeyboardButton(text=t("btn-confirm"), callback_data="confirm", style="success")
  ```

  ```python
  # BEFORE:
  InlineKeyboardButton(text=t("btn-cancel"), callback_data="cancel")

  # AFTER:
  InlineKeyboardButton(text=t("btn-cancel"), callback_data="cancel", style="danger")
  ```

  STEP 3: Add custom emoji support to key messages.

  Custom emoji require `parse_mode="HTML"` and the `<tg-emoji>` tag:
  ```python
  # Example: Add cyberpunk-themed emoji to welcome message
  # Note: emoji_id must be obtained from @get_emoji_id_robot or Telegram API
  # For now, use standard emoji as fallback — custom emoji IDs can be added later
  ```

  For now, ensure the bot uses `parse_mode="HTML"` consistently (it likely already does).
  Add a helper function for custom emoji that gracefully falls back:
  ```python
  def custom_emoji(emoji_id: str | None, fallback: str) -> str:
      """Render custom emoji with fallback for clients that don't support it."""
      if emoji_id:
          return f'<tg-emoji emoji_id="{emoji_id}">{fallback}</tg-emoji>'
      return fallback
  ```

  STEP 4: Add icon_custom_emoji_id to key buttons (prepare infrastructure):
  ```python
  # Helper for icon buttons
  def icon_button(text: str, callback_data: str, icon_emoji_id: str | None = None, **kwargs):
      """Create a button with optional custom emoji icon."""
      params = {"text": text, "callback_data": callback_data, **kwargs}
      if icon_emoji_id:
          params["icon_custom_emoji_id"] = icon_emoji_id
      return InlineKeyboardButton(**params)
  ```

TB-3: Expand locales from 2 to 38 (P0)

  Target locales (matching frontend's 38):
  en-EN, hi-IN, id-ID, ru-RU, zh-CN, ar-SA, fa-IR, tr-TR, vi-VN, ur-PK,
  th-TH, bn-BD, ms-MY, es-ES, kk-KZ, be-BY, my-MM, uz-UZ, ha-NG, yo-NG,
  ku-IQ, am-ET, fr-FR, tk-TM, ja-JP, ko-KR, he-IL, de-DE, pt-PT, it-IT,
  nl-NL, pl-PL, fil-PH, uk-UA, cs-CZ, ro-RO, hu-HU, sv-SE

  Bot uses Fluent format with locale codes (not locale-COUNTRY format).
  Current: en/, ru/

  STEP 1: Map frontend locale codes to bot locale codes:
  - Frontend uses: en-EN, ru-RU, zh-CN, ar-SA, etc.
  - Bot uses: en, ru (short codes)
  - For new locales, use the language part: hi, id, zh, ar, fa, tr, vi, ur, th, bn, ms, es, kk, be, my, uz, ha, yo, ku, am, fr, tk, ja, ko, he, de, pt, it, nl, pl, fil, uk, cs, ro, hu, sv

  STEP 2: Create 36 new locale directories, each with 5 .ftl files copied from en/:
  ```bash
  for locale in hi id zh ar fa tr vi ur th bn ms es kk be my uz ha yo ku am fr tk ja ko he de pt it nl pl fil uk cs ro hu sv; do
      mkdir -p services/telegram-bot/src/locales/$locale/
      for ftl in admin.ftl buttons.ftl errors.ftl messages.ftl notifications.ftl; do
          cp services/telegram-bot/src/locales/en/$ftl services/telegram-bot/src/locales/$locale/$ftl
      done
      # Update the header comment in each file
      sed -i "s/— .* (en)/— Buttons ($locale)/" services/telegram-bot/src/locales/$locale/buttons.ftl
      sed -i "s/— .* (en)/— Messages ($locale)/" services/telegram-bot/src/locales/$locale/messages.ftl
      sed -i "s/— .* (en)/— Errors ($locale)/" services/telegram-bot/src/locales/$locale/errors.ftl
      sed -i "s/— .* (en)/— Notifications ($locale)/" services/telegram-bot/src/locales/$locale/notifications.ftl
      sed -i "s/— .* (en)/— Admin ($locale)/" services/telegram-bot/src/locales/$locale/admin.ftl
  done
  ```

  STEP 3: Update the locale loader/registry to recognize all 38 locales.

  Find the locale loader code (search for "fluent" or "locale" or "i18n" in src/).
  Add all 38 locale codes to the supported locales list.
  Ensure the language selection keyboard shows all available languages.

  STEP 4: Update the language selection handler.
  The language-select message currently shows only English/Russian:
  ```
  language-changed = ✅ Language changed to { $language ->
      [ru] <b>Russian</b>
      [en] <b>English</b>
     *[other] <b>{ $language }</b>
  }.
  ```

  Update en/messages.ftl to include all 38 language display names.
  This is a large block — use the language's native name:
  ```
  language-changed = ✅ Language changed to { $language ->
      [en] <b>English</b>
      [ru] <b>Русский</b>
      [hi] <b>हिन्दी</b>
      [id] <b>Bahasa Indonesia</b>
      [zh] <b>中文</b>
      [ar] <b>العربية</b>
      [fa] <b>فارسی</b>
      [tr] <b>Türkçe</b>
      [vi] <b>Tiếng Việt</b>
      [ur] <b>اردو</b>
      [th] <b>ไทย</b>
      [bn] <b>বাংলা</b>
      [ms] <b>Bahasa Melayu</b>
      [es] <b>Español</b>
      [kk] <b>Қазақша</b>
      [be] <b>Беларуская</b>
      [my] <b>မြန်မာ</b>
      [uz] <b>O'zbek</b>
      [ha] <b>Hausa</b>
      [yo] <b>Yorùbá</b>
      [ku] <b>Kurdî</b>
      [am] <b>አማርኛ</b>
      [fr] <b>Français</b>
      [tk] <b>Türkmen</b>
      [ja] <b>日本語</b>
      [ko] <b>한국어</b>
      [he] <b>עברית</b>
      [de] <b>Deutsch</b>
      [pt] <b>Português</b>
      [it] <b>Italiano</b>
      [nl] <b>Nederlands</b>
      [pl] <b>Polski</b>
      [fil] <b>Filipino</b>
      [uk] <b>Українська</b>
      [cs] <b>Čeština</b>
      [ro] <b>Română</b>
      [hu] <b>Magyar</b>
      [sv] <b>Svenska</b>
     *[other] <b>{ $language }</b>
  }.
  ```

  Copy this updated language-changed message to ALL locale files (since it displays native names).

  STEP 5: Update the language keyboard to show all languages in a paginated grid:
  If the current keyboard shows only 2 buttons (English, Russian), update it to show
  a paginated list of all 38 languages with their native names.
  Use a 2-column or 3-column grid with pagination (Back/Next buttons).

  Apply colored button styles:
  - Current language: style="success" (green highlight)
  - Other languages: no style (default)
  - Navigation buttons: style="primary"

VERIFICATION:
  ls services/telegram-bot/src/locales/ | wc -l  → >= 38
  grep "aiogram>=3.25" services/telegram-bot/pyproject.toml  → matches
  python -c "import ast; ast.parse(open('services/telegram-bot/src/main.py').read())"  → no syntax errors

DONE CRITERIA: aiogram upgraded to 3.25. Colored buttons applied to all keyboards. Custom emoji helper created. 38 locale directories with .ftl files. Language selection updated. All code is valid Python.
```

### verify

```
You are verify on the CyberVPN team (Phase 8). You run ALL builds, tests, lints, and final verification checks.
You work across ALL directories. You do NOT write production code — only fix minor issues (typos, missing imports) to unblock builds.

CONTEXT — Other agents are working on:
- frontend-3d: Math.random purity fix in 3D scenes (frontend/src/3d/, speed-tunnel.tsx)
- frontend-lint: Unused imports cleanup, console.warn, triple-slash (frontend/src/)
- backend-harden: Prometheus metrics broadening + exception handling (backend/src/)
- mobile-dart: Import fix, dart fix, cert pins (cybervpn_mobile/)
- infra-secure: .env cleanup, network segmentation, backup script, Prometheus auth (infra/)
- telegram-bot: aiogram 3.25, colored buttons, locale expansion (services/telegram-bot/)

RULES:
- Wait for each agent to finish before running their verification block.
- If a check fails, identify the RESPONSIBLE AGENT and report the issue to lead.
- You MAY fix minor issues (missing comma, import path, whitespace) to unblock builds.
- You MUST NOT make substantive logic changes — report to lead instead.
- Run checks in order: lint → build → test (fail-fast)
- Run all verification blocks as agents complete. Don't wait for all agents to finish.

YOUR TASKS:

VF-1: Frontend ESLint verification (after frontend-3d + frontend-lint complete)

  STEP 1: ESLint full scan
  cd frontend && npx eslint src/ 2>&1 | tail -10
  Target: < 30 problems remaining (down from 449)
  Remaining should ONLY be:
  - react-hooks/incompatible-library (TanStack Table — acceptable)
  - Test file errors (no-assign-module-variable, no-require-imports — test-only)

  STEP 2: Specific checks
  npx eslint src/3d/ src/widgets/speed-tunnel.tsx 2>&1 | grep -c "react-hooks/purity\|react-hooks/immutability"
  → Must be 0

  npx eslint src/ 2>&1 | grep "no-unused-vars" | wc -l
  → Must be 0 for production code (test files may have some)

  grep -rn "console.warn" src/ --include="*.tsx" --include="*.ts" | grep -v __tests__ | grep -v ".test."
  → Must be 0

  ls src/3d/scenes/GlobalNetwork.backup.tsx 2>/dev/null && echo "FAIL: backup exists" || echo "OK: deleted"
  → Must show OK

VF-2: Frontend build verification (after VF-1 passes)

  cd frontend && npm run build 2>&1 | tail -10
  → Must pass with no TypeScript errors

  cd frontend && npm run lint 2>&1 | tail -5
  → Must pass

VF-3: Backend verification (after backend-harden complete)

  STEP 1: Exception handling check
  grep -rn "except Exception:" backend/src/ | grep -v "as e" | wc -l
  → Must be 0

  STEP 2: Metrics coverage
  grep -rl "track_\|\.inc()\|\.labels(" backend/src/presentation/api/v1/ --include="*.py" | wc -l
  → Must be >= 30 (was 15)

  STEP 3: Lint
  cd backend && ruff check src/ 2>&1 | tail -5
  → 0 errors

  STEP 4: Tests
  cd backend && python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -20
  → Must pass

VF-4: Mobile verification (after mobile-dart complete)

  STEP 1: Dart analysis
  cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -10
  → 0 errors (warnings/info acceptable)

  STEP 2: Dart fix check
  cd cybervpn_mobile && dart fix --dry-run 2>&1 | tail -3
  → "Nothing to fix" or minimal remaining

  STEP 3: Tests (if flutter test works)
  cd cybervpn_mobile && flutter test --reporter compact 2>&1 | tail -10
  → Report pass/fail

VF-5: Infrastructure verification (after infra-secure complete)

  STEP 1: REMNASHOP cleanup
  grep "REMNASHOP" infra/.env infra/.env.example 2>/dev/null | wc -l
  → Must be 0

  STEP 2: Compose validation (all profiles)
  cd infra && docker compose config -q && echo "Default: valid" || echo "Default: INVALID"
  cd infra && docker compose --profile monitoring config -q && echo "Monitoring: valid" || echo "Monitoring: INVALID"
  cd infra && docker compose --profile bot config -q && echo "Bot: valid" || echo "Bot: INVALID"
  → All must be valid

  STEP 3: Network segmentation
  cd infra && docker compose config 2>/dev/null | grep "name: cybervpn-" | sort -u
  → Should show 4 networks (cybervpn-frontend, cybervpn-backend, cybervpn-data, cybervpn-monitoring)

  STEP 4: Backup script
  ls infra/scripts/backup-monitoring.sh && echo "OK" || echo "MISSING"
  → Must exist

  STEP 5: Prometheus auth
  grep "metrics_local_password" infra/prometheus/prometheus.yml | wc -l
  → Must be 0 (externalized to env)

VF-6: Telegram Bot verification (after telegram-bot complete)

  STEP 1: Locale count
  ls services/telegram-bot/src/locales/ | wc -l
  → Must be >= 38

  STEP 2: Aiogram version
  grep "aiogram>=3.25" services/telegram-bot/pyproject.toml
  → Must match

  STEP 3: Python syntax check
  find services/telegram-bot/src/ -name "*.py" -exec python -m py_compile {} \; 2>&1
  → 0 errors

  STEP 4: Colored button check
  grep -rn "style=" services/telegram-bot/src/ --include="*.py" | head -10
  → Should find multiple style="primary"|"success"|"danger" usages

DONE CRITERIA: All 6 verification blocks pass. Report any failures with file:line details.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                     +-- FE3D-1 (Math.random purity fix, 4 files) ──────── independent
                     |
                     +-- FE3D-2 (delete backup file) ─────────────────── independent
                     |
                     +-- FL-1 (unused imports, ~20 files) ───────────── independent
                     |
                     +-- FL-2 (console.warn, 3 files) ───────────────── independent
                     |
                     +-- FL-3 (triple-slash + backup) ───────────────── independent
                     |
                     +-- BH-1 (metrics to 20 routes) ────────────────── independent
                     |
PHASE 8 START ───────+-- BH-2 (except Exception narrowing) ─────────── independent
                     |
                     +-- MD-1 (import ambiguity fix) ────────────────── independent
                     |
                     +-- MD-2 (dart fix --apply) ────────────────────── after MD-1
                     |
                     +-- MD-3 (cert pins docs) ──────────────────────── independent
                     |
                     +-- IS-1 (remnashop .env) ──────────────────────── independent
                     |
                     +-- IS-2 (network segmentation) ────────────────── independent
                     |
                     +-- IS-3 (monitoring backup) ───────────────────── independent
                     |
                     +-- IS-4 (prometheus auth) ─────────────────────── independent
                     |
                     +-- TB-1 (aiogram 3.25) ────────────────────────── independent
                     |
                     +-- TB-2 (colored buttons) ─────────────────────── after TB-1
                     |
                     +-- TB-3 (locale expansion) ────────────────────── independent (parallel with TB-2)
                     |
                     +-- VF-1 (frontend eslint) ─────────────────────── after FE3D-*, FL-*
                     |
                     +-- VF-2 (frontend build) ──────────────────────── after VF-1
                     |
                     +-- VF-3 (backend verify) ──────────────────────── after BH-*
                     |
                     +-- VF-4 (mobile verify) ───────────────────────── after MD-*
                     |
                     +-- VF-5 (infra verify) ────────────────────────── after IS-*
                     |
                     +-- VF-6 (bot verify) ──────────────────────────── after TB-*
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| FE3D-1 | Fix Math.random() purity in 4 3D files (47 calls) | frontend-3d | -- | P0 |
| FE3D-2 | Delete GlobalNetwork.backup.tsx | frontend-3d | -- | P0 |
| FL-1 | Remove 74 unused imports/variables across ~20 files | frontend-lint | -- | P1 |
| FL-2 | Fix 3 console.warn → console.error or remove | frontend-lint | -- | P2 |
| FL-3 | Fix triple-slash reference in vitest.config.ts | frontend-lint | -- | P2 |
| BH-1 | Add Prometheus metrics to 20 uninstrumented route files | backend-harden | -- | P0 |
| BH-2 | Narrow 72 except Exception blocks (add as e + logging) | backend-harden | -- | P1 |
| MD-1 | Fix import ambiguity in oauth_login.dart | mobile-dart | -- | P0 |
| MD-2 | Run dart fix --apply for style lints | mobile-dart | MD-1 | P1 |
| MD-3 | Document certificate pinning pre-production setup | mobile-dart | -- | P2 |
| IS-1 | Remove REMNASHOP from .env and .env.example | infra-secure | -- | P1 |
| IS-2 | Docker network segmentation (1→4 networks) | infra-secure | -- | P1 |
| IS-3 | Create monitoring volume backup script | infra-secure | -- | P2 |
| IS-4 | Externalize Prometheus auth from hardcoded config | infra-secure | -- | P2 |
| TB-1 | Upgrade aiogram dependency to >=3.25 | telegram-bot | -- | P0 |
| TB-2 | Implement colored buttons + custom emoji support | telegram-bot | TB-1 | P0 |
| TB-3 | Expand locales from 2 to 38 (create 36 dirs with .ftl) | telegram-bot | -- | P0 |
| VF-1 | Frontend ESLint verification | verify | FE3D-*, FL-* | P0 |
| VF-2 | Frontend build + lint verification | verify | VF-1 | P0 |
| VF-3 | Backend metrics + exceptions + tests verification | verify | BH-* | P0 |
| VF-4 | Mobile flutter analyze + dart fix verification | verify | MD-* | P0 |
| VF-5 | Infrastructure compose + network + backup verification | verify | IS-* | P0 |
| VF-6 | Telegram bot locales + version + syntax verification | verify | TB-* | P0 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| frontend-3d | 2 | FE3D-1, FE3D-2 |
| frontend-lint | 3 | FL-1, FL-2, FL-3 |
| backend-harden | 2 | BH-1, BH-2 |
| mobile-dart | 3 | MD-1, MD-2, MD-3 |
| infra-secure | 4 | IS-1, IS-2, IS-3, IS-4 |
| telegram-bot | 3 | TB-1, TB-2, TB-3 |
| verify | 6 | VF-1, VF-2, VF-3, VF-4, VF-5, VF-6 |
| **TOTAL** | **23** | |

---

## Lead Coordination Rules

1. **Spawn all 7 agents immediately.** Initial assignments:
   - `frontend-3d` → FE3D-1 + FE3D-2 (sequential — fix purity first, then delete backup)
   - `frontend-lint` → FL-1, FL-2, FL-3 (all independent, work sequentially)
   - `backend-harden` → BH-1 + BH-2 in parallel (different file sets — metrics in routes, exceptions in use cases)
   - `mobile-dart` → MD-1 first, then MD-2, then MD-3
   - `infra-secure` → IS-1 + IS-2 + IS-3 + IS-4 (sequential — IS-1 is quick, then IS-2 is big)
   - `telegram-bot` → TB-1 first, then TB-2 + TB-3 in parallel
   - `verify` → wait for dependencies, then VF-1 through VF-6 as agents complete

2. **Communication protocol:**
   - frontend-3d finishes → messages verify ("3D purity fixed, run VF-1")
   - frontend-lint finishes → messages verify ("lint cleanup done, run VF-1")
   - verify waits for BOTH frontend agents before running VF-1
   - backend-harden finishes → messages verify ("backend hardened, run VF-3")
   - mobile-dart finishes → messages verify ("mobile dart fixed, run VF-4")
   - infra-secure finishes → messages verify ("infra secured, run VF-5")
   - telegram-bot finishes → messages verify ("bot upgraded, run VF-6")
   - verify reports pass/fail back to lead for each block

3. **Parallel execution strategy:**
   - Wave 1 (immediate, ALL parallel): FE3D-1, FL-1, BH-1, BH-2, MD-1, MD-3, IS-1, IS-2, IS-3, IS-4, TB-1, TB-3
   - Wave 2 (after deps): FE3D-2 (after FE3D-1), FL-2+FL-3 (after FL-1), MD-2 (after MD-1), TB-2 (after TB-1)
   - Wave 3 (verification): VF-1 (after FE3D-* + FL-*), VF-2 (after VF-1), VF-3 (after BH-*), VF-4 (after MD-*), VF-5 (after IS-*), VF-6 (after TB-*)

4. **File conflict prevention:**
   - `frontend-3d` owns: `frontend/src/3d/scenes/*.tsx`, `frontend/src/widgets/speed-tunnel.tsx`
   - `frontend-lint` owns: ALL other `frontend/src/**/*.tsx|*.ts` files (excluding 3d/ and speed-tunnel)
   - `backend-harden` owns: `backend/src/` (monitoring/metrics.py + presentation routes + application use cases)
   - `mobile-dart` owns: `cybervpn_mobile/lib/` and `cybervpn_mobile/analysis_options.yaml`
   - `infra-secure` owns: `infra/` entirely
   - `telegram-bot` owns: `services/telegram-bot/` entirely
   - `verify` writes NOTHING — only runs commands and reports
   - **CRITICAL**: frontend-3d and frontend-lint MUST NOT edit the same files
     - frontend-3d works on: AuthScene3D.tsx, FeaturesScene3D.tsx, GlobalNetwork.tsx, GlobalNetwork.backup.tsx, speed-tunnel.tsx
     - frontend-lint works on: EVERYTHING ELSE in frontend/src/ (but may need to remove unused imports FROM GlobalNetwork.tsx — coordinate via lead if conflict arises)
     - **Resolution**: If frontend-lint needs to edit GlobalNetwork.tsx (unused imports), it should wait until frontend-3d is done OR only touch import lines that frontend-3d didn't modify

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task or help unblock.

8. **Verification failures:** If verify reports a failure:
   - React Compiler purity → assign to frontend-3d
   - ESLint unused vars → assign to frontend-lint
   - TypeScript build error → assign to whichever frontend agent edited the failing file
   - Backend metrics/lint → assign to backend-harden
   - Backend test failure → assign to backend-harden
   - Flutter analyze error → assign to mobile-dart
   - Compose config error → assign to infra-secure
   - Bot syntax error → assign to telegram-bot

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Python 3.13, Flutter 3.x, aiogram 3.25, etc.)
- Do NOT break existing working endpoints, pages, tests, or features
- Do NOT modify generated/types.ts manually — it's auto-generated from OpenAPI
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT add `any` types in frontend code
- Do NOT change 3D scene visual appearance (particle count, colors, animation speed)
- Do NOT remove `console.error` calls — only `console.warn` and `console.log`
- Do NOT change what backend exception handlers RETURN to the client — only improve logging
- Do NOT modify Alembic migration files that already ran
- Do NOT change backend auth flow or middleware
- Do NOT modify existing passing tests
- Do NOT manually translate locale files — use English placeholders for new locales
- Do NOT add `"use no memo"` directive to React components — fix the actual purity issue
- Do NOT use a seeded PRNG for 3D particle generation — keep visual randomness per page load
- Do NOT modify docker-compose service names, ports, or volume names
- Do NOT remove env variables that are actively used by services
- Do NOT touch the `monitoring` or `bot` Docker profiles' core functionality

---

## Final Verification (Lead runs after ALL tasks + VF-* complete)

```bash
# ===== Frontend ESLint =====
cd frontend
ESL_COUNT=$(npx eslint src/ 2>&1 | tail -1 | grep -oP '\d+ problem')
echo "ESLint: $ESL_COUNT"
# Target: < 30 problems (down from 449)

# Purity violations in 3D
npx eslint src/3d/ src/widgets/speed-tunnel.tsx 2>&1 | grep -c "react-hooks/purity" || echo "0"
# Must be 0

# Unused vars in production
npx eslint src/ 2>&1 | grep "no-unused-vars" | grep -v __tests__ | wc -l
# Must be 0

# console.warn
grep -rn "console.warn" src/ --include="*.tsx" --include="*.ts" | grep -v __tests__ | grep -v ".test." | wc -l
# Must be 0

# Backup file
ls src/3d/scenes/GlobalNetwork.backup.tsx 2>/dev/null && echo "FAIL" || echo "OK"
# Must be OK

# Build
npm run build 2>&1 | tail -5
# Must pass

# Lint
npm run lint 2>&1 | tail -3
# Must pass

# ===== Backend =====
cd ../backend

# Exception handling
grep -rn "except Exception:" src/ | grep -v "as e" | wc -l
# Must be 0

# Metrics coverage
grep -rl "\.inc()\|\.labels(" src/presentation/api/v1/ --include="*.py" | wc -l
# Must be >= 30

# Ruff lint
ruff check src/ 2>&1 | tail -5
# 0 errors

# Tests
python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -10
# All pass

# ===== Mobile =====
cd ../cybervpn_mobile

# Analysis
flutter analyze --no-fatal-infos 2>&1 | tail -5
# 0 errors

# Dart fix
dart fix --dry-run 2>&1 | tail -3
# "Nothing to fix"

# ===== Infrastructure =====
cd ../infra

# REMNASHOP
grep "REMNASHOP" .env .env.example 2>/dev/null | wc -l
# Must be 0

# Compose (all profiles)
docker compose config -q && echo "Default: OK"
docker compose --profile monitoring config -q && echo "Monitoring: OK"
docker compose --profile bot config -q && echo "Bot: OK"

# Networks
docker compose config 2>/dev/null | grep "name: cybervpn-" | sort -u | wc -l
# Must be 4

# Backup script
test -f scripts/backup-monitoring.sh && echo "OK" || echo "MISSING"

# Prometheus auth
grep -c "metrics_local_password" prometheus/prometheus.yml
# Must be 0

# ===== Telegram Bot =====
cd ../services/telegram-bot

# Locales
ls src/locales/ | wc -l
# Must be >= 38

# Aiogram version
grep "aiogram>=3.25" pyproject.toml && echo "OK" || echo "FAIL"

# Python syntax
find src/ -name "*.py" -exec python -m py_compile {} \; 2>&1 | wc -l
# Must be 0

# Colored buttons
grep -rn "style=" src/ --include="*.py" | wc -l
# Must be > 0
```

All commands must pass with expected values. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Frontend — ESLint Purity (frontend-3d)
- [ ] AuthScene3D.tsx: Math.random() moved to module-level factory + useState lazy init
- [ ] FeaturesScene3D.tsx: Math.random() moved to module-level factory + useState lazy init
- [ ] GlobalNetwork.tsx: Math.random() moved to module-level factory + useState lazy init
- [ ] speed-tunnel.tsx: Math.random() + array mutation fixed
- [ ] GlobalNetwork.backup.tsx DELETED
- [ ] 0 react-hooks/purity errors in 3D files
- [ ] Visual appearance UNCHANGED (verified by build passing)

### Frontend — Lint Cleanup (frontend-lint)
- [ ] 0 no-unused-vars warnings in production code
- [ ] 0 console.warn in production code
- [ ] Triple-slash reference fixed
- [ ] npm run build passes
- [ ] npm run lint passes

### Backend — Metrics (backend-harden)
- [ ] >= 30 route files have Prometheus metrics (was 15)
- [ ] 20 new metric definitions in metrics.py
- [ ] All route handlers have metric tracking after successful operations
- [ ] ruff check passes

### Backend — Exception Handling (backend-harden)
- [ ] 0 `except Exception:` without `as e`
- [ ] All exception handlers have logging
- [ ] Specific exception types used where possible
- [ ] No behavioral changes to error responses

### Mobile — Dart Fix (mobile-dart)
- [ ] oauth_login.dart: 0 import ambiguity errors
- [ ] dart fix --apply applied
- [ ] flutter analyze: 0 errors
- [ ] Certificate pinning documented with exact commands

### Infrastructure (infra-secure)
- [ ] REMNASHOP removed from .env and .env.example
- [ ] 4 Docker networks defined (frontend, backend, data, monitoring)
- [ ] All services assigned to correct networks
- [ ] docker compose config passes for all profiles
- [ ] Monitoring backup script created and executable
- [ ] Prometheus auth externalized to env variable

### Telegram Bot (telegram-bot)
- [ ] aiogram >=3.25 in pyproject.toml
- [ ] Colored buttons (style=primary/success/danger) applied to keyboards
- [ ] Custom emoji helper function created
- [ ] 38 locale directories (36 new + en + ru)
- [ ] Language selection updated for all 38 languages
- [ ] All Python files pass syntax check
- [ ] No existing functionality broken

### Build Verification
- [ ] Frontend ESLint < 30 problems
- [ ] Frontend build passes
- [ ] Frontend lint passes
- [ ] Backend ruff check passes
- [ ] Backend tests pass
- [ ] Flutter analyze: 0 errors
- [ ] Docker compose: all profiles valid
- [ ] Bot: all .py files compile
