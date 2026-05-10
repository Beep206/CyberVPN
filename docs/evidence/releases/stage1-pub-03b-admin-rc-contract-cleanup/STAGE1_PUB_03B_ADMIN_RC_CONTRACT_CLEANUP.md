# STAGE1-PUB-03B: Admin RC Contract Cleanup

Date: 2026-05-10  
Scope: Stage 1 public internet deployment, admin release-candidate contract cleanup  
Result: `PASS_REPEAT_STAGE1_PUB_03`

## Purpose

`STAGE1-PUB-03A` reduced the RC blocker set but left the admin test suite stale against the current Stage 1 contract. This pass aligns admin runtime and tests with the approved S1 assumptions:

- admin canonical domain is `https://admin.cyber-vpn.net`;
- admin public rollout is limited to `ru-RU` and `en-EN`;
- frontend auth uses httpOnly cookie flows, not localStorage bearer tokens;
- payment invoice API path is `/api/v1/payments/crypto/invoice`;
- Next.js metadata handlers must generate real `robots.txt` and `sitemap.xml`;
- Axios 1.16 test behavior must remain interceptable by MSW.

## Runtime Changes

1. `admin/src/lib/api/client.ts`
   - Forced Axios to use the Node `http` adapter under `NODE_ENV=test` so MSW `setupServer` intercepts admin API calls reliably after the Axios 1.16 upgrade.
   - Preserved browser same-origin `/api/v1` behavior outside tests.
   - Added blob response normalization for download/export endpoints when the Node test adapter returns string/JSON instead of a browser `Blob`.

2. `admin/src/app/robots.ts`
   - Replaced the placeholder full-site disallow with an allow-all policy plus explicit disallow paths for auth/private/test/admin-app routes across configured locales.
   - Added canonical sitemap URL using `SITE_URL`.

3. `admin/src/app/sitemap.ts`
   - Replaced the empty placeholder sitemap with generated entries for indexable marketing/content routes.
   - Includes guide, comparison and device detail content for the current `ru-RU` / `en-EN` rollout.

4. `admin/src/test/setup.ts`
   - Extended the `motion/react` test mock with `useMotionValue`, `useSpring` and `useMotionTemplate` to match components used by the current admin UI.

## Test Contract Cleanup

1. Updated old tokenStorage/Bearer-token expectations to the S1 cookie-auth contract.
2. Updated payment tests from `/payments/invoice` to `/payments/crypto/invoice`.
3. Updated SEO/locale tests from the old broad public-marketing rollout to S1 `ru-RU` / `en-EN`.
4. Updated structured-data tests from `vpn.ozoxy.ru` to the admin canonical `SITE_URL`.
5. Updated route error boundary tests to the actual current UI copy and Sentry breadcrumb usage.

## Evidence

- Admin tests: `admin-tests-after-03b.txt`
  - `Test Files 87 passed (87)`
  - `Tests 556 passed (556)`
- Admin lint: `admin-lint-after-03b.txt`
  - `eslint` completed successfully.
- Admin build: `admin-build-after-03b.txt`
  - Next.js production build completed successfully.
  - `/robots.txt` and `/sitemap.xml` are generated routes.

## Remaining Notes

This pass does not create an immutable RC tag by itself. It only clears the admin contract blocker and makes it valid to repeat `STAGE1-PUB-03: Release Candidate Packaging`.

Next action: repeat `STAGE1-PUB-03`.
