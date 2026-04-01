
> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** исправить критические SEO/GEO/AEO проблемы фронтенда без деградации дизайна, motion-слоя и скорости, а затем подготовить платформу для масштабирования органики, AI citations и конверсии.

**Architecture:** P0 строится вокруг единого server-first metadata/crawl policy слоя и жёсткой index hygiene. P1 переводит marketing/help/docs в SSR-friendly knowledge surface с progressive enhancement для интерактивности и 3D. P2 добавляет контентную архитектуру, trust layer и аналитический growth loop поверх уже исправленного технического фундамента.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.9, next-intl, Tailwind CSS 4, Motion, Three.js / React Three Fiber, Vitest, Testing Library.

---

## Non-Negotiables

1. Не ломать cyberpunk visual language.
2. Не резать 3D и motion "топором"; только переводить в progressive enhancement.
3. Не ухудшать Core Web Vitals и mobile experience.
4. Не открывать в индекс приватные, auth, miniapp, test и utility routes.
5. Не плодить metadata вручную по всем страницам; сначала собрать единый helper layer.

## Release Order

1. P0: crawl/index/canonical/metadata foundation.
2. P1: SSR-first public shell, help/docs, structured data, performance guardrails.
3. P2: content hubs, trust center, growth instrumentation, tiered locale rollout.

## Definition Of Done

- Все intended public pages имеют корректные canonical, hreflang и robots policy.
- `robots.txt` и `sitemap.xml` ссылаются на `https://vpn.ozoxy.ru`.
- `dashboard`, `miniapp`, `auth`, `oauth`, `verify`, `test` и аналогичные utility routes не индексируются.
- Маркетинговые страницы отдают meaningful HTML без top-level bailout для основного знания и CTA.
- Дизайн визуально сохраняется.
- `NEXT_TELEMETRY_DISABLED=1 npm run build`, targeted Vitest suites, `npm run check:mobile` и SEO static audit проходят.

## P0 Gate Commands

Run from: `frontend/`

```bash
npm run test:run -- src/shared/lib/__tests__/seo-route-policy.test.ts
npm run test:run -- src/shared/lib/__tests__/site-metadata.test.ts
npm run test:run -- src/app/__tests__/robots.test.ts
npm run test:run -- src/app/__tests__/sitemap.test.ts
npm run test:run -- src/widgets/__tests__/landing-hero-seo.test.tsx
npm run test:run -- src/widgets/__tests__/footer-seo.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
npm run check:mobile
```

Expected:
- all tests PASS
- build PASS
- no crawl-policy or canonical failures in SEO audit
- no mobile regression failures

## P1 Gate Commands

```bash
npm run test:run -- src/widgets/__tests__/public-terminal-header.test.tsx
npm run test:run -- src/widgets/__tests__/help-faq-server.test.tsx
npm run test:run -- src/widgets/__tests__/docs-content-server.test.tsx
npm run test:run -- src/shared/lib/__tests__/structured-data.test.tsx
npm run test:run -- src/3d/__tests__/performance-baseline.test.ts
npm run test:run -- src/shared/lib/__tests__/web-vitals.test.ts
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
npm run check:mobile
```

Expected:
- no top-level SSR bailout on core marketing/help/docs routes
- performance baselines preserved
- build artifacts contain expected indexable HTML

## P2 Gate Commands

```bash
npm run test:run -- src/app/[locale]/(marketing)/guides/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/compare/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
npm run check:mobile
```

Expected:
- new content hubs generate valid metadata, schema and internal links
- no performance regressions from added content surfaces

### Task 1: Create a single SEO route policy source of truth

**Priority:** P0

**Files:**
- Create: `frontend/src/shared/lib/seo-route-policy.ts`
- Create: `frontend/src/shared/lib/__tests__/seo-route-policy.test.ts`
- Modify: `frontend/src/shared/lib/site-metadata.ts`

**Step 1: Write the failing test**

Add tests for:
- `isIndexableRoute('/en-EN/pricing') === true`
- `isIndexableRoute('/en-EN/dashboard') === false`
- `isIndexableRoute('/en-EN/test-error') === false`
- localized alternate generation for `/pricing`
- `x-default` fallback generation

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/seo-route-policy.test.ts
```

Expected: FAIL because helper does not exist yet.

**Step 3: Write minimal implementation**

In `seo-route-policy.ts`, define:
- `SITE_URL` reuse
- `INDEXABLE_MARKETING_PATHS`
- `NOINDEX_PATH_PREFIXES`
- `NOINDEX_EXACT_PATHS`
- `toAbsoluteLocalizedUrl(locale, path)`
- `buildLocalizedAlternates(path)`
- `isIndexableLocalizedPath(pathname)`

Keep all route decisions centralized here. No duplicated route lists elsewhere.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/seo-route-policy.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/shared/lib/seo-route-policy.ts src/shared/lib/site-metadata.ts src/shared/lib/__tests__/seo-route-policy.test.ts
git commit -m "feat: add centralized seo route policy"
```

### Task 2: Fix `robots.txt` to match real locale routing

**Priority:** P0

**Files:**
- Create: `frontend/src/app/__tests__/robots.test.ts`
- Modify: `frontend/src/app/robots.ts`
- Reference: `frontend/src/shared/lib/seo-route-policy.ts`

**Step 1: Write the failing test**

Cover:
- sitemap points to `https://vpn.ozoxy.ru/sitemap.xml`
- public crawling allowed
- locale-prefixed dashboard and miniapp paths disallowed
- test routes disallowed
- `OAI-SearchBot` not blocked on indexable public content

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/app/__tests__/robots.test.ts
```

Expected: FAIL due to wrong domain and incomplete disallow coverage.

**Step 3: Write minimal implementation**

Update `robots.ts` so it:
- uses `SITE_URL`
- blocks locale-aware private patterns
- blocks test/debug paths
- keeps indexable marketing surface open

Do not invent special bot rules unless they serve a concrete policy need.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/app/__tests__/robots.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/app/robots.ts src/app/__tests__/robots.test.ts
git commit -m "fix: align robots policy with localized routes"
```

### Task 3: Fix `sitemap.xml` so it reflects the real public site

**Priority:** P0

**Files:**
- Create: `frontend/src/app/__tests__/sitemap.test.ts`
- Modify: `frontend/src/app/sitemap.ts`
- Reference: `frontend/src/shared/lib/seo-route-policy.ts`

**Step 1: Write the failing test**

Cover:
- uses `https://vpn.ozoxy.ru`
- includes `/pricing`, `/features`, `/download`, `/help`, `/docs`, `/security`, `/network`, `/status`, `/contact`
- excludes dashboard, miniapp, auth callbacks, test routes
- emits entries for supported indexable locales only

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/app/__tests__/sitemap.test.ts
```

Expected: FAIL

**Step 3: Write minimal implementation**

Replace the hardcoded `publicRoutes` list with route policy helpers. Keep implementation deterministic and auditable.

If the generated list becomes too large, split later into sitemap index files, but do not block P0 on that unless build output becomes unwieldy.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/app/__tests__/sitemap.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/app/sitemap.ts src/app/__tests__/sitemap.test.ts
git commit -m "fix: generate sitemap from public seo route policy"
```

### Task 4: Repair locale metadata, canonical, hreflang, `lang`, and `dir`

**Priority:** P0

**Files:**
- Create: `frontend/src/shared/lib/__tests__/site-metadata.test.ts`
- Modify: `frontend/src/shared/lib/site-metadata.ts`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/[locale]/layout.tsx`
- Reference: `frontend/src/i18n/config.ts`

**Step 1: Write the failing test**

Cover:
- canonical for `/pricing` resolves to `https://vpn.ozoxy.ru/en-EN/pricing`
- alternate languages are page-equivalent, not locale root
- `x-default` exists
- RTL locales map to correct direction

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/site-metadata.test.ts
```

Expected: FAIL because current helpers are too shallow.

**Step 3: Write minimal implementation**

Refactor `site-metadata.ts` into a reusable metadata builder:
- `withSiteMetadata()` should accept canonical path and route type
- build page-level alternates from route policy
- expose helper for `html` language attributes

Update:
- root layout to stop hardcoding `lang="en"`
- locale layout to stop canonicalizing everything to `/${locale}`

Do not scatter per-page canonical logic if a helper can own it.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/site-metadata.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/shared/lib/site-metadata.ts src/shared/lib/__tests__/site-metadata.test.ts src/app/layout.tsx src/app/[locale]/layout.tsx
git commit -m "fix: repair localized canonical and hreflang metadata"
```

### Task 5: Roll page-level metadata across marketing routes and noindex private surfaces

**Priority:** P0

**Files:**
- Modify: `frontend/src/app/[locale]/(marketing)/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/features/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/download/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/help/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/docs/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/security/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/network/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/privacy/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/privacy-policy/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/status/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/contact/page.tsx`
- Modify: `frontend/src/app/[locale]/(auth)/layout.tsx`
- Modify: `frontend/src/app/[locale]/(dashboard)/layout.tsx`
- Modify: `frontend/src/app/[locale]/miniapp/layout.tsx`
- Modify: `frontend/src/app/[locale]/test-animation/page.tsx`
- Modify: `frontend/src/app/[locale]/test-error/page.tsx`

**Step 1: Write the failing test**

Create one test file:
- `frontend/src/app/__tests__/page-metadata-policy.test.ts`

Cover:
- core marketing routes are indexable
- auth, dashboard, miniapp, test routes are `noindex`
- marketing titles/descriptions include actual user intent, not only brand styling

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/app/__tests__/page-metadata-policy.test.ts
```

Expected: FAIL

**Step 3: Write minimal implementation**

Update page-level `generateMetadata` to use new helper with:
- page-specific canonical path
- per-page title and description
- `robots` policy

For:
- `(auth)` layout: `noindex, nofollow`
- `(dashboard)` layout: `noindex, nofollow`
- `miniapp` layout: `noindex, nofollow`
- test pages: either remove from prod surface or set hard `noindex`

Also remove fake `SearchAction` from `app/layout.tsx` unless a real search route is implemented.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/app/__tests__/page-metadata-policy.test.ts
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: PASS and build PASS

**Step 5: Commit**

```bash
git add src/app/layout.tsx src/app/[locale]/layout.tsx src/app/[locale]/(marketing) src/app/[locale]/(auth)/layout.tsx src/app/[locale]/(dashboard)/layout.tsx src/app/[locale]/miniapp/layout.tsx src/app/[locale]/test-animation/page.tsx src/app/[locale]/test-error/page.tsx src/app/__tests__/page-metadata-policy.test.ts
git commit -m "fix: roll out page-level seo metadata policy"
```

### Task 6: Make CTA and entity links crawlable and trustworthy

**Priority:** P0

**Files:**
- Create: `frontend/src/widgets/__tests__/landing-hero-seo.test.tsx`
- Create: `frontend/src/widgets/__tests__/footer-seo.test.tsx`
- Modify: `frontend/src/widgets/landing-hero.tsx`
- Modify: `frontend/src/widgets/footer.tsx`

**Step 1: Write the failing test**

Cover:
- hero CTAs render as real links with meaningful hrefs
- footer social links do not use `#`
- footer internal links remain present
- link text stays descriptive

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/widgets/__tests__/landing-hero-seo.test.tsx
npm run test:run -- src/widgets/__tests__/footer-seo.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Update:
- hero primary CTA to real `Link` to acquisition target
- hero secondary CTA to download route
- footer social links to real brand/entity profiles
- keep existing visuals and button styling exactly or near-exactly intact

Do not convert styling to bland default links.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/widgets/__tests__/landing-hero-seo.test.tsx
npm run test:run -- src/widgets/__tests__/footer-seo.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/widgets/landing-hero.tsx src/widgets/footer.tsx src/widgets/__tests__/landing-hero-seo.test.tsx src/widgets/__tests__/footer-seo.test.tsx
git commit -m "fix: make public ctas and entity links crawlable"
```

### Task 7: Add a build artifact SEO audit script

**Priority:** P0

**Files:**
- Create: `frontend/scripts/seo-static-audit.mjs`
- Modify: `frontend/package.json`

**Step 1: Write the failing script invocation**

Define audit assertions:
- no `vpn-admin.example.com`
- no canonical to locale root on deep pages
- no `BAILOUT_TO_CLIENT_SIDE_RENDERING` on target pages once P1 lands
- no indexable test pages
- no fake search route in JSON-LD

**Step 2: Run script to verify it fails**

Run:
```bash
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
```

Expected: FAIL on current artifacts

**Step 3: Write minimal implementation**

Add `check:seo` script:

```json
"check:seo": "node scripts/seo-static-audit.mjs"
```

Start with P0 assertions only. Add bailout assertions in P1.

**Step 4: Run script to verify it passes**

Run:
```bash
node scripts/seo-static-audit.mjs
```

Expected: PASS on P0 checks

**Step 5: Commit**

```bash
git add scripts/seo-static-audit.mjs package.json
git commit -m "chore: add seo build artifact audit"
```

### Task 8: Split public header/footer shell from authenticated client-heavy shell

**Priority:** P1

**Files:**
- Create: `frontend/src/widgets/public-terminal-header.tsx`
- Create: `frontend/src/widgets/public-terminal-header-controls.tsx`
- Create: `frontend/src/widgets/__tests__/public-terminal-header.test.tsx`
- Modify: `frontend/src/widgets/terminal-header.tsx`
- Modify: `frontend/src/widgets/terminal-header-controls.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/docs/layout.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/help/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/features/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/download/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/contact/page.tsx`
- Modify: `frontend/src/widgets/footer.tsx`

**Step 1: Write the failing test**

Cover:
- public header renders without auth-store dependency
- still keeps theme/language affordances or graceful fallback
- keeps existing visual shell and CTA region

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/widgets/__tests__/public-terminal-header.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Architecture rule:
- dashboard keeps current authenticated shell
- marketing gets a dedicated public shell
- any client-only controls must be small islands, not the whole header body

Keep:
- same silhouette
- same typography
- same accent treatments

Avoid:
- auth-store reads in public shell
- route hooks in public top nav unless isolated

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/widgets/__tests__/public-terminal-header.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: PASS and reduced public bailout surface

**Step 5: Commit**

```bash
git add src/widgets/public-terminal-header.tsx src/widgets/public-terminal-header-controls.tsx src/widgets/terminal-header.tsx src/widgets/terminal-header-controls.tsx src/widgets/footer.tsx src/widgets/__tests__/public-terminal-header.test.tsx src/app/[locale]/(marketing)
git commit -m "refactor: use server-first public marketing shell"
```

### Task 9: Convert Help Center into SSR-first answer surface

**Priority:** P1

**Files:**
- Create: `frontend/src/widgets/help-faq-server.tsx`
- Create: `frontend/src/widgets/help-faq-client.tsx`
- Create: `frontend/src/widgets/help-categories-server.tsx`
- Create: `frontend/src/widgets/__tests__/help-faq-server.test.tsx`
- Modify: `frontend/src/widgets/help-faq.tsx`
- Modify: `frontend/src/widgets/help-categories.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/help/page.tsx`
- Modify: `frontend/messages/en-EN/HelpCenter.json`

**Step 1: Write the failing test**

Cover:
- SSR output contains FAQ questions and answers
- category navigation still works after hydration
- no `useSearchParams` dependency for baseline content availability

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/widgets/__tests__/help-faq-server.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Move the baseline FAQ knowledge into server-rendered sections:
- top summary
- category blocks
- visible Q/A content in HTML

Keep client enhancement only for:
- animated typing
- category highlighting
- URL query sync if still desired

Do not let `useSearchParams` own the primary answer surface.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/widgets/__tests__/help-faq-server.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
```

Expected: PASS and Help page no longer has empty knowledge HTML.

**Step 5: Commit**

```bash
git add src/widgets/help-faq* src/widgets/help-categories* src/app/[locale]/(marketing)/help/page.tsx messages/en-EN/HelpCenter.json src/widgets/__tests__/help-faq-server.test.tsx
git commit -m "refactor: render help center knowledge server-side"
```

### Task 10: Convert Docs into SSR-first knowledge surface

**Priority:** P1

**Files:**
- Create: `frontend/src/widgets/docs-content-server.tsx`
- Create: `frontend/src/widgets/docs-sidebar-client.tsx`
- Create: `frontend/src/widgets/__tests__/docs-content-server.test.tsx`
- Modify: `frontend/src/widgets/docs-container.tsx`
- Modify: `frontend/src/widgets/docs-content.tsx`
- Modify: `frontend/src/widgets/docs-sidebar.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/docs/page.tsx`
- Modify: `frontend/messages/en-EN/Docs.json`

**Step 1: Write the failing test**

Cover:
- SSR output contains docs headings and code-copy-adjacent content
- active section tracking is enhancement only
- docs page remains visually consistent

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/widgets/__tests__/docs-content-server.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Render:
- document sections
- headings
- descriptive body copy
- key setup steps

server-side first.

Keep client-only:
- active section highlighting
- fancy sidebar motion
- scene sync

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/widgets/__tests__/docs-content-server.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
node scripts/seo-static-audit.mjs
```

Expected: PASS and Docs page keeps meaningful HTML.

**Step 5: Commit**

```bash
git add src/widgets/docs-* src/app/[locale]/(marketing)/docs/page.tsx messages/en-EN/Docs.json src/widgets/__tests__/docs-content-server.test.tsx
git commit -m "refactor: render docs knowledge server-side"
```

### Task 11: Contain 3D, smooth scrolling, and motion as progressive enhancement

**Priority:** P1

**Files:**
- Modify: `frontend/src/app/providers/smooth-scroll-provider.tsx`
- Modify: `frontend/src/shared/ui/lazy-mount.tsx`
- Modify: `frontend/src/widgets/3d-background/global-network-wrapper.tsx`
- Modify: `frontend/src/widgets/landing-features-scene.tsx`
- Modify: `frontend/src/widgets/landing-technical-scene.tsx`
- Modify: `frontend/src/widgets/quick-start-scene.tsx`
- Modify: `frontend/src/widgets/speed-tunnel-scene.tsx`
- Modify: `frontend/src/widgets/landing-hero.tsx`
- Modify: `frontend/src/widgets/landing-features.tsx`
- Modify: `frontend/src/widgets/landing-technical.tsx`
- Modify: `frontend/src/widgets/quick-start.tsx`
- Test: `frontend/src/3d/__tests__/performance-baseline.test.ts`
- Test: `frontend/src/shared/lib/__tests__/web-vitals.test.ts`

**Step 1: Write the failing test**

Add/update expectations for:
- no eager heavy scene mounts above the fold on weak contexts
- smooth scroll not required for content visibility
- performance helper usage remains intact

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/3d/__tests__/performance-baseline.test.ts
```

Expected: FAIL once new guard assertions are added.

**Step 3: Write minimal implementation**

Rules:
- text and CTA stay available before scene hydration
- scenes mount after content, not instead of content
- smooth scrolling only after paint and only where it does not affect crawlable markup
- mobile or reduced-motion users get lighter enhancement

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/3d/__tests__/performance-baseline.test.ts
npm run check:mobile
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/app/providers/smooth-scroll-provider.tsx src/shared/ui/lazy-mount.tsx src/widgets/3d-background/global-network-wrapper.tsx src/widgets/landing-hero.tsx src/widgets/landing-features.tsx src/widgets/landing-technical.tsx src/widgets/quick-start.tsx src/widgets/*scene.tsx src/3d/__tests__/performance-baseline.test.ts
git commit -m "perf: gate 3d and motion as progressive enhancement"
```

### Task 12: Expand structured data and OG coverage without fake signals

**Priority:** P1

**Files:**
- Create: `frontend/src/shared/lib/structured-data.tsx`
- Create: `frontend/src/shared/lib/__tests__/structured-data.test.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/help/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/download/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/docs/page.tsx`
- Modify: `frontend/src/app/[locale]/(marketing)/features/page.tsx`
- Modify: `frontend/src/app/opengraph-image.tsx`

**Step 1: Write the failing test**

Cover:
- Organization schema stays valid
- fake `SearchAction` removed unless route exists
- FAQ schema only appears where visible FAQ content exists
- breadcrumb / software application / offer helpers serialize correctly

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/structured-data.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Introduce composable JSON-LD helpers:
- `OrganizationJsonLd`
- `BreadcrumbJsonLd`
- `FaqJsonLd`
- `SoftwareApplicationJsonLd`
- `OfferJsonLd`

Only emit schema that is actually backed by visible content.

Update OG image to be page-extensible later, but do not block on per-page OG generation in this task if that risks schedule.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/structured-data.test.tsx
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/shared/lib/structured-data.tsx src/shared/lib/__tests__/structured-data.test.tsx src/app/layout.tsx src/app/[locale]/(marketing) src/app/opengraph-image.tsx
git commit -m "feat: add structured data helpers for public pages"
```

### Task 13: Add SEO-aware analytics and AI referral attribution

**Priority:** P1

**Files:**
- Create: `frontend/src/lib/analytics/providers/ga4.ts`
- Create: `frontend/src/lib/analytics/__tests__/ga4.test.ts`
- Modify: `frontend/src/lib/analytics/index.ts`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/widgets/landing-hero.tsx`
- Modify: `frontend/src/widgets/footer.tsx`

**Step 1: Write the failing test**

Cover:
- GA4 provider maps event calls correctly
- `utm_source=chatgpt.com` can be captured downstream
- hero CTA and download CTA have explicit analytics hooks

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/lib/analytics/__tests__/ga4.test.ts
```

Expected: FAIL

**Step 3: Write minimal implementation**

Wire a real provider integration boundary while keeping the current abstraction. Add event names for:
- `seo.landing_cta_click`
- `seo.download_cta_click`
- `seo.help_to_trial_click`
- `seo.ai_referral_session`

Do not overfit to one provider API in feature code.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/lib/analytics/__tests__/ga4.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/lib/analytics/index.ts src/lib/analytics/providers/ga4.ts src/lib/analytics/__tests__/ga4.test.ts src/app/layout.tsx src/widgets/landing-hero.tsx src/widgets/footer.tsx
git commit -m "feat: add analytics provider for seo and ai attribution"
```

### Task 14: Add scalable content hub scaffolding for guides, comparison, and device pages

**Priority:** P2

**Files:**
- Create: `frontend/src/app/[locale]/(marketing)/guides/[slug]/page.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/compare/[slug]/page.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/devices/[slug]/page.tsx`
- Create: `frontend/src/content/seo/guides.ts`
- Create: `frontend/src/content/seo/comparisons.ts`
- Create: `frontend/src/content/seo/devices.ts`
- Create: `frontend/src/widgets/seo/article-page.tsx`
- Create: `frontend/src/widgets/seo/comparison-page.tsx`
- Create: `frontend/src/widgets/seo/device-page.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/guides/__tests__/page.test.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/compare/__tests__/page.test.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx`

**Step 1: Write the failing test**

Cover:
- slug content resolves
- canonical path generation works
- schema and internal CTA regions render

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/app/[locale]/(marketing)/guides/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/compare/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx
```

Expected: FAIL

**Step 3: Write minimal implementation**

Seed at least:
- one guide page
- one comparison page
- one device page

Keep them server-rendered and metadata-driven from content files.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/app/[locale]/(marketing)/guides/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/compare/__tests__/page.test.tsx
npm run test:run -- src/app/[locale]/(marketing)/devices/__tests__/page.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/app/[locale]/(marketing)/guides src/app/[locale]/(marketing)/compare src/app/[locale]/(marketing)/devices src/content/seo src/widgets/seo
git commit -m "feat: scaffold scalable seo content hubs"
```

### Task 15: Add trust center and locale rollout controls

**Priority:** P2

**Files:**
- Create: `frontend/src/app/[locale]/(marketing)/trust/page.tsx`
- Create: `frontend/src/app/[locale]/(marketing)/audits/page.tsx`
- Create: `frontend/src/shared/lib/locale-rollout-policy.ts`
- Create: `frontend/src/shared/lib/__tests__/locale-rollout-policy.test.ts`
- Modify: `frontend/src/i18n/config.ts`
- Modify: `frontend/src/shared/lib/seo-route-policy.ts`

**Step 1: Write the failing test**

Cover:
- only tier-1 locales are indexable for growth surfaces
- trust pages are indexable and linked
- unsupported locales can still function without being promoted to sitemap/indexable marketing surfaces

**Step 2: Run test to verify it fails**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/locale-rollout-policy.test.ts
```

Expected: FAIL

**Step 3: Write minimal implementation**

Introduce explicit locale tiers:
- tier 1: fully indexed marketing locales
- tier 2: available but not promoted in SEO surfaces
- tier 3: internal/required/localized fallback only

Do not remove locales blindly; control their indexability and sitemap presence through policy.

**Step 4: Run test to verify it passes**

Run:
```bash
npm run test:run -- src/shared/lib/__tests__/locale-rollout-policy.test.ts
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/app/[locale]/(marketing)/trust/page.tsx src/app/[locale]/(marketing)/audits/page.tsx src/shared/lib/locale-rollout-policy.ts src/shared/lib/__tests__/locale-rollout-policy.test.ts src/i18n/config.ts src/shared/lib/seo-route-policy.ts
git commit -m "feat: add trust center and locale rollout policy"
```

## Suggested Execution Order Inside This Session

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8
9. Task 9
10. Task 10
11. Task 11
12. Task 12
13. Task 13
14. Task 14
15. Task 15

## High-Risk Areas

- `frontend/src/app/[locale]/layout.tsx`
  - current canonical logic is globally wrong; fix carefully and verify metadata merging.

- `frontend/src/app/layout.tsx`
  - root metadata and JSON-LD affect every route; avoid breaking OG/Twitter defaults.

- `frontend/src/widgets/terminal-header.tsx`
  - shared shell touches both marketing and dashboard; split responsibilities instead of patching in place.

- `frontend/src/widgets/help-faq.tsx`
  - current `useSearchParams` approach is likely blocking SSR knowledge output.

- `frontend/src/widgets/docs-container.tsx`
  - current client composition is likely too heavy for acquisition routes.

- `frontend/src/app/providers/smooth-scroll-provider.tsx`
  - do not let smooth scroll become a prerequisite for content rendering.

## Visual Guardrails

- Preserve existing color tokens, font usage and overall composition.
- If a server-first fallback is introduced, it must visually match the hydrated version.
- Public header/footer refactors must remain recognizably CyberVPN, not generic SaaS chrome.
- Any performance downgrade for motion/3D must be conditional by capability, not universal.

## Performance Guardrails

- Keep `src/3d/__tests__/performance-baseline.test.ts` green at all times.
- Re-run `npm run check:mobile` after every P0 and P1 milestone.
- Do not move heavy client code into the first contentful region.
- Prefer SSR text + deferred enhancement over client-only spectacle.

Plan complete and saved to `docs/plans/2026-03-30-frontend-seo-geo-aeo-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
