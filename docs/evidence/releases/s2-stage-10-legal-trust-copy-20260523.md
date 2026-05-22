# S2 Stage 10 Evidence: Legal, Public Copy, And Trust Pages

**Stage:** `S2-STAGE-10`
**Date:** 2026-05-23
**Status:** Passed local source review
**Scope:** CyberVPN Public Release 1.0 legal/trust copy

---

## 1. Purpose

This evidence records the S2 legal/trust copy cleanup.

Goal: remove S1 candidate placeholders from public legal/trust surfaces and keep CyberVPN public promises aligned with the deployed architecture and evidence gates.

---

## 2. Files Changed

| File / group | Purpose |
|---|---|
| `frontend/messages/*/Terms.json` | S2 Terms of Service wording |
| `frontend/messages/*/privacy-policy.json` | S2 Privacy Policy wording and bounded no-logs claim |
| `frontend/messages/*/AcceptableUse.json` | S2 AUP wording and abuse/support contacts |
| `frontend/messages/*/RefundPolicy.json` | S2 Refund Policy wording and provider-specific limits |
| `frontend/messages/*/CookiePolicy.json` | S2 Cookie Policy wording and `.org` node/subscription-only boundary |
| `frontend/messages/*/Privacy.json` | Public privacy summary wording |
| `frontend/messages/*/landing.json` | Removed S1/beta public marketing wording |
| `frontend/messages/*/footer.json` | Removed S1/beta public footer wording |
| `frontend/messages/*/Status.json` | Public release status wording |
| `frontend/messages/*/HelpCenter.json` | Public release help/support wording |
| `frontend/messages/*/Features.json` | Public release capabilities wording |
| `frontend/messages/*/dashboard.json` | Removed stale S1/go-live dashboard strings |
| `frontend/src/content/seo/trust.ts` | Trust/audit page claim boundaries updated |
| `frontend/src/app/[locale]/(dashboard)/partner/page.tsx` | Removed stale Stage 1 metadata wording |
| `docs/cybervpn_stage2_launch_docs/09_STAGE2_LEGAL_TRUST_COPY.md` | S2 legal/trust contract |
| `docs/plans/2026-05-22-cybervpn-stage2-public-release-master-plan.md` | Marks S2-STAGE-10 completion |

---

## 3. Placeholder Scan

Command:

```bash
rg -n "S1 candidate|Controlled Public Beta|Stage 1|before go-live|final legal review" frontend/messages frontend/src/content frontend/src/app -g '!**/node_modules/**'
```

Observed result after cleanup:

```text
no matches
```

Interpretation:

1. public legal/trust copy no longer presents itself as S1 candidate copy;
2. public copy no longer says final legal review is still required before go-live;
3. stale Stage 1 dashboard and metadata strings were removed from frontend source/messages.

---

## 4. Domain Claim Review

S2 public domain boundary:

| Surface | Public wording |
|---|---|
| `cyber-vpn.net` | Primary public customer domain |
| `admin.cyber-vpn.net` | Primary admin domain |
| `cyber-vpn.org` | VPN node and subscription delivery routes only where presented |
| Node hostnames under `.org` | VPN node hostnames |

Hard rule preserved:

```text
.org is not a general customer-site mirror of .net.
```

---

## 5. Privacy / No-Logs Claim Review

Allowed claim now used:

```text
CyberVPN app/backend is not designed to store browsing content, visited website content, DNS query content or raw VPN traffic content.
```

Required limitation now used:

```text
This is not an independent audited no-logs certification.
```

The Privacy Policy and trust pages disclose that operational records may exist for security, payments, support, provisioning, node operations, observability, abuse handling, backups and audit logs.

---

## 6. Support Contact Review

Public contacts present in legal copy:

```text
support@cyber-vpn.net
privacy@cyber-vpn.net
abuse@cyber-vpn.net
refund@cyber-vpn.net
```

Support copy also tells users not to send passwords, 2FA codes, full card data, raw QR codes, raw subscription URLs or raw VPN config files.

---

## 7. Localization Review

All existing locale directories were updated for the public legal/trust files.

Observed locale count:

```text
39
```

Policy:

1. `ru-RU` contains Russian launch-critical wording where required.
2. Non-Russian locales use English S2 fallback copy until professional localization is approved.
3. No locale may retain S1 candidate or pre-go-live legal placeholders on public legal/trust pages.

---

## 8. Residual Risk

This repository update is not external legal advice and does not replace owner/legal review outside the codebase.

Known non-blocking S2 risk:

1. professional legal localization for all non-Russian locales is not complete;
2. external independent no-logs/security audit is not claimed and has not been published;
3. if the seller structure changes, Terms/Privacy/checkout copy must be updated before collecting payments under the new structure.

---

## 9. Local Verification Commands

Executed local verification:

```bash
npm run test:run -- src/shared/lib/__tests__/stage1-terms-copy.test.ts src/shared/lib/__tests__/stage1-privacy-policy-copy.test.ts src/shared/lib/__tests__/stage1-acceptable-use-copy.test.ts src/shared/lib/__tests__/stage1-refund-policy-copy.test.ts src/shared/lib/__tests__/stage1-cookie-policy-copy.test.ts
npm run lint
npm run build
npm audit --audit-level=high
```

Observed:

```text
targeted legal-copy tests: 5 passed, 18 tests passed
frontend lint: passed, 0 errors, 6 existing Mini App unused-variable warnings
frontend build: passed, 2801 static pages generated
npm audit --audit-level=high: passed for high/critical threshold; 5 moderate advisories remain
```

Security-focused source checks:

```bash
rg -n "S1 candidate|Controlled Public Beta|Stage 1|before go-live|final legal review" frontend/messages frontend/src/content frontend/src/app -g '!**/node_modules/**'
rg -n "password|token|secret|api[_-]?key|private[_-]?key" docs/evidence/releases/s2-stage-10-legal-trust-copy-20260523.md docs/cybervpn_stage2_launch_docs/09_STAGE2_LEGAL_TRUST_COPY.md frontend/src/content/seo/trust.ts
```

Observed:

```text
stale S1/pre-go-live placeholder scan: no matches
secret pattern scan: no private key, provider token, GitHub/GitLab token or Telegram bot token patterns found
```
