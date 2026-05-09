> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-07
> Backlog ID: `S1-FE-001`
> Статус: PASS for local/no-cost marketing critical-page content review. Deployed staging/RC screenshots remain required before go-live.

# S1-FE-001 Marketing Critical Pages Evidence

## Purpose

`S1-FE-001` proves that the public S1 marketing-critical frontend pages exist and are not carrying placeholders, stale domains or unsupported launch claims.

For `S1 Controlled Public Beta`, public copy must stay bounded to the current approved product posture:

- CyberVPN is a controlled public beta, not a fully mature global VPN network.
- VLESS Reality RAW is the default S1 transport and VLESS Reality XHTTP is the alternate S1 transport.
- Startup regions, node availability, uptime and payment availability must be evidence-gated.
- No public promise of no-logs, no-disks, anonymous payments, universal DPI bypass, auto-renewal, broad P2P/torrent support or fixed uptime/SLA is allowed unless a later evidence gate explicitly proves it.

## Critical Routes Audited

The local audit verifies these route files exist:

```text
src/app/[locale]/(marketing)/page.tsx
src/app/[locale]/(marketing)/pricing/page.tsx
src/app/[locale]/(marketing)/features/page.tsx
src/app/[locale]/(marketing)/devices/page.tsx
src/app/[locale]/(marketing)/devices/[slug]/page.tsx
src/app/[locale]/(marketing)/help/page.tsx
src/app/[locale]/(marketing)/status/page.tsx
src/app/[locale]/(marketing)/terms/page.tsx
src/app/[locale]/(marketing)/privacy/page.tsx
src/app/[locale]/(marketing)/privacy-policy/page.tsx
src/app/[locale]/(marketing)/acceptable-use/page.tsx
src/app/[locale]/(marketing)/refund-policy/page.tsx
src/app/[locale]/(marketing)/cookie-policy/page.tsx
```

## Critical Message Files Audited

The local audit verifies EN/RU critical marketing and legal message files exist:

```text
messages/en-EN/landing.json
messages/ru-RU/landing.json
messages/en-EN/Pricing.json
messages/ru-RU/Pricing.json
messages/en-EN/Features.json
messages/ru-RU/Features.json
messages/en-EN/HelpCenter.json
messages/ru-RU/HelpCenter.json
messages/en-EN/Status.json
messages/ru-RU/Status.json
messages/en-EN/Terms.json
messages/ru-RU/Terms.json
messages/en-EN/Privacy.json
messages/ru-RU/Privacy.json
messages/en-EN/AcceptableUse.json
messages/ru-RU/AcceptableUse.json
messages/en-EN/RefundPolicy.json
messages/ru-RU/RefundPolicy.json
messages/en-EN/CookiePolicy.json
messages/ru-RU/CookiePolicy.json
```

## Changes Made

| Path | Change |
|---|---|
| `frontend/scripts/stage1-marketing-critical-pages-audit.mjs` | Added deterministic S1 marketing critical-page audit for route existence, message existence, canonical domain, placeholder/stale-domain patterns, unsupported public claims and legal metadata usage |
| `frontend/package.json` | Added `check:marketing:s1` |
| `frontend/src/shared/lib/seo-route-policy.ts` | Changed canonical public URL from the old launch domain to `https://cyber-vpn.net` |
| `frontend/scripts/seo-static-audit.mjs` and SEO/static tests | Updated stale canonical domain expectations to `cyber-vpn.net` |
| `frontend/messages/en-EN/landing.json`, `frontend/messages/ru-RU/landing.json` | Reframed landing copy from broad production claims to bounded S1 controlled beta copy |
| `frontend/src/widgets/landing-features.tsx` | Replaced unsupported network-size and uptime stats with S1-safe launch facts |
| `frontend/src/widgets/speed-tunnel.tsx` | Removed public `10 Gbit/s` claim from the landing visual |
| `frontend/src/widgets/landing-technical.tsx` | Replaced fake node names/latencies and outdated protocol label with S1-safe region/protocol presentation |
| `frontend/src/widgets/quick-start.tsx` | Replaced fake `get.cybervpn.com` install command with non-secret QR/subscription/config wording |
| `frontend/messages/en-EN/Features.json`, `frontend/messages/ru-RU/Features.json` | Removed unsupported quantum/multihop/kill-switch/no-logs/P2P-optimized claims and replaced them with S1 transport, support, privacy and policy copy |
| `frontend/messages/en-EN/HelpCenter.json`, `frontend/messages/ru-RU/HelpCenter.json` | Removed unsupported anonymous-payment, Monero, zero-knowledge, kill-switch and military-grade claims |
| `frontend/messages/en-EN/Status.json`, `frontend/messages/ru-RU/Status.json` | Removed `99.99%` availability copy and replaced it with beta availability-window language |
| `frontend/messages/en-EN/Pricing.json`, `frontend/messages/ru-RU/Pricing.json` and pricing widgets | Replaced "unlimited" traffic wording with fair-use policy wording |
| `frontend/src/i18n/messages/generated/*` | Regenerated message bundles through `npm --prefix frontend run prepare:i18n` |

## Local Audit Result

Command:

```bash
npm --prefix frontend run check:marketing:s1
```

Result:

```text
PASS
Critical route files: 13
Critical message files: 20
Canonical site URL: https://cyber-vpn.net
Marketing copy files scanned for unsupported claims: 10
PASS: critical marketing route files exist.
PASS: critical EN/RU marketing and legal message files exist.
PASS: canonical public URL is cyber-vpn.net.
PASS: no placeholder, stale-domain, or unsupported S1 marketing-claim patterns found.
```

## Verification Commands

| Check | Result |
|---|---|
| `npm --prefix frontend run check:marketing:s1` | PASS |
| `npm --prefix frontend run check:i18n:s1` | PASS: 39 enabled locales fallback-complete for S1 critical paths; EN/RU directly reviewed |
| `npm --prefix frontend run test:run -- src/app/__tests__/sitemap.test.ts src/shared/lib/__tests__/locale-rollout-policy.test.ts src/app/[locale]/'(marketing)'/devices/__tests__/page.test.tsx src/app/[locale]/'(marketing)'/guides/__tests__/page.test.tsx src/app/[locale]/'(marketing)'/compare/__tests__/page.test.tsx src/shared/lib/__tests__/seo-route-policy.test.ts src/shared/lib/__tests__/structured-data.test.ts src/app/__tests__/page-metadata-policy.test.ts src/shared/lib/__tests__/stage1-terms-copy.test.ts src/shared/lib/__tests__/stage1-privacy-policy-copy.test.ts src/shared/lib/__tests__/stage1-acceptable-use-copy.test.ts src/shared/lib/__tests__/stage1-refund-policy-copy.test.ts src/shared/lib/__tests__/stage1-cookie-policy-copy.test.ts` | PASS: 13 files, 44 tests |
| `npm --prefix frontend run lint -- scripts/stage1-marketing-critical-pages-audit.mjs scripts/stage1-i18n-critical-path-audit.mjs scripts/seo-static-audit.mjs src/shared/lib/seo-route-policy.ts src/shared/lib/site-metadata.ts src/widgets/landing-features.tsx src/widgets/landing-technical.tsx src/widgets/speed-tunnel.tsx src/widgets/quick-start.tsx src/widgets/pricing/tier-cards.tsx src/widgets/pricing/catalog.ts src/app/[locale]/'(marketing)'/pricing/page.tsx src/app/[locale]/'(marketing)'/features/page.tsx src/app/[locale]/'(marketing)'/help/page.tsx src/app/[locale]/'(marketing)'/status/page.tsx` | PASS |
| `npm --prefix frontend run build` | PASS: Next.js 16.2.4, Cache Components enabled, 2801 static pages generated |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain `icu-minify`, `next-intl` and `postcss` through `next`; `audit fix --force` was not applied because it proposes a breaking/downgrade path |
| High-confidence secret scan over touched S1-FE-001 files | PASS: no matches |
| Static dangerous-pattern scan over touched S1-FE-001 runtime files | PASS: no executable-dangerous matches; audit script intentionally contains blocked placeholder regex patterns |
| `git diff --check` over touched S1-FE-001 files/docs | PASS |
| Stale next-step scan for `S1-FE-001` as the current/next task | PASS: no matches in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | PASS: no running containers reported |

## Important Limitations

This is local/no-cost evidence. It does not prove deployed staging, CDN, redirect, TLS or browser screenshot readiness.

Before go-live, repeat this evidence on the immutable RC tag and attach:

- deployed screenshots for `en-EN` and `ru-RU` pricing, features, devices, help, status and legal pages;
- deployed `.net` primary and `.org` mirror/redirect proof;
- deployed SEO/canonical proof for `https://cyber-vpn.net`;
- final public bundle/env scan for the deployed artifact.

## Documentation References Used

- Next.js App Router project structure and file conventions: https://nextjs.org/docs/app/getting-started/project-structure

## Acceptance Result

`S1-FE-001` is **completed locally** for Stage 1 marketing critical-page readiness.

The project can proceed with payment-provider evidence work, but S1 go-live remains blocked until deployed staging/RC screenshots and final artifact/domain proof are attached.

Next ID to execute after `S1-PAY-011`: `S1-PAY-013` - PayRam readiness if enabled.
