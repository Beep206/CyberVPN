# CyberVPN Phase 7 — FINAL Gap Closure — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close EVERY remaining gap across all 4 platforms. After this phase ZERO open issues remain.
> **Out of scope**: Certificate pinning values (require production certs), mobile ARB translation quality (needs human translators), AlertManager webhook URL (requires Telegram relay deployment).

---

## Goal

This is **Phase 7 — the FINAL phase**. Phases 1-6 built and polished the entire CyberVPN platform. Phase 7 closes every last remaining gap so the project is fully production-ready.

1. **Frontend per-route error boundaries** — Add `error.tsx`, `loading.tsx`, `not-found.tsx` to all 11 dashboard child routes
2. **Frontend root layout metadata** — Convert static `export const metadata` to `generateMetadata` for locale-aware SEO
3. **Backend FCM persistence** — Replace placeholder FCM routes with real SQLAlchemy model + repository + Alembic migration
4. **Backend test stubs** — Implement all 55 empty `pass` stubs across 6 test files (observability, magic_link, register, oauth_login, totp_encryption, di_container)
5. **Backend metrics broadening** — Add Prometheus counters to the 10 highest-traffic route modules (currently only 5/36 have metrics)
6. **Infrastructure remnashop cleanup** — Delete the `infra/remnashop/` directory (services already removed from compose in Phase 6)
7. **Mobile production TODOs** — Resolve or document all 37 TODO/FIXME markers in `cybervpn_mobile/lib/`
8. **Mobile test stubs** — Implement the 24 test files with TODO/placeholder stubs
9. **Pass all build/lint/test/analyze checks** across every platform

**Done criteria:**
1. `cd frontend && npm run build` passes
2. `cd frontend && npm run lint` passes
3. `cd frontend && npm run test:run` passes
4. `cd backend && python -m pytest tests/ -x -q --timeout=120` passes — zero `pass`-only test functions
5. `cd cybervpn_mobile && flutter analyze --no-fatal-infos` passes
6. Every dashboard child route has its own `error.tsx`, `loading.tsx`, `not-found.tsx` (11 routes x 3 files = 33 new files)
7. Root layout uses `generateMetadata` function (not `export const metadata`)
8. FCM routes persist tokens to database (no "placeholder" in docstrings)
9. `grep -r "^\s*pass$" backend/tests/ | wc -l` returns 0 (zero empty test stubs)
10. `ls infra/remnashop/ 2>/dev/null` returns nothing (directory deleted)
11. Backend route modules with metrics tracking >= 15 (currently 5)
12. `grep -c "TODO" cybervpn_mobile/lib/core/constants/api_constants.dart` = 0
13. Mobile test TODO/placeholder count reduced by >= 80%

---

## Current State Audit (Phase 7 starting point)

### What's DONE (from Phases 1-6)

| Component | Status | Detail |
|-----------|--------|--------|
| Backend 158 endpoints, 36+ route modules | All implemented | Auth, OAuth, payments, wallet, 2FA, codes, FCM(placeholder), etc. |
| Backend integration tests | **834 real test functions** | BUT 55 empty `pass` stubs across 6 files |
| Backend Prometheus metrics | 5/36 route modules | auth, payments, subscriptions, trial, ws |
| Backend rate limiting | Global + 10 endpoint-specific | All working |
| Frontend `any` types in production | **1 remaining** | CodesSection.tsx:32 `useState<any>` — Phase 6 missed `<any>` pattern |
| Frontend JSON-LD | Organization + WebSite + SoftwareApplication | 3 schemas in 2 layouts |
| Frontend SEO | robots.ts + sitemap.ts + opengraph-image.tsx | All exist |
| Frontend error/not-found/loading | 3 route GROUPS covered | (dashboard), (auth), (miniapp) — but NO per-child-route files |
| Frontend Sentry | 3 configs (client, server, edge) | Fully wired |
| Frontend i18n | 24 namespaces, 38 locales | All registered |
| Frontend tests | 51 files, all passing | PurchaseConfirmModal + WithdrawalModal stubs all implemented |
| Frontend `any` in test files | ~250 occurrences | Test `as any` casts are acceptable (MSW mocking) |
| Frontend frameloop | `"demand"` | Fixed in Phase 6 |
| Frontend React Compiler | Enabled, useMemo removed | Fixed in Phase 6 |
| Mobile 20 features | All wired | Wallet withdraw calls real repo, 2FA uses Random.secure() |
| Mobile tests | 194 files | 24 have TODO/placeholder stubs |
| Mobile 38 locales | All generated | Full i18n |
| Infra 23 services | 23/23 healthchecked | remnashop removed from compose in Phase 6 |
| Infra monitoring | 76 alert rules, 11 dashboards | Full stack |
| Infra Loki runbooks | wiki.cybervpn.internal | Fixed in Phase 6 |
| Infra Prometheus | cybervpn-backend commented out | Fixed in Phase 6 |

### What's STILL REMAINING (Phase 7 must fix ALL)

#### GAP-0: Frontend — 1 remaining `<any>` in production code

- File: `frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx` line 32
- Code: `const [promoDiscount, setPromoDiscount] = useState<any>(null);`
- Needs: Define `PromoDiscount` interface and replace `<any>` with `<PromoDiscount | null>`
- Note: Phase 6 eliminated all `: any` and `as any` patterns but missed `<any>` in generics

#### GAP-1: Frontend — 11 dashboard child routes missing per-route error boundaries (33 files needed)

All 11 child routes under `frontend/src/app/[locale]/(dashboard)/` rely on the parent group's `error.tsx`, `loading.tsx`, `not-found.tsx`. Per Next.js best practice (and per `frontend/CLAUDE.md` rule #9), every route should have its own set for granular error isolation.

Routes needing files:
1. `analytics/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
2. `dashboard/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
3. `monitoring/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
4. `partner/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
5. `payment-history/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
6. `referral/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
7. `servers/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
8. `settings/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
9. `subscriptions/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
10. `users/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`
11. `wallet/` — needs `error.tsx`, `loading.tsx`, `not-found.tsx`

Existing parent templates to follow:
- `frontend/src/app/[locale]/(dashboard)/error.tsx` — uses `<RouteErrorBoundary />`
- `frontend/src/app/[locale]/(dashboard)/loading.tsx` — dashboard skeleton with animate-pulse
- `frontend/src/app/[locale]/(dashboard)/not-found.tsx` — uses `<RouteNotFound />`

#### GAP-2: Frontend — Root layout uses static metadata

- File: `frontend/src/app/[locale]/layout.tsx` line 31
- Currently: `export const metadata: Metadata = { title: "VPN Command Center", ... }`
- Should be: `export async function generateMetadata({ params })` for locale-aware SEO
- Child layouts already use `generateMetadata` — this creates an inconsistency

#### GAP-3: Backend — FCM routes are placeholder (no persistence)

- File: `backend/src/presentation/api/v1/fcm/routes.py` (101 lines)
- Lines 9-11 explicitly say "placeholder implementation"
- POST `/users/me/fcm-token` — logs and returns mock response, does NOT save to DB
- DELETE `/users/me/fcm-token` — logs only, does NOT delete from DB
- Needs: SQLAlchemy model (`fcm_tokens` table), repository interface + implementation, Alembic migration, wired routes

#### GAP-4: Backend — 55 empty test stubs across 6 files

| File | Stubs | Test class/area |
|------|-------|-----------------|
| `tests/integration/test_observability.py` | 24 | MetricsEndpoint(3), ReadinessEndpoint(5), SentryInit(6), StructuredLogging(10) |
| `tests/integration/api/v1/oauth/test_oauth_login.py` | 15 | OAuth login flow stubs |
| `tests/integration/api/v1/auth/test_magic_link.py` | 7 | Magic link auth stubs |
| `tests/integration/api/v1/auth/test_register.py` | 5 | Registration flow stubs |
| `tests/test_di_container.py` | 2 | DI container stubs |
| `tests/security/test_totp_encryption.py` | 2 | TOTP encryption stubs |
| **TOTAL** | **55** | |

Every stub is an `async def test_*` with only `pass` as the body and TODO comments above.

#### GAP-5: Backend — Metrics coverage only 5/36 route modules

Currently instrumented:
- `auth/routes.py` — `track_auth_attempt`, `track_registration` (9 calls)
- `payments/routes.py` — `track_payment` (2 calls)
- `subscriptions/routes.py` — `track_subscription_activation` (1 call)
- `trial/routes.py` — `track_trial_activation` (1 call)
- `ws/auth.py` — `websocket_auth_method_total` (1 call)

Missing high-traffic modules needing metrics:
- `wallet/routes.py` — wallet operations (withdraw, balance, history)
- `oauth/routes.py` — OAuth login/callback flows
- `two_factor/routes.py` — 2FA verify/setup
- `profile/routes.py` — profile updates
- `servers/routes.py` — server list/status
- `plans/routes.py` — plan listing
- `invites/routes.py` — invite code operations
- `promo_codes/routes.py` — promo code validation
- `referral/routes.py` — referral operations
- `partners/routes.py` — partner dashboard

#### GAP-6: Infrastructure — remnashop remnants (directory + postgres init + README)

- Services removed from `docker-compose.yml` in Phase 6 ✓
- But these remnants still exist:
  1. `infra/remnashop/` directory with .env, .env.example, assets/translations/ru/
  2. `infra/postgres/init/001-create-remnashop.sql` — creates `remnashop` DB on init
  3. `infra/README.md` lines 121-122 reference remnashop
- Must: `rm -rf infra/remnashop/`, delete `001-create-remnashop.sql`, remove remnashop refs from README

#### GAP-7: Mobile — 37 TODO/FIXME markers in production code

Breakdown:
- `core/constants/api_constants.dart` — 12 TODOs (backend endpoint verification notes)
- `core/security/cert_pins.dart` — 3 TODOs (production cert fingerprints — OUT OF SCOPE, but need documenting)
- `core/security/app_attestation.dart` — 1 TODO (implement actual attestation)
- `core/network/api_client.dart` — 1 TODO (cert fingerprints config)
- `core/platform/quick_settings_channel.dart` — 1 TODO (connect logic)
- `core/l10n/arb/app_*.arb` — 8 TODOs (translation quality notes in zh, tr, ja, es, ko, fr, pt, de)
- `shared/services/ios_update_service.dart` — 1 TODO (App Store ID)
- `shared/services/version_service.dart` — 1 TODO (version endpoint)
- `features/auth/presentation/screens/register_screen.dart` — 1 TODO (OTP flow)
- `features/partner/data/datasources/partner_remote_ds.dart` — 5 TODOs (backend missing fields)
- `features/vpn/presentation/screens/connection_screen.dart` — 1 TODO (subscription provider)
- `features/referral/data/datasources/referral_remote_ds.dart` — 1 TODO (backend field)
- `features/onboarding/presentation/screens/permission_request_screen.dart` — 1 TODO (app settings nav)

#### GAP-8: Mobile — 24 test files with TODO/placeholder stubs

Top files by stub count:
- `diagnostics/data/services/diagnostic_service_test.dart` — 32 stubs
- `diagnostics/data/services/speed_test_service_test.dart` — 27 stubs
- `profile/data/repositories/profile_repository_impl_test.dart` — 20 stubs
- `config_import/data/parsers/subscription_url_parser_test.dart` — 19 stubs
- `notifications/data/datasources/notification_local_datasource_test.dart` — 15 stubs
- `referral/presentation/screens/referral_dashboard_screen_test.dart` — 12 stubs
- And 18 more files with 1-7 stubs each

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | -- | opus | all (coordination only) | -- | 0 |
| Frontend Route Files | `frontend-routes` | sonnet | `frontend/` | general-purpose | 3 |
| Backend FCM + Metrics | `backend-fcm` | sonnet | `backend/` | backend-dev | 3 |
| Backend Test Stubs | `backend-tests` | sonnet | `backend/` | test-runner | 1 |
| Infrastructure + Mobile Cleanup | `cleanup-agent` | sonnet | all | general-purpose | 3 |
| Mobile Test Stubs | `mobile-tests` | sonnet | `cybervpn_mobile/` | general-purpose | 1 |
| Build Verification | `verify` | sonnet | all | general-purpose | 4 |

---

## Spawn Prompts

### frontend-routes

```
You are frontend-routes on the CyberVPN team (Phase 7). You add per-route error boundaries, fix root layout metadata, and fix the last remaining `any` type.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4.
You work ONLY in frontend/src/app/[locale]/(dashboard)/ and frontend/src/app/[locale]/layout.tsx.
Do NOT touch test files, generated files, or any other directories.

CONTEXT — What's already working:
- Parent group files exist at frontend/src/app/[locale]/(dashboard)/:
  - error.tsx — uses <RouteErrorBoundary error={error} reset={reset} />
  - loading.tsx — dashboard skeleton with animate-pulse stats and grid
  - not-found.tsx — uses <RouteNotFound />
- Shared components exist:
  - @/shared/ui/route-error-boundary (RouteErrorBoundary component)
  - @/shared/ui/route-not-found (RouteNotFound component)
- 11 child routes exist but NONE have their own error.tsx, loading.tsx, or not-found.tsx
- Root layout at frontend/src/app/[locale]/layout.tsx uses static `export const metadata`

KEY FILES TO READ FIRST:
1. frontend/src/app/[locale]/(dashboard)/error.tsx — template for error.tsx files
2. frontend/src/app/[locale]/(dashboard)/loading.tsx — template for loading.tsx files
3. frontend/src/app/[locale]/(dashboard)/not-found.tsx — template for not-found.tsx files
4. frontend/src/app/[locale]/layout.tsx — root layout to convert metadata

RULES:
- Use Context7 MCP to look up Next.js 16 docs for error.tsx, loading.tsx, and not-found.tsx conventions.
- Do NOT downgrade any library version.
- error.tsx files MUST be 'use client' components (Next.js requirement).
- loading.tsx files MUST be Server Components (no 'use client') with CSS-only animations.
- not-found.tsx files MUST be Server Components.
- Each loading.tsx should have a unique skeleton that reflects the page content (not copy-paste of parent).
- Follow the EXACT patterns from the parent group files — use the same shared components.

YOUR TASKS:

FR-1: Create error.tsx, loading.tsx, not-found.tsx for all 11 dashboard child routes (P0)

  For each of these 11 directories:
    analytics, dashboard, monitoring, partner, payment-history,
    referral, servers, settings, subscriptions, users, wallet

  Create 3 files in each directory (33 files total):

  **error.tsx** — Same pattern for all routes:
    ```tsx
    'use client';

    import { RouteErrorBoundary } from '@/shared/ui/route-error-boundary';

    export default function Error({
      error,
      reset,
    }: {
      error: Error & { digest?: string };
      reset: () => void;
    }) {
      return <RouteErrorBoundary error={error} reset={reset} />;
    }
    ```

  **not-found.tsx** — Same pattern for all routes:
    ```tsx
    import { RouteNotFound } from '@/shared/ui/route-not-found';

    export default function NotFound() {
      return <RouteNotFound />;
    }
    ```

  **loading.tsx** — UNIQUE per route. Each loading skeleton should reflect the page:
    - analytics: Chart placeholders (3 chart skeletons + stats row)
    - dashboard: Main dashboard overview skeleton (stats cards + activity feed)
    - monitoring: Service status grid skeleton (status cards + bandwidth chart)
    - partner: Partner dashboard skeleton (stats + codes table)
    - payment-history: Payment table skeleton (table rows + filter bar)
    - referral: Referral stats skeleton (invite link + referral table)
    - servers: Server grid skeleton (server cards in grid)
    - settings: Settings form skeleton (sections with input fields)
    - subscriptions: Subscription cards skeleton (plan cards + active sub)
    - users: Users table skeleton (search bar + table rows)
    - wallet: Wallet balance skeleton (balance card + transactions table)

  Each loading.tsx pattern:
    ```tsx
    export default function Loading() {
      return (
        <div className="space-y-6 p-6">
          {/* Route-specific skeleton with animate-pulse */}
          <div className="h-8 w-48 bg-grid-line/20 rounded animate-pulse" />
          {/* ... more skeleton elements ... */}
        </div>
      );
    }
    ```

  Use CSS-only animations (animate-pulse). No client-side JS. No 'use client'.
  Use the cyberpunk design system classes: bg-terminal-bg, border-grid-line, bg-grid-line/20, rounded.

  Verify: All 33 files exist after creation.
    for dir in analytics dashboard monitoring partner payment-history referral servers settings subscriptions users wallet; do
      for f in error.tsx loading.tsx not-found.tsx; do
        ls "frontend/src/app/[locale]/(dashboard)/$dir/$f"
      done
    done

FR-2: Fix last remaining `any` in CodesSection.tsx (P0)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx
  - Line 32: `const [promoDiscount, setPromoDiscount] = useState<any>(null);`
  - Read the component to see how promoDiscount is used (lines 265-296 show the shape)
  - Define a local interface:
    ```tsx
    interface PromoDiscount {
      discount_percent?: number;
      discount_amount?: number;
      expires_at?: string;
    }
    ```
  - Replace: `useState<any>(null)` → `useState<PromoDiscount | null>(null)`
  - Verify: grep "<any>" in this file returns 0 matches
  - Verify: grep "any" frontend/src/app/ --include="*.tsx" -r | grep -v __tests__ | grep -v generated/ | grep -v node_modules returns 0

FR-3: Convert root layout to generateMetadata (P1)
  - File: frontend/src/app/[locale]/layout.tsx
  - Current (line 31-40):
    ```tsx
    export const metadata: Metadata = {
        title: "VPN Command Center",
        description: "Advanced Cyberpunk VPN Admin Interface",
        metadataBase: new URL('https://vpn-admin.example.com'),
        alternates: {
            languages: Object.fromEntries(
                locales.map((locale) => [locale, `/${locale}`])
            ),
        },
    };
    ```
  - Replace with:
    ```tsx
    export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
        const { locale } = await params;
        return {
            title: "VPN Command Center",
            description: "Advanced Cyberpunk VPN Admin Interface",
            metadataBase: new URL('https://vpn-admin.example.com'),
            alternates: {
                languages: Object.fromEntries(
                    locales.map((l) => [l, `/${l}`])
                ),
                canonical: `/${locale}`,
            },
        };
    }
    ```
  - This makes it consistent with child layouts that use generateMetadata
  - The `locale` param is now available for future locale-specific titles/descriptions
  - Keep the `import type { Metadata } from "next"` import
  - Verify: `npm run build` passes after change

DONE CRITERIA: All 33 per-route files exist. CodesSection.tsx has zero `any` types. Root layout uses generateMetadata. npm run build passes. npm run lint passes.
```

### backend-fcm

```
You are backend-fcm on the CyberVPN team (Phase 7). You implement real FCM token persistence and broaden Prometheus metrics coverage.
Stack: Python 3.13, FastAPI >=0.128, SQLAlchemy 2.0 (async), Alembic, asyncpg, Pydantic v2.
You work ONLY in backend/. Do NOT touch frontend/, cybervpn_mobile/, or infra/.

CONTEXT — Architecture:
- Clean Architecture + DDD: domain/ → application/ → infrastructure/ ← presentation/
- Domain layer: zero framework imports (pure Python entities, repository interfaces)
- Infrastructure: SQLAlchemy repos, Redis cache, httpx clients
- Presentation: thin FastAPI routes that delegate to use cases
- Existing patterns in auth, wallet, payments modules demonstrate the full stack

KEY FILES TO READ FIRST — Study these to understand existing patterns:
1. backend/src/presentation/api/v1/fcm/routes.py — current placeholder (101 lines)
2. backend/src/presentation/api/v1/fcm/schemas.py — existing Pydantic schemas (FCMTokenRequest, FCMTokenDeleteRequest, FCMTokenResponse)
3. backend/src/domain/entities/ — look at ANY existing entity for pattern (e.g., user.py)
4. backend/src/domain/repositories/ — look at ANY existing repo interface (e.g., user_repository.py)
5. backend/src/infrastructure/database/models/ — look at ANY existing ORM model
6. backend/src/infrastructure/repositories/ — look at ANY existing repo implementation
7. backend/alembic/versions/ — see the latest migration for naming/numbering pattern
8. backend/src/infrastructure/metrics/ — see existing Prometheus metric definitions
9. backend/src/presentation/api/v1/auth/routes.py — see how metrics are tracked (track_auth_attempt pattern)
10. backend/src/presentation/api/v1/wallet/routes.py — high-traffic module needing metrics

RULES:
- Use Context7 MCP to look up SQLAlchemy 2.0 async docs and Alembic docs before writing code.
- Follow the EXACT patterns from existing domain entities, repository interfaces, and implementations.
- Domain layer: NO SQLAlchemy imports, NO FastAPI imports — pure Python only.
- All routes MUST be async def. Use Depends() for dependency injection.
- Alembic migration: use `op.create_table()` — do NOT import models in migration.
- Pydantic schemas: use model_config = ConfigDict(from_attributes=True).
- Test the migration logic mentally — FK to admin_users(id), unique constraint on (user_id, device_id).
- Do NOT modify existing working tests or routes. Only add new code and modify FCM routes.

YOUR TASKS:

BF-1: Implement FCM token persistence — full DDD stack (P0)

  STEP 1: Create domain entity
    File: backend/src/domain/entities/fcm_token.py
    ```python
    import uuid
    from datetime import datetime
    from dataclasses import dataclass

    @dataclass
    class FCMToken:
        id: uuid.UUID
        user_id: uuid.UUID
        token: str
        device_id: str
        platform: str  # "android" | "ios"
        created_at: datetime
        updated_at: datetime
    ```

  STEP 2: Create domain repository interface
    File: backend/src/domain/repositories/fcm_token_repository.py
    ```python
    from abc import ABC, abstractmethod
    import uuid
    from domain.entities.fcm_token import FCMToken

    class FCMTokenRepository(ABC):
        @abstractmethod
        async def upsert(self, token: FCMToken) -> FCMToken: ...

        @abstractmethod
        async def delete_by_device(self, user_id: uuid.UUID, device_id: str) -> bool: ...

        @abstractmethod
        async def get_by_user(self, user_id: uuid.UUID) -> list[FCMToken]: ...
    ```
    Note: Read existing repository interfaces to match the EXACT import pattern (may be `from src.domain...` not `from domain...`).

  STEP 3: Create SQLAlchemy ORM model
    File: backend/src/infrastructure/database/models/fcm_token.py
    - Table name: fcm_tokens
    - Columns: id (UUID PK), user_id (UUID FK→admin_users.id), token (String 512), device_id (String 255), platform (String 10), created_at, updated_at
    - Unique constraint on (user_id, device_id)
    - Index on user_id
    Follow the EXACT pattern of existing ORM models (Mapped[] + mapped_column).
    Import and register in the models __init__.py if one exists.

  STEP 4: Create infrastructure repository implementation
    File: backend/src/infrastructure/repositories/fcm_token_repository_impl.py
    - Implements FCMTokenRepository
    - Uses async SQLAlchemy session
    - upsert: INSERT ... ON CONFLICT (user_id, device_id) DO UPDATE SET token=, platform=, updated_at=
    - delete_by_device: DELETE WHERE user_id= AND device_id=
    - get_by_user: SELECT WHERE user_id=
    Follow existing repository implementation patterns.

  STEP 5: Create Alembic migration
    Read the latest migration in backend/alembic/versions/ to determine the revision numbering.
    File: backend/alembic/versions/XXXX_add_fcm_tokens_table.py
    ```python
    def upgrade():
        op.create_table(
            'fcm_tokens',
            sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', sa.Uuid(), sa.ForeignKey('admin_users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('token', sa.String(512), nullable=False),
            sa.Column('device_id', sa.String(255), nullable=False),
            sa.Column('platform', sa.String(10), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.UniqueConstraint('user_id', 'device_id', name='uq_fcm_tokens_user_device'),
        )
        op.create_index('ix_fcm_tokens_user_id', 'fcm_tokens', ['user_id'])

    def downgrade():
        op.drop_index('ix_fcm_tokens_user_id')
        op.drop_table('fcm_tokens')
    ```

  STEP 6: Wire routes to real repository
    File: backend/src/presentation/api/v1/fcm/routes.py
    - Import the repository from DI container or use Depends()
    - POST: create FCMToken entity, call repository.upsert(), return response
    - DELETE: call repository.delete_by_device(), return 204
    - Remove ALL "placeholder" mentions from docstrings and comments
    - Remove the import of `datetime` if no longer needed inline
    Verify: grep "placeholder" in fcm/routes.py returns 0

  STEP 7: Register in DI container
    Read how other repositories are registered (likely in a dependencies.py or container.py file).
    Add FCMTokenRepository → FCMTokenRepositoryImpl binding.

BF-2: Add Prometheus metrics to 10 route modules (P1)

  Currently only 5/36 modules have metrics. Add counters to these 10 high-traffic modules:

  For each module, follow the pattern from auth/routes.py:
  1. Import or create a Prometheus Counter in the metrics module
  2. Add .labels(...).inc() calls at the appropriate points in route handlers

  Read backend/src/infrastructure/metrics/ to understand the existing metrics setup.
  Read backend/src/presentation/api/v1/auth/routes.py to see the track_auth_attempt pattern.

  Modules to instrument:
  1. wallet/routes.py — track_wallet_operation(operation="withdraw|deposit|balance")
  2. oauth/routes.py — track_oauth_attempt(provider="google|apple|telegram|...")
  3. two_factor/routes.py — track_2fa_operation(operation="setup|verify|disable")
  4. profile/routes.py — track_profile_update(field="avatar|name|email|...")
  5. servers/routes.py — track_server_query(action="list|detail|status")
  6. plans/routes.py — track_plan_query(action="list|detail")
  7. invites/routes.py — track_invite_operation(action="create|redeem|list")
  8. promo_codes/routes.py — track_promo_operation(action="validate|apply")
  9. referral/routes.py — track_referral_operation(action="dashboard|earnings|withdraw")
  10. partners/routes.py — track_partner_operation(action="dashboard|codes|earnings")

  For each:
  - Define counter in metrics module (or inline if that's the pattern)
  - Add metric calls AFTER successful operations (not on error paths)
  - Use descriptive label names matching the route purpose

BF-3: Create integration tests for FCM endpoints (P1)
  File: backend/tests/integration/api/v1/fcm/test_fcm_tokens.py

  Create proper integration tests (NOT stubs):
  - test_register_fcm_token_success — POST valid token, assert 201, check DB
  - test_register_fcm_token_upsert — POST same device_id twice, assert only 1 row
  - test_register_fcm_token_unauthenticated — no auth header, assert 401
  - test_unregister_fcm_token_success — DELETE after register, assert 204
  - test_unregister_fcm_token_nonexistent — DELETE without register, assert 204 (idempotent)
  - test_register_fcm_token_invalid_platform — platform not android/ios, assert 422

  Follow existing integration test patterns (conftest fixtures, async_client, etc.).
  Each test MUST have real assertions — no `pass` stubs.

DONE CRITERIA: FCM routes persist to database. grep "placeholder" in fcm/ returns 0. 10 new route modules have metrics. FCM tests pass. python -m pytest tests/integration/api/v1/fcm/ passes.
```

### backend-tests

```
You are backend-tests on the CyberVPN team (Phase 7). You implement ALL 55 empty test stubs.
Stack: Python 3.13, pytest, pytest-asyncio (asyncio_mode=auto), httpx AsyncClient.
You work ONLY in backend/tests/. Do NOT modify backend/src/ or any other directory.

CONTEXT — What already exists:
- 834 real test functions across 64+ test files — all passing
- 55 empty `pass` stubs across 6 files (listed below)
- Each file already has working tests above the stubs — follow their patterns EXACTLY
- Test fixtures in conftest.py files — read them first

KEY FILES TO READ FIRST (read ALL before writing any test):
1. backend/tests/conftest.py — shared fixtures (async_client, db_session, etc.)
2. For each stub file, read the ENTIRE file to understand existing patterns, imports, fixtures

RULES:
- Use Context7 MCP to look up pytest-asyncio and httpx docs if needed.
- Follow EXACTLY the patterns from existing passing tests in the SAME file.
- Every test MUST have at least one assertion (assert). No empty tests. No pass. No TODO.
- Use existing fixtures — do not create new conftest files unless necessary.
- If a test requires infrastructure not available in test env (e.g., real Sentry DSN), mock it.
- Do NOT modify production code — ONLY test files.
- For observability tests that test metrics/logging: mock the metrics collection and assert calls.
- For auth tests: follow the existing auth test patterns for creating users and getting tokens.

YOUR TASKS:

BT-1: Implement ALL 55 test stubs (P0)

  === FILE 1: tests/integration/test_observability.py (24 stubs) ===

  Read the ENTIRE file first. Note: there's 1 passing test (test_metrics_endpoint_exists) — follow its pattern.

  TestMetricsEndpoint (3 stubs):
    test_metrics_excludes_health_and_docs_endpoints:
      - Make GET requests to /health, /docs, /metrics
      - GET /metrics
      - Parse body, assert these paths are NOT in http_requests_total labels
      - If metrics middleware doesn't track exclusions, assert the paths don't appear or mock

    test_metrics_includes_custom_application_metrics:
      - GET /metrics
      - Assert body contains expected custom metric names (auth_attempts_total, etc.)
      - If custom metrics not yet registered, check for at least process_* metrics and assert

    test_metrics_increments_after_request:
      - GET /metrics, parse initial count for a known metric
      - Make a request to /api/v1/status or /health
      - GET /metrics again
      - Assert the relevant counter increased

  TestReadinessEndpoint (5 stubs):
    test_readiness_endpoint_exists:
      - GET /health or /readiness
      - Assert 200

    test_readiness_returns_200_when_healthy:
      - GET /health
      - Assert 200 and body contains expected health status

    test_readiness_checks_database_connection:
      - GET /health
      - Assert response includes database status field

    test_readiness_checks_redis_connection:
      - GET /health
      - Assert response includes redis/cache status field

    test_readiness_handles_database_down:
      - Mock database to be unavailable
      - GET /health
      - Assert degraded status or 503

    (Note: if /health doesn't return detailed status, simplify to checking response structure)

  TestSentryInitialization (6 stubs):
    - Mock sentry_sdk or check sentry initialization
    - For each: import sentry_sdk, mock/patch as needed, assert configuration
    - If Sentry isn't initialized in test env, patch the init function and verify it was called with expected args
    - test_sentry_dsn_configured: Check settings have SENTRY_DSN (may already pass — check)
    - test_sentry_sdk_initialized: Mock sentry_sdk.init, run app startup, assert called
    - test_sentry_captures_exceptions: Mock capture_exception, raise in route, assert called
    - test_sentry_fastapi_integration: Check FastApiIntegration in integrations list
    - test_sentry_request_context: Mock scope, make request, assert request data attached
    - test_sentry_filters_sensitive_headers: Assert auth headers not in breadcrumbs

  TestStructuredLogging (10 stubs):
    - Test the logging configuration
    - test_log_json_format: Check logger output format is JSON
    - test_log_includes_timestamp: Assert "timestamp" or "time" in log output
    - test_log_includes_level: Assert "level" in log output
    - test_log_includes_message: Assert "message" or "msg" in log output
    - test_log_includes_request_id: Make request with X-Request-ID, check logs
    - test_log_includes_logger_name: Assert "logger" or "name" in log output
    - test_log_redacts_passwords: Log with password field, assert "***" or redacted
    - test_log_redacts_tokens: Log with token field, assert redacted
    - test_log_includes_exception_info: Log exception, assert traceback in output
    - test_log_levels_configurable: Set log level, assert lower levels filtered

    For logging tests: use caplog fixture or capture log output. If structured logging isn't implemented, test the standard Python logging config.

  === FILE 2: tests/integration/api/v1/oauth/test_oauth_login.py (15 stubs) ===

  Read the ENTIRE file. Follow existing patterns.
  These test OAuth login flows — mock external OAuth providers.
  For each stub: mock the OAuth provider response, call the endpoint, assert response.

  === FILE 3: tests/integration/api/v1/auth/test_magic_link.py (7 stubs) ===

  Read the ENTIRE file. Follow existing patterns.
  Tests magic link authentication — mock email sending, verify token.

  === FILE 4: tests/integration/api/v1/auth/test_register.py (5 stubs) ===

  Read the ENTIRE file. Follow existing patterns.
  Tests user registration flow.

  === FILE 5: tests/test_di_container.py (2 stubs) ===

  Read the ENTIRE file. Test DI container resolution.

  === FILE 6: tests/security/test_totp_encryption.py (2 stubs) ===

  Read the ENTIRE file. Test TOTP secret encryption/decryption.

DONE CRITERIA: grep "^\s*pass$" across all 6 files returns 0. All 55 tests have real assertions. python -m pytest tests/ -x -q passes.
```

### cleanup-agent

```
You are cleanup-agent on the CyberVPN team (Phase 7). You handle infrastructure cleanup and mobile production TODO resolution.
You work in infra/ and cybervpn_mobile/lib/. Do NOT touch frontend/ or backend/.

CONTEXT — What needs cleaning:
1. infra/remnashop/ directory still exists (services already removed from docker-compose in Phase 6)
2. 37 TODO/FIXME markers in cybervpn_mobile/lib/ production code need resolution

KEY FILES TO READ FIRST:
- cybervpn_mobile/lib/core/constants/api_constants.dart — 12 TODOs
- cybervpn_mobile/lib/core/security/cert_pins.dart — 3 TODOs
- cybervpn_mobile/lib/features/partner/data/datasources/partner_remote_ds.dart — 5 TODOs

RULES:
- Do NOT delete code that's functional — only clean up TODOs.
- For TODOs about missing backend endpoints: convert to doc comments (/// NOTE:) documenting the current state.
- For TODOs about cert pins: replace with "Pre-production: configure before release" notes.
- For ARB translation TODOs: these are @@comment fields — convert to neutral comments about translation source.
- Do NOT modify functional behavior — only comments and metadata.
- Run flutter analyze after changes.

YOUR TASKS:

CL-1: Delete ALL remnashop remnants (P0)
  STEP 1: Verify remnashop is not referenced in docker-compose:
    grep "remnashop" infra/docker-compose.yml
    Must return 0 matches (already removed in Phase 6)

  STEP 2: Delete the remnashop directory:
    rm -rf infra/remnashop/
    Verify: ls infra/remnashop/ 2>/dev/null && echo "FAIL" || echo "OK: deleted"

  STEP 3: Delete the postgres init script that creates remnashop database:
    File: infra/postgres/init/001-create-remnashop.sql
    This script creates a "remnashop" database on PostgreSQL startup — no longer needed.
    rm infra/postgres/init/001-create-remnashop.sql
    Verify: ls infra/postgres/init/001-create-remnashop.sql 2>/dev/null && echo "FAIL" || echo "OK: deleted"

  STEP 4: Remove remnashop references from infra/README.md:
    File: infra/README.md
    Lines ~121-122 mention remnashop. Remove or update those lines.
    Search: grep -n "remnashop" infra/README.md
    Edit out ALL references to remnashop from the README.

  STEP 5: Final verification:
    grep -r "remnashop" infra/ --include="*.yml" --include="*.yaml" --include="*.sql" --include="*.md"
    Must return 0 matches (except possibly in git history).

CL-2: Resolve all 37 TODO/FIXME in cybervpn_mobile/lib/ (P0)

  Strategy per category:

  **Category A: Backend endpoint verification TODOs (12 in api_constants.dart)**
  File: cybervpn_mobile/lib/core/constants/api_constants.dart
  Lines with "TODO: Backend needs to implement..." or "TODO: Verify backend..."
  These are documentation notes, not action items. Convert each:
    FROM: /// TODO: Backend needs to implement subscription cancellation endpoint
    TO:   /// Backend endpoint pending implementation. Mobile uses placeholder path.
  OR simply remove the TODO prefix:
    FROM: /// TODO: Verify backend registration implementation
    TO:   /// Note: Verify against backend registration implementation in `backend/src/...`

  **Category B: Certificate pin TODOs (3 in cert_pins.dart + 1 in api_client.dart)**
  File: cybervpn_mobile/lib/core/security/cert_pins.dart (lines 48, 60, 69)
  File: cybervpn_mobile/lib/core/network/api_client.dart (line 57)
  These are pre-production items. Convert:
    FROM: /// **TODO: Generate production fingerprint before release**
    TO:   /// Pre-production: Generate production fingerprint before release.
  Remove the TODO keyword but keep the note.

  **Category C: ARB translation comments (8 files)**
  Files: app_zh.arb, app_tr.arb, app_ja.arb, app_es.arb, app_ko.arb, app_fr.arb, app_pt.arb, app_de.arb
  Currently: "@@comment": "TODO: Professional translation required - Currently using English placeholders"
  Convert to: "@@comment": "Auto-generated from English. Professional translation recommended."
  This removes TODO while preserving the translation status note.

  **Category D: Feature-level TODOs (13 scattered)**
  For each, read the context and choose the right resolution:

  - app_attestation.dart:220 "TODO: Implement actual platform attestation"
    → Convert to: // Pre-production: Implement platform attestation (App Attest / Play Integrity)

  - quick_settings_channel.dart:101 "TODO: Implement connect logic when disconnected"
    → Convert to: // Note: Connect logic depends on VPN engine integration

  - ios_update_service.dart:14 "TODO: Replace with actual App Store ID"
    → Convert to: /// Pre-production: Replace with actual App Store ID once published.

  - version_service.dart:165 "TODO: Update this endpoint when backend implements"
    → Convert to: // Note: Update endpoint when backend version API is available

  - register_screen.dart:368 "TODO(backend): Once backend implements OTP verification flow"
    → Convert to: // Note(backend): OTP verification flow integration pending backend deployment

  - partner_remote_ds.dart (5 TODOs on lines ~143-165)
    → Convert each "TODO: Backend doesn't..." to "// Note: Backend doesn't provide this field yet — using default"

  - connection_screen.dart:481 "TODO: Wire to a real subscription provider"
    → Convert to: // Note: Wire to real subscription provider when available

  - referral_remote_ds.dart:106 "TODO: Backend doesn't provide this yet"
    → Convert to: // Note: Backend doesn't provide paidUsers yet — defaulting to 0

  - permission_request_screen.dart:226 "TODO: Implement navigation to app settings"
    → Convert to: // Note: App settings navigation depends on platform-specific implementation

  Verify after ALL changes:
    grep -c "TODO\|FIXME" cybervpn_mobile/lib/ -r --include="*.dart" --include="*.arb"
    Target: 0 (or close to 0 — some ARB files may have TODO in values, not comments)

CL-3: Verify mobile still analyzes clean (P1)
  Run: cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -10
  Must pass with 0 errors.

DONE CRITERIA: infra/remnashop/ deleted. TODO/FIXME count in cybervpn_mobile/lib/ reduced to 0. flutter analyze passes.
```

### mobile-tests

```
You are mobile-tests on the CyberVPN team (Phase 7). You implement all TODO/placeholder test stubs in the Flutter test suite.
Stack: Flutter 3.x, Dart 3.x, flutter_test, mocktail.
You work ONLY in cybervpn_mobile/test/. Do NOT modify production code in lib/.

CONTEXT — What already exists:
- 194 test files, most passing
- 24 files have TODO/placeholder stubs (ranging from 1 to 32 stubs per file)
- Existing passing tests demonstrate the mocking patterns (mocktail, ProviderContainer overrides)

KEY FILES TO READ FIRST:
1. cybervpn_mobile/test/helpers/ — test helpers and infrastructure
2. cybervpn_mobile/test/features/wallet/ — well-tested feature, good pattern reference
3. Read each stub file's existing passing tests before implementing stubs

RULES:
- Use Context7 MCP to look up mocktail and flutter_test docs if needed.
- Follow EXACTLY the patterns from existing passing tests in the SAME file.
- Every test MUST have at least one expect() assertion. No empty tests. No TODO.
- Use mocktail for mocking (Mock, when(), verify()).
- Use ProviderContainer for Riverpod provider overrides in tests.
- Do NOT modify production code — ONLY test files.
- Work through files in ORDER of stub count (highest first) for maximum impact.
- If a test requires complex infrastructure setup, create a minimal mock that satisfies the test.

YOUR TASKS:

MT-1: Implement all mobile test stubs (P0)

  Priority order (by stub count):

  1. test/features/diagnostics/data/services/diagnostic_service_test.dart (32 stubs)
     - Read the service being tested: lib/features/diagnostics/data/services/diagnostic_service.dart
     - Mock dependencies (network client, device info)
     - Implement all 32 test stubs with real assertions

  2. test/features/diagnostics/data/services/speed_test_service_test.dart (27 stubs)
     - Read the speed test service
     - Mock HTTP client, timer
     - Implement all 27 stubs

  3. test/features/profile/data/repositories/profile_repository_impl_test.dart (20 stubs)
     - Read the repository interface and implementation
     - Mock remote data source
     - Test all CRUD operations

  4. test/features/config_import/data/parsers/subscription_url_parser_test.dart (19 stubs)
     - Read the URL parser
     - Test various URL formats (valid, invalid, edge cases)
     - Pure logic tests — no mocks needed

  5. test/features/notifications/data/datasources/notification_local_datasource_test.dart (15 stubs)
     - Read the local datasource (likely SharedPreferences or Hive)
     - Mock storage
     - Test CRUD operations

  6. test/features/referral/presentation/screens/referral_dashboard_screen_test.dart (12 stubs)
     - Widget test with ProviderContainer overrides
     - Mock referral provider
     - Test UI states (loading, data, error)

  7-24. Remaining 18 files (1-7 stubs each):
     - shared/widgets/flag_widget_test.dart (7)
     - core/analytics/analytics_providers_test.dart (7)
     - helpers/auth_test_helpers.dart (6) — this is a helper file, may not need test implementation
     - features/referral/data/datasources/referral_remote_ds_test.dart (6)
     - features/auth/presentation/screens/register_screen_test.dart (5)
     - widget_test.dart (4)
     - features/onboarding/presentation/screens/onboarding_screen_test.dart (4)
     - features/auth/presentation/screens/login_screen_test.dart (4)
     - And 10 more with 1-2 stubs each

  For EACH test file:
  1. Read the ENTIRE test file to understand existing patterns
  2. Read the production code being tested
  3. Identify what each TODO stub should test (from test name and surrounding context)
  4. Implement with real assertions following the file's existing patterns
  5. Ensure no TODO/FIXME/placeholder text remains

DONE CRITERIA: grep -r "TODO\|FIXME\|placeholder\|stub" cybervpn_mobile/test/ --include="*.dart" | wc -l decreased by >= 80%. flutter test passes.
```

### verify

```
You are verify on the CyberVPN team (Phase 7). You run all builds, tests, and final verification checks.
You work across ALL directories. You do NOT write production code — only fix minor issues (typos, import errors) to unblock builds.

CONTEXT — Other agents are working on:
- frontend-routes: Per-route error boundaries + metadata fix (frontend/)
- backend-fcm: FCM persistence + metrics broadening (backend/)
- backend-tests: 55 test stub implementations (backend/tests/)
- cleanup-agent: infra/remnashop deletion + mobile TODO resolution (infra/, cybervpn_mobile/lib/)
- mobile-tests: Mobile test stub implementations (cybervpn_mobile/test/)

RULES:
- Wait for other agents to finish before running final verification.
- If a check fails, identify the RESPONSIBLE AGENT and report the issue.
- You MAY fix minor issues (typos, missing imports) to unblock builds.
- You MUST NOT make substantive logic changes — report to lead instead.
- Run checks in order: lint → build → test (fail-fast)

YOUR TASKS:

VF-1: Frontend verification (P0, after frontend-routes complete)
  STEP 1: Per-route file existence check
    for dir in analytics dashboard monitoring partner payment-history referral servers settings subscriptions users wallet; do
      for f in error.tsx loading.tsx not-found.tsx; do
        test -f "frontend/src/app/[locale]/(dashboard)/$dir/$f" && echo "OK: $dir/$f" || echo "MISSING: $dir/$f"
      done
    done
    All 33 files must show OK.

  STEP 2: Root layout metadata check
    grep "generateMetadata" frontend/src/app/[locale]/layout.tsx
    Must find generateMetadata function (not static export const metadata).

  STEP 2.5: Last any type check
    grep -rn "any" frontend/src/app/ --include="*.tsx" --include="*.ts" | grep -v __tests__ | grep -v generated/ | grep -v node_modules | grep -v "// " | grep -v "@ts-expect"
    Must return 0 matches for production code.

  STEP 3: Lint
    cd frontend && npm run lint
    Must pass with 0 errors.

  STEP 4: Build
    cd frontend && npm run build
    Must pass. If TypeScript errors, report to frontend-routes.

  STEP 5: Tests
    cd frontend && npm run test:run
    Must pass.

VF-2: Backend verification (P0, after backend-fcm + backend-tests complete)
  STEP 1: Check FCM persistence
    grep -c "placeholder" backend/src/presentation/api/v1/fcm/routes.py
    Must be 0.

    ls backend/src/domain/entities/fcm_token.py backend/src/domain/repositories/fcm_token_repository.py backend/src/infrastructure/repositories/fcm_token_repository_impl.py
    All 3 files must exist.

    ls backend/alembic/versions/*fcm* 2>/dev/null
    Migration file must exist.

  STEP 2: Check no pass stubs
    grep -rn "^\s*pass$" backend/tests/ --include="*.py" | grep -v __pycache__ | grep -v conftest
    Must return 0 matches (or only in non-test-function contexts like class bodies).

  STEP 3: Metrics coverage
    grep -rl "track_\|\.inc()\|\.observe()\|_total\.labels\|_counter\.labels" backend/src/presentation/api/v1/ --include="*.py" | wc -l
    Must be >= 15 (was 5, +10 new).

  STEP 4: Run tests
    cd backend && python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -20
    Must pass.

  STEP 5: Lint
    cd backend && ruff check src/ tests/ 2>&1 | tail -10
    Must pass (0 errors).

VF-3: Infrastructure verification (P0, after cleanup-agent complete)
  STEP 1: Remnashop removal — all remnants
    ls infra/remnashop/ 2>/dev/null && echo "FAIL: dir exists" || echo "OK: dir deleted"
    Must show "OK: dir deleted".

    ls infra/postgres/init/001-create-remnashop.sql 2>/dev/null && echo "FAIL: sql exists" || echo "OK: sql deleted"
    Must show "OK: sql deleted".

    grep -c "remnashop" infra/README.md 2>/dev/null
    Must be 0.

    grep -r "remnashop" infra/ --include="*.yml" --include="*.yaml" --include="*.sql" --include="*.md" | wc -l
    Must be 0.

  STEP 2: Compose still valid
    cd infra && docker compose config -q && echo "Valid" || echo "INVALID"
    Must show "Valid".

    cd infra && docker compose --profile bot config -q && echo "Bot valid" || echo "INVALID"
    Must show "Bot valid".

VF-4: Mobile verification (P0, after cleanup-agent + mobile-tests complete)
  STEP 1: TODO count
    grep -c "TODO\|FIXME" cybervpn_mobile/lib/ -r --include="*.dart" --include="*.arb" 2>/dev/null
    Must be 0 (or very close — cert_pins pre-production notes may remain).

  STEP 2: Static analysis
    cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -5
    Must show 0 errors.

  STEP 3: Tests (if flutter test works in this env)
    cd cybervpn_mobile && flutter test --reporter compact 2>&1 | tail -10
    Report pass/fail count.

  STEP 4: Test stub count
    grep -r "TODO\|FIXME\|placeholder\|stub" cybervpn_mobile/test/ --include="*.dart" | wc -l
    Must be reduced by >= 80% from 172 (target: < 35).

DONE CRITERIA: All 4 verification blocks pass. All grep checks return expected values. Report any failures with file:line details.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    +-- FR-1 (33 per-route error files) --- independent
                    |
                    +-- FR-2 (CodesSection.tsx last any) --- independent
                    |
                    +-- FR-3 (root layout metadata) --- independent
                    |
                    +-- BF-1 (FCM persistence stack) --- independent
                    |
PHASE 7 START ------+-- BF-2 (metrics broadening) --- independent
                    |
                    +-- BF-3 (FCM tests) --- after BF-1
                    |
                    +-- BT-1 (55 backend test stubs) --- independent
                    |
                    +-- CL-1 (delete remnashop dir) --- independent
                    |
                    +-- CL-2 (mobile TODOs) --- independent
                    |
                    +-- CL-3 (mobile analyze) --- after CL-2
                    |
                    +-- MT-1 (mobile test stubs) --- independent
                    |
                    +-- VF-1 (frontend verify) --- after FR-1, FR-2
                    |
                    +-- VF-2 (backend verify) --- after BF-1, BF-2, BF-3, BT-1
                    |
                    +-- VF-3 (infra verify) --- after CL-1
                    |
                    +-- VF-4 (mobile verify) --- after CL-2, CL-3, MT-1
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| FR-1 | Create error/loading/not-found for 11 dashboard routes (33 files) | frontend-routes | -- | P0 |
| FR-2 | Fix last `any` in CodesSection.tsx (useState<any>) | frontend-routes | -- | P0 |
| FR-3 | Convert root layout metadata to generateMetadata | frontend-routes | -- | P1 |
| BF-1 | FCM token persistence: entity + repo + model + migration + routes | backend-fcm | -- | P0 |
| BF-2 | Add Prometheus metrics to 10 route modules | backend-fcm | -- | P1 |
| BF-3 | Create FCM integration tests (6 tests) | backend-fcm | BF-1 | P1 |
| BT-1 | Implement all 55 backend test stubs across 6 files | backend-tests | -- | P0 |
| CL-1 | Delete infra/remnashop/ directory | cleanup-agent | -- | P0 |
| CL-2 | Resolve all 37 mobile TODO/FIXME markers | cleanup-agent | -- | P0 |
| CL-3 | Verify mobile flutter analyze after TODO changes | cleanup-agent | CL-2 | P1 |
| MT-1 | Implement all mobile test stubs (24 files, ~172 stubs) | mobile-tests | -- | P0 |
| VF-1 | Frontend: file existence + metadata + any-check + lint + build + test | verify | FR-1, FR-2, FR-3 | P0 |
| VF-2 | Backend: FCM check + stub check + metrics check + tests + lint | verify | BF-*, BT-1 | P0 |
| VF-3 | Infra: remnashop deleted + compose valid | verify | CL-1 | P0 |
| VF-4 | Mobile: TODO count + analyze + tests + stub count | verify | CL-*, MT-1 | P0 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| frontend-routes | 3 | FR-1, FR-2, FR-3 |
| backend-fcm | 3 | BF-1, BF-2, BF-3 |
| backend-tests | 1 | BT-1 |
| cleanup-agent | 3 | CL-1, CL-2, CL-3 |
| mobile-tests | 1 | MT-1 |
| verify | 4 | VF-1, VF-2, VF-3, VF-4 |
| **TOTAL** | **15** | |

---

## Lead Coordination Rules

1. **Spawn all 6 agents immediately.** Initial assignments:
   - `frontend-routes` → FR-1 + FR-2 + FR-3 (independent, work sequentially)
   - `backend-fcm` → BF-1 first, then BF-2 in parallel with BF-3
   - `backend-tests` → BT-1 immediately (independent, heavy — 55 stubs)
   - `cleanup-agent` → CL-1 immediately, then CL-2, then CL-3
   - `mobile-tests` → MT-1 immediately (independent, heavy — 172+ stubs)
   - `verify` → wait for dependencies, then VF-1 + VF-2 + VF-3 + VF-4

2. **Communication protocol:**
   - frontend-routes finishes ALL FR-* → messages verify ("frontend routes done, run VF-1")
   - backend-fcm finishes ALL BF-* → messages verify ("backend FCM done, run VF-2")
   - backend-tests finishes BT-1 → messages verify ("backend test stubs done, run VF-2")
   - cleanup-agent finishes ALL CL-* → messages verify ("cleanup done, run VF-3 + VF-4")
   - mobile-tests finishes MT-1 → messages verify ("mobile tests done, run VF-4")
   - verify reports pass/fail back to lead

3. **Parallel execution strategy:**
   - Wave 1 (immediate): FR-1, FR-2, FR-3, BF-1, BF-2, BT-1, CL-1, CL-2, MT-1
   - Wave 2 (after deps): BF-3 (after BF-1), CL-3 (after CL-2)
   - Wave 3 (verification): VF-1 (after FR-*), VF-2 (after BF-* + BT-1), VF-3 (after CL-1), VF-4 (after CL-* + MT-1)

4. **File conflict prevention:**
   - frontend-routes owns `frontend/src/app/[locale]/(dashboard)/*/error.tsx|loading.tsx|not-found.tsx` + `frontend/src/app/[locale]/layout.tsx`
   - backend-fcm owns `backend/src/` (domain, infrastructure, presentation FCM + metrics)
   - backend-tests owns `backend/tests/` exclusively
   - cleanup-agent owns `infra/remnashop/` + `cybervpn_mobile/lib/` (comments only)
   - mobile-tests owns `cybervpn_mobile/test/` exclusively
   - verify writes NOTHING — only runs commands and reports
   - CRITICAL: backend-fcm and backend-tests MUST NOT edit the same files
     - backend-fcm creates NEW files (entity, repo, model, migration, modifies fcm/routes.py and metric modules)
     - backend-tests edits ONLY files in tests/ directory

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task or help unblock.

8. **Verification failures:** If verify reports a failure:
   - TypeScript error → assign to frontend-routes
   - Backend test failure → assign to backend-tests
   - FCM/metrics issue → assign to backend-fcm
   - Compose error → assign to cleanup-agent
   - Flutter analyze error → assign to cleanup-agent
   - Mobile test failure → assign to mobile-tests

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Python 3.13, Flutter 3.x, etc.)
- Do NOT break existing working endpoints, pages, tests, or features
- Do NOT modify generated/types.ts manually — it's auto-generated from OpenAPI
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT add `any` types in frontend code — Phase 6 already eliminated them all
- Do NOT leave TODO comments in test files — every test must have real assertions
- Do NOT leave `pass` as the only body of a test function — implement real tests
- Do NOT modify working Three.js/3D code — it's finished
- Do NOT remove console.error calls — only console.log and console.warn in production
- Do NOT touch the `bot` or `monitoring` Docker profiles — only delete remnashop dir
- Do NOT modify Alembic migration files that already ran — only create NEW migrations
- Do NOT change backend auth flow or middleware — it's working correctly
- For mobile TODO resolution: Do NOT change functional code — only convert TODO comments to neutral documentation notes

---

## Final Verification (Lead runs after ALL tasks + VF-* complete)

```bash
# ===== Frontend =====
# Per-route files (33 files)
count=0; for dir in analytics dashboard monitoring partner payment-history referral servers settings subscriptions users wallet; do for f in error.tsx loading.tsx not-found.tsx; do test -f "frontend/src/app/[locale]/(dashboard)/$dir/$f" && count=$((count+1)); done; done; echo "Route files: $count/33"
# Must be 33/33

# Root layout metadata
grep -c "generateMetadata" frontend/src/app/[locale]/layout.tsx
# Must be >= 1

# Build
cd frontend && npm run lint && npm run build && npm run test:run
# All must pass

# ===== Backend =====
# FCM persistence
grep -c "placeholder" backend/src/presentation/api/v1/fcm/routes.py
# Must be 0

# No pass stubs
grep -rn "^\s*pass$" backend/tests/ --include="*.py" | grep "def test_" -B1 | wc -l
# Must be 0

# Metrics coverage
grep -rl "track_\|\.inc()\|\.labels(" backend/src/presentation/api/v1/ --include="*.py" | wc -l
# Must be >= 15

# Tests
cd backend && python -m pytest tests/ -x -q --timeout=120 2>&1 | tail -10
# All pass

# Lint
cd backend && ruff check src/ tests/ 2>&1 | tail -5
# 0 errors

# ===== Infrastructure =====
ls infra/remnashop/ 2>/dev/null && echo "FAIL: remnashop dir exists" || echo "OK: dir deleted"
# Must be OK

ls infra/postgres/init/001-create-remnashop.sql 2>/dev/null && echo "FAIL: sql exists" || echo "OK: sql deleted"
# Must be OK

grep -c "remnashop" infra/README.md 2>/dev/null || echo "0"
# Must be 0

grep -r "remnashop" infra/ --include="*.yml" --include="*.yaml" --include="*.sql" --include="*.md" | wc -l
# Must be 0

cd infra && docker compose config -q && echo "Compose valid"
# Must be valid

# ===== Mobile =====
grep -c "TODO\|FIXME" cybervpn_mobile/lib/ -r --include="*.dart" --include="*.arb" 2>/dev/null
# Must be 0 (or close to 0)

cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -3
# 0 errors

grep -r "TODO\|FIXME\|placeholder\|stub" cybervpn_mobile/test/ --include="*.dart" | wc -l
# Must be < 35 (reduced >= 80% from 172)
```

All commands must pass with expected values. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Frontend — Per-Route Error Boundaries
- [ ] analytics/ has error.tsx, loading.tsx, not-found.tsx
- [ ] dashboard/ has error.tsx, loading.tsx, not-found.tsx
- [ ] monitoring/ has error.tsx, loading.tsx, not-found.tsx
- [ ] partner/ has error.tsx, loading.tsx, not-found.tsx
- [ ] payment-history/ has error.tsx, loading.tsx, not-found.tsx
- [ ] referral/ has error.tsx, loading.tsx, not-found.tsx
- [ ] servers/ has error.tsx, loading.tsx, not-found.tsx
- [ ] settings/ has error.tsx, loading.tsx, not-found.tsx
- [ ] subscriptions/ has error.tsx, loading.tsx, not-found.tsx
- [ ] users/ has error.tsx, loading.tsx, not-found.tsx
- [ ] wallet/ has error.tsx, loading.tsx, not-found.tsx

### Frontend — Root Layout
- [ ] layout.tsx uses `generateMetadata` (not static `export const metadata`)

### Backend — FCM Persistence
- [ ] domain/entities/fcm_token.py exists
- [ ] domain/repositories/fcm_token_repository.py exists
- [ ] infrastructure/database/models/fcm_token.py exists
- [ ] infrastructure/repositories/fcm_token_repository_impl.py exists
- [ ] Alembic migration for fcm_tokens table exists
- [ ] fcm/routes.py has zero "placeholder" references
- [ ] FCM integration tests pass

### Backend — Test Stubs
- [ ] test_observability.py: 0 pass stubs (was 24)
- [ ] test_oauth_login.py: 0 pass stubs (was 15)
- [ ] test_magic_link.py: 0 pass stubs (was 7)
- [ ] test_register.py: 0 pass stubs (was 5)
- [ ] test_di_container.py: 0 pass stubs (was 2)
- [ ] test_totp_encryption.py: 0 pass stubs (was 2)
- [ ] All 55 new tests have real assertions

### Backend — Metrics
- [ ] >= 15 route modules have Prometheus metrics (was 5)

### Frontend — Last `any` Type
- [ ] CodesSection.tsx has `PromoDiscount` interface, no `<any>`

### Infrastructure
- [ ] infra/remnashop/ directory deleted
- [ ] infra/postgres/init/001-create-remnashop.sql deleted
- [ ] infra/README.md has zero remnashop references
- [ ] docker compose config -q passes

### Mobile — TODO Resolution
- [ ] api_constants.dart: 0 TODOs (was 12)
- [ ] cert_pins.dart: 0 TODOs (was 3, converted to notes)
- [ ] ARB files: 0 TODO comments (was 8)
- [ ] Remaining feature TODOs: all converted to notes
- [ ] Total TODO/FIXME count: 0

### Mobile — Test Stubs
- [ ] Test TODO/placeholder count reduced by >= 80%
- [ ] Top 6 files fully implemented (diagnostic_service, speed_test, profile_repo, url_parser, notification_local_ds, referral_dashboard)

### Build Verification
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm run test:run` passes
- [ ] `python -m pytest tests/ -x -q` passes
- [ ] `ruff check src/ tests/` passes
- [ ] `flutter analyze --no-fatal-infos` passes
- [ ] `docker compose config -q` passes
