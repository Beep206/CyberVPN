# S1-FE-005 Wallet Page Evidence

> Date: 2026-05-06
> Backlog ID: `S1-FE-005`
> Scope: local/no-cost frontend implementation and evidence for the Stage 1 wallet page.
> Result: `LOCAL_PASS`

## Purpose

`S1-FE-005` proves that the authenticated customer wallet page can act as a safe payment-history surface for Controlled Public Beta.

The wallet must help a user understand recent billing activity without exposing raw provider identifiers, checkout URLs, idempotency keys, provider snapshots or provider request payloads.

## Implemented Scope

- `/wallet` now shows a dedicated recent payments section.
- The page calls the existing customer-scoped payment history API through `paymentsApi.getHistory({ limit: 5, offset: 0 })`.
- The frontend does not send `user_uuid`, `customer_uuid` or any operator-selected user identifier.
- Rendered payment fields are limited to provider display label, status, amount, currency, created date and shortened internal payment id.
- Raw provider fields remain out of the wallet UI.
- A CTA links to `/payment-history` for the full payment timeline.
- Wallet withdrawals remain hidden and disabled by default through `NEXT_PUBLIC_STAGE1_WALLET_WITHDRAWALS_ENABLED`.
- Withdrawal fetches and mutation controls are not mounted unless the explicit wallet-withdrawal flag is enabled.
- English and Russian wallet copy were updated and generated bundles were refreshed.

## Files Touched

- `frontend/src/widgets/billing-cabinet/wallet-cabinet-dashboard.tsx`
- `frontend/src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx`
- `frontend/messages/en-EN/wallet.json`
- `frontend/messages/ru-RU/wallet.json`
- `frontend/src/i18n/messages/generated/en-EN.json`
- `frontend/src/i18n/messages/generated/ru-RU.json`

## Relationship to S1-PAY-010

`S1-PAY-010` proves the payment-history API/customer-scope contract and the full payment-history page.

`S1-FE-005` proves the wallet-page consumer surface for that contract. It intentionally reuses the customer-scoped history endpoint and keeps sensitive provider fields out of the wallet page.

## Local Verification

| Check | Command | Result |
|---|---|---|
| Focused frontend tests | `npm --prefix frontend run test:run -- src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx src/lib/api/__tests__/payments.test.ts src/shared/lib/__tests__/surface-policy.test.ts` | `PASS`: 3 files, 39 tests |
| Focused lint | `npm --prefix frontend run lint -- src/widgets/billing-cabinet/wallet-cabinet-dashboard.tsx src/widgets/billing-cabinet/payment-history-dashboard.tsx src/widgets/billing-cabinet/billing-cabinet-model.ts src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx src/lib/api/payments.ts src/shared/lib/stage1-growth-flags.ts src/shared/lib/__tests__/surface-policy.test.ts` | `PASS` |
| Production build | `npm --prefix frontend run build` | `PASS`: Next.js 16.2.4, 2684 static pages generated |
| Production dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | `PASS` for high/critical. Known `postcss` moderate remains through `next`; `npm audit fix --force` is not applied because it proposes a breaking downgrade to `next@9.3.3`. |
| Runtime secret scan | `rg` high-confidence secret patterns over wallet runtime/message/generated files, excluding tests | `PASS`: no runtime matches |
| Dangerous frontend pattern scan | `rg` for `dangerouslySetInnerHTML`, `eval`, `new Function`, `innerHTML`, shell/process patterns in billing widgets | `PASS`: no matches |
| Whitespace check | `git diff --check` | `PASS` |

Note: the initial broad secret scan matched deliberate test sentinel fields named `secret` with values ending in `should-not-render`. These are not credentials; they exist to prove raw provider payloads do not render. Runtime scan excludes test fixtures and passes.

## Safe Rendering Contract

The wallet page must not render:

- provider external payment id;
- idempotency key;
- provider checkout/payment URL;
- provider snapshot payload;
- request snapshot payload;
- full raw provider response;
- operator-selected customer/user identifiers.

The focused tests inject these raw fields into mocked payment records and assert that none are visible in the wallet UI.

## Remaining Go-Live Evidence

This local evidence does not clear go-live by itself. Before S1 go-live, attach:

1. Deployed staging/RC `/wallet` screenshots for no-payment, pending/processing and completed payment states.
2. Real enabled-provider payment samples flowing into the customer-scoped payment-history API.
3. Proof that deployed wallet history uses authenticated customer scope only.
4. Final RC artifact/bundle scan proving no provider credentials or raw payment payloads are exposed client-side.
5. Support/admin procedure proof for paid-but-no-access and orphan payment escalation from the wallet/payment-history context.

## Acceptance Result

`S1-FE-005` is **completed locally** for implementation, i18n, focused tests, lint, production frontend build and local security scans.

This closes the no-cost/local wallet-page implementation step. Deployed staging/RC evidence and real provider/payment records remain open go-live requirements.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-006`...`S1-FE-008` are completed locally through `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
