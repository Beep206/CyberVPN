# PRD: Post-SEC-01 Migration Fixes & Frontend Quality

**Author:** Claude Code
**Date:** 2026-02-10
**Status:** Draft
**Epic:** POST-SEC01

---

## 1. Problem & Context

The SEC-01 migration to httpOnly cookies was completed successfully: the backend now sets/manages auth tokens via `Set-Cookie` headers, and `tokenStorage` in the frontend is a no-op shim. However, several frontend components still reference the old token-based API, creating broken auth flows and degraded UX. Additionally, installed tooling (TanStack Query, Ruff lint rules) is not wired up, the Dockerfile carries unnecessary bloat, and the monorepo workspace config is broken.

### Why Now

- **AuthGuard is broken in production.** `tokenStorage.hasTokens()` always returns `false`, so the session-recovery code path (`fetchUser()`) inside AuthGuard is **unreachable**. Users with valid httpOnly cookies get redirected to login on every dashboard page load. This is a P0 regression from the SEC-01 migration.
- **2-3 second auth latency.** Without edge-level cookie checks, every dashboard visit goes: render shell -> client-side `/auth/me` call -> redirect. Moving the check to the Next.js proxy eliminates the round-trip.
- **No loading indicators.** Dashboard page transitions show a blank screen -- no `loading.tsx` files exist under `(dashboard)/`.
- **TanStack Query installed but unused.** `@tanstack/react-query@5.87.4` is in `package.json` but no `QueryClientProvider` exists. Data grids fetch via raw axios with no caching, deduplication, or retry.
- **Dockerfile ships 200MB of build tools.** `build-essential` stays in the final image.
- **Ruff uses default rules.** Security (bandit), import sorting, bugbear checks are all missing.
- **`npm run dev` from root fails.** Workspace is `"admin"` but directory is `frontend/`.

---

## 2. Success Criteria

| # | Metric | Target |
|---|--------|--------|
| 1 | AuthGuard correctly restores sessions via httpOnly cookie | Users with valid session cookie land on dashboard without redirect loop |
| 2 | Edge auth redirect latency | Dashboard loads without client-side auth spinner for unauthenticated users (redirect happens at proxy level) |
| 3 | Page transition UX | Every `(dashboard)/` route shows a loading skeleton during navigation |
| 4 | TanStack Query active | `QueryClientProvider` wraps the app; at least ServersDataGrid uses `useQuery` |
| 5 | Docker image size | Final image < 250MB (currently ~450MB with build-essential) |
| 6 | Ruff lint coverage | `["E","F","I","B","UP","S","ASYNC"]` rules active; `ruff check .` passes CI |
| 7 | Monorepo root scripts work | `npm run dev` from repo root starts the frontend dev server |

---

## 3. Scope

### In Scope

Seven work items across frontend, backend, and infra.

### Out of Scope

- Migrating all data grids from mock data to real API (only the QueryClient wiring and one example migration).
- Removing the `tokenStorage` shim entirely (may break other consumers; defer).
- Backend auth endpoint changes (backend already correctly handles httpOnly cookies).
- Mobile app changes.

---

## 4. Detailed Requirements

### FIX-01: AuthGuard Session Recovery (High Priority)

**Problem:** `AuthGuard.tsx` calls `tokenStorage.hasTokens()` which always returns `false` (no-op shim after SEC-01). The `fetchUser()` recovery path is unreachable. Users with valid httpOnly cookies are redirected to login.

**Current flow (broken):**
```
AuthGuard mount
  -> isAuthenticated? NO (first load, store not hydrated yet)
  -> tokenStorage.hasTokens()? NO (always false)
  -> setIsChecking(false) -> redirect to /login
```

**Target flow:**
```
AuthGuard mount
  -> isAuthenticated? YES (from Zustand persist) -> render children
  -> isAuthenticated? NO -> fetchUser() via /auth/me
    -> 200: set isAuthenticated=true, render children
    -> 401: redirect to /login
```

**Implementation:**
1. Remove the `tokenStorage.hasTokens()` check entirely from `AuthGuard.tsx`.
2. If `isAuthenticated` is `false` and `isLoading` is `false`, always call `fetchUser()` to attempt session recovery via httpOnly cookie.
3. Only redirect to login after `fetchUser()` returns and `isAuthenticated` is still `false`.
4. Avoid double-fetching: if AuthProvider already called `fetchUser()` and set `isAuthenticated`, AuthGuard should respect that and skip the call.

**Files:**
- `frontend/src/features/auth/components/AuthGuard.tsx`

**Tests:**
- Unit test: AuthGuard calls `fetchUser()` when `isAuthenticated=false` (no `hasTokens` gate).
- Unit test: AuthGuard renders children when `fetchUser()` succeeds.
- Unit test: AuthGuard redirects to login when `fetchUser()` fails (401).
- Unit test: AuthGuard does not call `fetchUser()` if already `isAuthenticated=true`.

---

### FIX-02: Edge Auth Check in Proxy (High Priority)

**Problem:** `proxy.ts` only handles i18n via `next-intl`. No server-side auth check. With httpOnly cookies, the proxy can inspect the cookie and redirect unauthenticated users before any page rendering. Currently users see: loading spinner -> `/auth/me` request -> redirect (2-3 seconds wasted).

**Current proxy.ts comment:**
```
// Auth is handled client-side via Zustand store (tokens in localStorage).
```
This comment is outdated post-SEC-01. Auth is now via httpOnly cookies, which ARE visible to server-side code.

**Implementation:**
1. In `proxy.ts`, after i18n middleware, add a cookie presence check for `/(dashboard)/` routes.
2. Check for the auth cookie name (from backend `settings.COOKIE_NAME`, default `access_token` or similar -- verify actual cookie name).
3. If cookie is absent on a `/(dashboard)/` route, return `NextResponse.redirect()` to `/{locale}/login?redirect={originalPath}`.
4. If cookie is present, allow the request through (the cookie may be expired -- backend will return 401 and client-side AuthGuard handles that case).
5. Update or remove the outdated comment about client-side auth.

**Important:** This is a **fast-path optimization**, not a security boundary. The proxy only checks cookie **presence**, not validity. The backend remains the authority on session validity. AuthGuard remains as the client-side fallback for expired/invalid cookies.

**Files:**
- `frontend/src/proxy.ts`

**Tests:**
- Integration test: Request to `/en/dashboard/servers` without auth cookie -> 307 redirect to `/en/login`.
- Integration test: Request to `/en/dashboard/servers` with auth cookie -> passes through to page.
- Integration test: Request to `/en/login` without auth cookie -> no redirect (public route).

---

### FIX-03: Dashboard Loading States (Medium Priority)

**Problem:** No `loading.tsx` files exist under `frontend/src/app/[locale]/(dashboard)/`. Next.js App Router uses `loading.tsx` for automatic `<Suspense>` boundaries at the route level. Without them, page-to-page navigation (servers -> users -> analytics) shows no loading indicator.

**Implementation:**
1. Create a shared cyberpunk-themed loading skeleton component matching the dashboard design system (matrix-green, scanlines, JetBrains Mono).
2. Add `loading.tsx` at the `(dashboard)/` layout level to cover all child routes.
3. Optionally add route-specific `loading.tsx` for pages with distinct layouts (e.g., servers grid vs analytics charts).

**Design:**
- Animated pulse/scanline effect consistent with the cyberpunk theme.
- Use CSS only (no JS) to avoid hydration issues -- `loading.tsx` is a Server Component.
- Skeleton should approximate the page layout (sidebar stays, content area shows loading).

**Files:**
- `frontend/src/app/[locale]/(dashboard)/loading.tsx` (new)
- Optionally: `frontend/src/app/[locale]/(dashboard)/servers/loading.tsx`, etc.

**Tests:**
- Visual verification: navigate between dashboard pages and confirm loading skeleton appears.
- Snapshot test for loading component markup.

---

### FIX-04: TanStack Query Integration (Medium Priority)

**Problem:** `@tanstack/react-query@5.87.4` is installed in `package.json` but never initialized. No `QueryClientProvider` or `QueryClient` exists. All data fetching uses raw axios without caching, deduplication, retry, or background refetch.

**Implementation:**

**Phase 1 -- Wire up QueryClient (this PRD):**
1. Create `frontend/src/app/providers/query-provider.tsx` with `QueryClientProvider` and sensible defaults:
   - `staleTime: 60_000` (1 min)
   - `retry: 2` with exponential backoff
   - `refetchOnWindowFocus: true`
2. Add `QueryProvider` to the provider chain in root layout (after `AuthProvider`, before `SmoothScrollProvider`).
3. Add React Query DevTools in development mode (`@tanstack/react-query-devtools`).

**Phase 2 -- Migrate one data grid (this PRD, as example):**
4. Create a `useServers()` hook using `useQuery` that fetches from the servers API endpoint.
5. Refactor `ServersDataGrid` to use `useServers()` instead of mock data / direct axios.
6. Document the pattern for other grids to follow.

**Phase 3 -- Migrate remaining grids (future PRD):**
- UsersDataGrid, AnalyticsDashboard, etc.

**Files:**
- `frontend/src/app/providers/query-provider.tsx` (new)
- `frontend/src/app/[locale]/layout.tsx` (add QueryProvider to chain)
- `frontend/src/features/servers/hooks/useServers.ts` (new, example hook)
- `frontend/src/widgets/servers-data-grid.tsx` (refactor to use hook)

**Tests:**
- Unit test: QueryProvider renders without errors.
- Unit test: `useServers()` returns data, loading, and error states.
- Integration test: ServersDataGrid renders server data from `useServers()`.

---

### FIX-05: Multi-Stage Dockerfile (Medium Priority)

**Problem:** `backend/Dockerfile` installs `build-essential` (gcc, make, ~200MB) for compiling Python C-extensions and leaves it in the final image. This increases image size and attack surface.

**Current Dockerfile (single stage):**
```dockerfile
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ...
RUN pip install --no-cache-dir -e .
COPY . .
```

**Target Dockerfile (multi-stage):**
```dockerfile
# Stage 1: Builder
FROM python:3.13-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade "pip>=26.0"
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.13-slim
RUN groupadd -r cybervpn && useradd -r -g cybervpn cybervpn
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=cybervpn:cybervpn . .
USER cybervpn
EXPOSE 8000 9091
CMD ["python", "-m", "src.serve"]
```

**Key considerations:**
- Preserve the non-root `cybervpn` user (SEC-002).
- Preserve pip security upgrade (`pip>=26.0`).
- Copy only installed packages and binaries from builder, not build-essential.
- Use `pip install .` (not `-e .`) in builder since editable installs don't work across stages.
- Test that all C-extension packages (argon2-cffi, asyncpg, etc.) work correctly.

**Files:**
- `backend/Dockerfile`

**Tests:**
- Build image and verify size < 250MB.
- Run `docker run --rm <image> python -c "import argon2; import asyncpg; print('OK')"`.
- Run full test suite inside container.

---

### FIX-06: Ruff Lint Rules Configuration (Medium Priority)

**Problem:** `pyproject.toml` has `[tool.ruff]` with only `target-version` and `line-length`. The `[tool.ruff.lint]` section is missing. Per `CLAUDE.md`, the recommended ruleset is `["E", "F", "I", "B", "UP", "S", "ASYNC"]`. Currently Ruff uses only default rules -- no bandit security checks, no import sorting, no bugbear, no pyupgrade.

**Implementation:**
1. Add `[tool.ruff.lint]` section to `backend/pyproject.toml`:
   ```toml
   [tool.ruff.lint]
   select = ["E", "F", "I", "B", "UP", "S", "ASYNC"]

   [tool.ruff.lint.per-file-ignores]
   "tests/**" = ["S101"]  # Allow assert in tests

   [tool.ruff.lint.isort]
   known-first-party = ["src"]
   ```
2. Run `ruff check .` and fix all new violations.
3. Run `ruff check --fix .` for auto-fixable issues (import sorting, pyupgrade).
4. Manually review and fix bandit (S) and bugbear (B) findings.
5. Ensure `ruff check .` passes cleanly before merging.

**Files:**
- `backend/pyproject.toml`
- Any backend `.py` files flagged by new rules.

**Tests:**
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- Backend CI runs `ruff check .` (already in `backend-ci.yml`).

---

### FIX-07: Workspace Name Mismatch (Low Priority)

**Problem:** Root `package.json` has `"workspaces": ["admin", ...]` but the actual directory is `frontend/`. Running `npm run dev` from the repo root fails because npm can't find the `admin` workspace.

**Root package.json (current):**
```json
{
  "workspaces": ["admin", "apps/*", "services/*", "packages/*"],
  "scripts": {
    "dev": "npm run dev -w admin",
    "build": "npm run build -w admin",
    "lint": "npm run lint -w admin"
  }
}
```

**Implementation:**
1. Change `"admin"` to `"frontend"` in the `workspaces` array.
2. Update all `-w admin` references to `-w frontend` in the `scripts` section.
3. Verify `npm install` resolves correctly from root.
4. Verify `npm run dev`, `npm run build`, `npm run lint` from root work.

**Files:**
- `package.json` (root)

**Tests:**
- `npm run dev` from repo root starts the dev server on `:3000`.
- `npm run build` from repo root completes without errors.

---

## 5. Implementation Order & Dependencies

```
Phase 1 (Critical -- unblocks daily usage):
  FIX-01: AuthGuard ──────┐
  FIX-02: Edge proxy auth ─┤  (can be parallel, both touch auth flow)
                           │
Phase 2 (Quality -- improves DX and UX):
  FIX-03: loading.tsx      │  (independent)
  FIX-04: TanStack Query   │  (independent)
  FIX-05: Multi-stage Docker│  (independent)
  FIX-06: Ruff lint rules  │  (independent)
                           │
Phase 3 (Cleanup):         │
  FIX-07: Workspace name ──┘  (independent, low risk)
```

FIX-01 and FIX-02 should be done first as they fix the broken auth flow. All Phase 2 items are independent and can be parallelized. FIX-07 is trivial and can be done at any time.

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FIX-01 causes double `fetchUser()` calls (AuthProvider + AuthGuard) | Extra API call on every page load | Add a guard: skip `fetchUser()` if `isLoading` is already `true` or `isAuthenticated` is already `true` |
| FIX-02 proxy cookie check blocks valid users with expired cookies | User sees login page even though refresh could succeed | Proxy only checks cookie **presence**, not validity. Expired cookies pass through; backend handles refresh or 401 |
| FIX-05 multi-stage build breaks C-extension packages | Runtime ImportError in production | Test all C-extension imports in CI: `python -c "import argon2, asyncpg, ..."` |
| FIX-06 Ruff rules produce hundreds of violations | Large noisy diff | Run `ruff check --fix` for auto-fixes first, then address remaining manually in a focused commit |
| FIX-04 TanStack Query conflicts with existing axios interceptors | Double error handling, token refresh race | Wrap axios instance in a query function; let TanStack handle retry, axios handles interceptors |

---

## 7. Open Questions

1. **Auth cookie name:** What is the exact cookie name set by the backend? Need to verify in `backend/src/presentation/api/v1/auth/cookies.py` for FIX-02.
2. **React Query DevTools:** Should devtools be included in the production bundle (lazy-loaded) or dev-only? Recommend dev-only via dynamic import.
3. **Loading skeleton design:** Should loading states match page-specific layouts (grid skeleton for servers, chart skeleton for analytics) or use a single generic skeleton?
