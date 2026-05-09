> CyberVPN Stage 1 Evidence
> ID: S1-FE-010
> Date: 2026-05-05
> Scope: local production frontend build, env classification and bundle leakage scan.

# S1-FE-010 Frontend Bundle/Env Scan Evidence

## Result

`S1-FE-010` is completed locally.

The frontend was built as a production Next.js artifact with explicit public env values and private canary secrets. The resulting client/static bundle and server app artifact were scanned. No private canary values, no real local OAuth/2FA secret values and no high-confidence secret patterns were found in the scanned artifacts.

This is local build evidence. It does not replace the required RC/staging/production scan with the final deployed environment variables and hosted artifact/CDN output.

## Source rules used

| Source | Rule applied |
|---|---|
| [Next.js environment variables docs](https://nextjs.org/docs/pages/guides/environment-variables) | Only `NEXT_PUBLIC_*` values are intended for browser bundling; non-public env values must stay server-side. |
| [Sentry Next.js options/build docs](https://docs.sentry.io/platforms/javascript/guides/nextjs/configuration/options/#release) and [build options](https://docs.sentry.io/platforms/javascript/guides/nextjs/configuration/build/#release-options) | Sentry release data is visible to the browser SDK/build output, so release identifiers must be treated as public build metadata, not secrets. |

## Code hardening completed

| File | Change | Reason |
|---|---|---|
| `frontend/src/instrumentation-client.ts` | Removed private `APP_ENV` and `SENTRY_RELEASE` fallbacks from client instrumentation | Client instrumentation should only use `NEXT_PUBLIC_*` and `NODE_ENV` |
| `frontend/src/__tests__/sentry-config.test.ts` | Added regression test proving private `APP_ENV`/`SENTRY_RELEASE` are ignored by client instrumentation | Prevents reintroducing private env reads into the client entrypoint |
| `frontend/next.config.ts` | Set Sentry `release.name` from public release metadata only: `NEXT_PUBLIC_SENTRY_RELEASE`, `GITHUB_SHA`, `VERCEL_GIT_COMMIT_SHA`, or a local fallback | Sentry injects release into the browser bundle; release must be public |
| `frontend/sentry.server.config.ts` and `frontend/sentry.edge.config.ts` | Removed explicit `release` option from `Sentry.init` | Keeps custom release ownership in `next.config.ts` and avoids duplicate/private release injection patterns |
| `frontend/src/widgets/pricing/feature-matrix.tsx` | Fixed a TypeScript build blocker by passing the add-on price object directly to `getPricePresentation` | Required to obtain a clean production build artifact for scanning |

## Build evidence

| Check | Result |
|---|---|
| Build command | `NEXT_DIST_DIR=.next-s1-fe-010 npm run build` with controlled public/private canary env |
| Build result | Passed |
| Static pages generated | `2684` |
| Dynamic/API routes | Built |
| Proxy | Built as Next.js proxy/middleware output |
| Static source maps in client artifact | None found under `frontend/.next-s1-fe-010/static` |

## Env classification

| Env/key family | S1 classification | Bundle expectation |
|---|---|---|
| `NEXT_PUBLIC_APP_ENV` | Public build/runtime label | May appear in client bundle |
| `NEXT_PUBLIC_SENTRY_DSN` | Public Sentry DSN, not a secret; blank in this scan | May appear only if configured |
| `NEXT_PUBLIC_SENTRY_RELEASE` | Public release/build identifier | May appear in client bundle |
| `NEXT_PUBLIC_TELEGRAM_BOT_NAME`, `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` | Public Telegram bot display/integration identifiers | May appear in client bundle |
| `NEXT_PUBLIC_STOREFRONT_KEY` | Public storefront identifier | May appear in client bundle |
| `NEXT_PUBLIC_STAGE1_*_ENABLED` flags | Public UI kill-switch flags | May appear in client bundle; default S1 growth/add-ons flags stay false |
| `NEXT_PUBLIC_GA_MEASUREMENT_ID` | Public analytics ID, only if analytics is approved | Empty in this scan; no GA ID pattern found |
| `API_URL` | Server-side backend URL | Must not be required in browser; browser client uses relative `/api/v1` |
| `OAUTH_TRANSACTION_SECRET`, `PENDING_2FA_SECRET` | Server-only auth transaction secrets | Must not appear in client/static bundle |
| `FRONTEND_OBSERVABILITY_INTERNAL_SECRET` | Server/internal observability contract secret | Must not appear in client/static bundle |
| `SENTRY_DSN` | Server-side Sentry DSN | Must not appear in client/static bundle |
| `SENTRY_RELEASE` | Treat as server/deploy metadata only; not a secret, but not used for client release injection in S1 | Must not drive browser bundle release; use public release metadata instead |
| `SENTRY_AUTH_TOKEN` | Build/upload secret | Value must never appear in bundle, logs or docs |

## Scan results

| Scan | Scope | Result |
|---|---|---|
| Private canary value scan | `frontend/.next-s1-fe-010/static`, `frontend/.next-s1-fe-010/server/app` | Passed: no private canary values found |
| Real local private env value scan | Local ignored `frontend/.env.local` values for OAuth/2FA secrets against build artifacts | Passed: no local private env values found |
| Static high-confidence secret pattern scan | `frontend/.next-s1-fe-010/static` | Passed |
| Private Sentry release canary regression scan | `frontend/.next-s1-fe-010/static` | Passed after `next.config.ts` release hardening |
| Client instrumentation regression test | `src/__tests__/sentry-config.test.ts` | Passed: 9 tests |
| Targeted lint | Sentry config/instrumentation/pricing files | Passed |

## Public bundle observations

| Value class | Observation | Decision |
|---|---|---|
| Public Sentry release | Found in static bundle as expected | Allowed only as public build metadata |
| Public Telegram bot name | Found in static bundle as expected | Allowed |
| Public storefront key | Found in static bundle as expected | Allowed |
| Public API URL | Not found in static bundle in this scan | Good: browser API client resolves to relative `/api/v1` |
| Private Sentry release canary | Not found after hardening | Required |
| Private Sentry DSN canary | Not found | Required |

## `.env.local` handling

| Check | Result |
|---|---|
| `frontend/.env.local` exists locally | Yes |
| Tracked by git | No |
| Ignored by git | Yes, via `frontend/.gitignore` |
| Contains local private OAuth/2FA secrets | Yes, redacted; values were not written to evidence |
| Local private values found in build artifacts | No |

## Remaining requirements before RC/go-live

| Requirement | Reason |
|---|---|
| Repeat S1-FE-010 against the real `stage1-beta-rc.N` build | Local canary build is not final release evidence |
| Scan the deployed hosted frontend artifact/CDN output | Build output can differ from hosted output if deploy platform injects env or rewrites |
| Confirm production env inventory contains no secret-like `NEXT_PUBLIC_*` values | `NEXT_PUBLIC_*` is intentionally browser-visible |
| Keep `SENTRY_AUTH_TOKEN` only in CI/build secret storage | It is a source-map upload credential, not runtime or browser config |
| Use only public identifiers for `NEXT_PUBLIC_SENTRY_RELEASE` | Sentry release is visible to client-side Sentry code |
| Keep non-essential analytics disabled unless consent evidence exists | `NEXT_PUBLIC_GA_MEASUREMENT_ID` was empty in this scan |

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-FE-010` as item `27` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| `NEXT_TELEMETRY_DISABLED=1 NEXT_DIST_DIR=.next-s1-fe-010 ... npm run build` | PASS: production build completed and generated `2801` static pages |
| Private canary scan over `.next-s1-fe-010/static` and `.next-s1-fe-010/server/app` | PASS: no `s1_fe010_private_*_canary_do_not_ship` values found |
| High-confidence secret pattern scan over `.next-s1-fe-010/static` and `.next-s1-fe-010/server/app` | PASS: no matches |
| Static source-map count under `.next-s1-fe-010/static` | PASS: `0` |
| `npm run test:run -- src/__tests__/sentry-config.test.ts` | PASS: `1` file, `9` tests |
| `npm run lint -- next.config.ts sentry.server.config.ts sentry.edge.config.ts src/instrumentation-client.ts src/__tests__/sentry-config.test.ts src/widgets/pricing/feature-matrix.tsx` | PASS |

The build temporarily asked Next.js to add `.next-s1-fe-010` type paths to `frontend/tsconfig.json`; those task-local generated include lines were removed after the scan so the repository is not left with build-artifact-specific config churn.

## Next ID

Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
