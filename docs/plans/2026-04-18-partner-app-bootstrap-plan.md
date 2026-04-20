# Partner App Bootstrap And First Delivery Slice Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** create a separate `partner` Next.js application, structurally based on `admin`, then establish the first delivery slice of the canonical partner portal.

**Architecture:** bootstrap `partner` as a new workspace by copying the `admin` app skeleton, not by extending `frontend` routes. Reuse the `admin` app shell, providers, i18n, scripts, and shared infrastructure first; then replace admin-only sections with the canonical partner portal route skeleton and graft in registration/onboarding flows from `frontend`, because `admin` is login-centric while `frontend` already has the richer self-service auth flow.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.9, next-intl, Tailwind 4, Zustand, TanStack Query, existing CyberVPN API clients.

## Document Role

This document defines the bootstrap scaffold and first delivery slice for the separate `partner` app.

It does not redefine portal product scope.

Portal scope, lifecycle, and canonical IA are defined by:

- `2026-04-18-partner-portal-prd.md`
- `2026-04-18-partner-portal-ia-and-menu-map.md`
- `2026-04-18-partner-portal-status-and-visibility-matrix.md`
- `2026-04-18-partner-portal-surface-policy-matrix.md`

This bootstrap plan must stay aligned with those documents and must not shrink the portal back into a referral or payout-only cabinet.

---

## Recommended Direction

### Option A: New top-level workspace `partner/` cloned from `admin/`

**Recommendation:** use this.

Why:

- matches the repo shape that already exists: `admin/` and `frontend/` are separate workspaces;
- gives partner its own build, env, scripts, routing tree, and deployment surface;
- lets us keep the admin-grade shell and operational UI patterns;
- avoids mixing partner roles and partner IA into customer `frontend`.

### Option B: New workspace under `apps/partner/`

Use only if you want all product apps moved under `apps/*`.

Why it is weaker right now:

- current top-level workspaces are already `admin/` and `frontend/`;
- adding `partner/` beside them is the lowest-friction path;
- moving to `apps/*` can happen later if the monorepo is normalized.

### Option C: Extend `frontend` or `admin` in place

Do not use this as the main direction.

Why not:

- `frontend` is customer-facing;
- `admin` is staff-facing;
- partner needs its own auth rules, navigation, and release path even if it starts as a clone.

## Current Codebase Facts That Shape The Plan

`admin` already gives us the right app skeleton:

- separate workspace: `admin/package.json`
- separate Next config: `admin/next.config.ts`
- separate app router root: `admin/src/app`
- separate providers/i18n/scripts/shared libs
- shell and nav driven by `admin/src/features/admin-shell/config/section-registry.ts`

Important constraint:

- `admin` shell is the right base, but its auth store is role-gated for staff/admin access.
- `frontend` already has richer self-service registration and verification flows.

That means:

- copy `admin` as the app foundation;
- do **not** blindly copy `admin` auth behavior;
- registration and partner onboarding should come from `frontend` patterns, adapted into `partner`.

## Scope Boundary For The Bootstrap Slice

Copy from `admin`:

- workspace structure
- `package.json`, `tsconfig.json`, `next.config.ts`
- `scripts/`
- `src/app`, `src/app/providers`
- `src/i18n`
- `src/shared`
- shell widgets such as sidebar/header/layout
- API client infrastructure and test setup

Do not carry over as-is:

- `features/admin-shell/config/section-registry.ts`
- admin-only sections: `customers`, `commerce`, `governance`, `infrastructure`, `integrations`, `security`
- admin auth redirect logic that checks staff roles

Reuse selectively from `frontend`:

- registration flow
- email verification / OTP
- forgot/reset password flows if needed
- partner-facing UI and API usage patterns
- referral-adjacent reporting widgets only when they map into canonical portal areas such as codes, conversions, analytics, or finance

## Phase 0: Freeze The App Boundary

**Purpose:** prevent scope drift before copying anything.

**Decision for the first delivery slice:**

- create a new top-level workspace: `partner/`
- clone the `admin` app structure into it
- keep partner as a separate deployed app
- use admin shell patterns
- replace auth gating and navigation before building partner modules

**Files expected in this phase:**

- Create: `partner/package.json`
- Create: `partner/next.config.ts`
- Create: `partner/tsconfig.json`
- Create: `partner/scripts/*`
- Create: `partner/src/*`
- Modify: root `package.json` scripts to add `dev:partner`, `build:partner`, `lint:partner`

## Phase 1: Bootstrap The New Workspace From `admin`

**Purpose:** get a running `partner` app fast by copying the proven app skeleton.

**Copy source:**

- `admin/package.json`
- `admin/tsconfig.json`
- `admin/next.config.ts`
- `admin/scripts/`
- `admin/src/app/`
- `admin/src/i18n/`
- `admin/src/shared/`
- `admin/src/lib/`
- `admin/src/stores/`
- `admin/src/test/`
- shell widgets and supporting UI pieces needed for render

**Immediate rename pass after copy:**

- `vpn-admin` -> `vpn-partner`
- admin host/origin vars -> partner equivalents
- admin labels/metadata -> partner labels/metadata
- admin console copy -> partner portal copy

**Exit criteria:**

- `npm run dev -w partner` starts
- localized login screen renders
- dashboard shell renders with placeholder partner routes

## Phase 2: Strip Admin IA And Replace It With Canonical Partner IA

**Purpose:** stop the clone from thinking like an admin console.

**Remove or neutralize first:**

- `customers`
- `commerce`
- `governance`
- `infrastructure`
- `integrations`
- `security`

**Replace with the stable canonical route families:**

- `/dashboard`
- `/application`
- `/organization`
- `/team`
- `/programs`
- `/legal`
- `/codes`
- `/campaigns`
- `/conversions`
- `/analytics`
- `/finance`
- `/compliance`
- `/integrations`
- `/cases`
- `/notifications`
- `/settings`
- `/reseller`

**Primary files to replace:**

- `partner/src/features/admin-shell/config/section-registry.ts`
- `partner/src/widgets/dashboard-navigation.ts`
- `partner/src/widgets/cyber-sidebar.tsx`
- dashboard landing pages under `partner/src/app/[locale]/(dashboard)/...`

**Result:**

- app still looks like `admin` structurally
- but the information architecture is now partner-native
- route visibility may still be placeholder or gated, but the route map itself must already match the canonical portal package

## Phase 3: Rebuild Auth For Partner Access

**Purpose:** keep the admin shell, but remove admin-only access assumptions.

**Problem in copied `admin` code:**

- `admin/src/stores/auth-store.ts` explicitly checks admin/staff roles and forces access-denied behavior

**Plan:**

- fork `auth-store` logic into partner semantics
- keep login page shell from `admin`
- bring registration and verification mechanics from `frontend`
- add partner-specific post-auth redirect, for example `/${locale}/dashboard`
- add partner eligibility/onboarding logic after authentication

**Flows for the first delivery slice:**

1. `login`
2. `register`
3. `verify`
4. `forgot-password`
5. `reset-password`
6. optional `invite acceptance` or `partner code bind`

**Source guidance:**

- base login shell: `admin/src/app/[locale]/(auth)/login/*`
- registration and verification patterns: `frontend/src/app/[locale]/(auth)/*`

## Phase 4: Wire Bootstrap-Critical Portal Surfaces

**Purpose:** wire the first useful portal surfaces without pretending the full target-state backend already exists.

**Keep only the API areas needed for the first delivery slice:**

- auth
- partner workspace and application
- organization profile and team basics
- program and lane status
- contracts and policy acknowledgements
- codes and tracking summary
- notifications or applicant messaging
- analytics overview and finance readiness summary where contracts already exist
- profile/settings if they exist and are relevant

**Do not import entire admin domain surface unless necessary:**

- infrastructure
- governance
- staff security ops
- customer support tooling

**Required bootstrap page skeleton:**

- `/dashboard` -> status-aware home
- `/application` -> staged onboarding and requested-info flow
- `/organization` -> workspace business profile
- `/team` -> placeholder or early membership management
- `/programs` -> lane memberships and restrictions
- `/legal` -> contracts, policy history, acknowledgements
- `/codes` -> codes and tracking starter surface
- `/campaigns` -> placeholder or starter assets/enablement surface
- `/conversions` -> placeholder until conversion scope is ready
- `/analytics` -> placeholder or starter reporting
- `/finance` -> payout readiness and statement onboarding
- `/compliance` -> declarations, remediation, governance visibility
- `/integrations` -> placeholder until active or lane-enabled
- `/cases` -> support and applicant messaging
- `/notifications` -> inbox and lifecycle events
- `/settings` -> profile and portal security
- `/reseller` -> hidden placeholder until reseller lane is enabled

These routes are stable even when some modules ship as placeholders first.

## Phase 5: Migrate Partner UI From Existing App Surfaces

**Purpose:** reuse what already exists instead of rebuilding everything inside `partner`.

**Best sources to mine:**

- `frontend/src/app/[locale]/(dashboard)/partner/*`
- `frontend/src/app/[locale]/(dashboard)/referral/*` only for reusable reporting, ledger, or attribution widgets that fit canonical portal modules
- shared API clients in `frontend/src/lib/api/*`
- any partner widgets already present in `admin/src/lib/api/partner.ts` and related modules

**Migration rule:**

- port partner-facing UI into `partner/src/app/...`
- keep low-level API patterns aligned with existing generated types
- prefer moving small focused modules, not entire customer dashboard trees
- do not preserve customer-referral semantics as a top-level partner portal section

## Phase 6: Partner-Specific Hardening

**Purpose:** turn the copied app into a durable portal.

**Work:**

- split env vars for partner domain/origin
- add partner-specific metadata, robots, sitemap policy if needed
- add route tests for auth redirects and navigation
- add role/status checks for approved partner vs pending applicant
- remove leftover admin wording and dead routes
- review CSP/origins in `partner/next.config.ts`

**Exit criteria:**

- partner app runs independently
- partner app has its own scripts and workspace commands
- navigation is partner-only
- registration/login/onboarding are partner-correct
- first canonical portal pages are functional without admin-only dependencies

## Practical Execution Order

The fastest safe order is:

1. Phase 0: lock the app boundary.
2. Phase 1: copy `admin` into `partner`.
3. Phase 2: replace navigation and routes with the canonical portal skeleton.
4. Phase 3: replace auth semantics and add registration.
5. Phase 4: wire bootstrap-critical portal APIs and placeholders.
6. Phase 5: port existing partner-facing UI into the canonical modules.
7. Phase 6: harden and clean leftovers.

## First Execution Slice

If we start implementation now, the best first slice is:

1. create top-level `partner/` by cloning `admin/`
2. add root workspace scripts for `partner`
3. make the copied app boot under its own name
4. replace admin section registry with the canonical partner section registry
5. keep placeholder pages for the canonical partner route families
6. postpone registration wiring to the next slice

That gets us an actual separate app quickly and creates the correct foundation for menu, registration, and partner functionality.
