> CyberVPN Launch Program
> Evidence ID: S1-PROD-004
> Date: 2026-05-04
> Status: local currency display rule completed locally; deployed payment-provider evidence remains required before beta.

# S1-PROD-004 Local Currency Display Evidence

## Scope

`S1-PROD-004` implements the Stage 1 rule from `02_STAGE1_CHARTER.md` and `03_STAGE1_PRD_USER_FLOWS.md`:

```text
Billing source of truth: USD
Local currency: display layer only
Russian locale estimate: RUB, rounded upward
Checkout payload currency: unchanged USD, except Telegram Stars XTR where already explicitly selected
```

This task does not enable local-currency billing, YooKassa/Digiseller RUB settlement, live FX rates, tax/fiscalization, or provider-specific minimum amount logic.

## Code Added / Changed

| File | Purpose |
|---|---|
| `frontend/src/shared/lib/pricing-display.ts` | Central S1 price presentation rule: billing amount stays USD; optional local estimate is display-only |
| `frontend/src/widgets/pricing/utils.ts` | Re-exports shared price formatting and presentation helpers for marketing pricing |
| `frontend/src/widgets/pricing/tier-cards.tsx` | Shows USD as primary paid-plan price and optional local display estimate |
| `frontend/src/widgets/pricing/feature-matrix.tsx` | Shows add-on price in USD and optional local display estimate |
| `frontend/src/app/[locale]/miniapp/plans/page.tsx` | Shows Mini App plan/quote/add-on prices in USD with optional local estimate while checkout remains USD/XTR |
| `frontend/src/app/[locale]/(dashboard)/subscriptions/lib/plan-presenter.ts` | Keeps dashboard plan price as USD and returns local estimate separately |
| `frontend/src/app/[locale]/(dashboard)/subscriptions/components/PlanCard.tsx` | Displays `Charged in USD` plus optional local estimate |
| `frontend/src/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal.tsx` | Displays checkout and gateway amounts in USD plus optional local display estimate |
| `frontend/messages/*/Pricing.json` | Adds pricing copy for billing currency and display-only estimate |
| `frontend/messages/*/MiniApp.json` | Adds Mini App copy for billing currency and display-only estimate |
| `frontend/src/shared/lib/__tests__/pricing-display.test.ts` | Proves the shared S1 currency presentation rule |
| `frontend/src/app/[locale]/(dashboard)/subscriptions/lib/__tests__/plan-presenter.test.ts` | Proves dashboard presenter keeps USD as billing currency |

## S1 Currency Contract

| Area | S1 behavior |
|---|---|
| Primary billing currency | `USD` |
| Public pricing card primary amount | USD |
| Checkout request currency | USD for normal checkout; XTR only for existing Telegram Stars flow |
| Russian local display | RUB estimate only |
| RUB rounding | Round upward to the next 10 RUB |
| Static display rate | `100 RUB / 1 USD` for S1 local display fallback |
| Rate version | `stage1-static-display-rates-v1` |
| Local display promise | `Approx. ... display only` / `Примерно ..., только для отображения` |
| Production provider settlement | Not changed by this task |

## Test Coverage

| Scenario | Result |
|---|---|
| Shared helper keeps `USD` as billing source of truth for `ru-RU` | Passed |
| Shared helper derives rounded-up RUB estimate when catalog RUB is absent | Passed |
| Shared helper does not invent local estimates for unsupported locales | Passed |
| Dashboard presenter returns USD as billing price and RUB as display estimate only | Passed |
| Plan card still renders USD prices | Passed |
| Purchase modal quote request still sends `currency: USD` | Passed |
| Mini App quote request still sends `currency: USD` | Passed |
| Mini App checkout commit still sends `currency: USD` for generic checkout | Passed |
| Existing Telegram Stars `XTR` branch remains isolated | Covered by existing Mini App checkout tests |

## Targeted Frontend Test Result

Command:

```bash
npm --prefix frontend run test:run -- \
  src/shared/lib/__tests__/pricing-display.test.ts \
  'src/app/[locale]/(dashboard)/subscriptions/lib/__tests__/plan-presenter.test.ts' \
  'src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PlanCard.test.tsx' \
  'src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx' \
  'src/app/[locale]/miniapp/plans/components/__tests__/PlansClient.test.tsx' \
  'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' \
  'src/app/[locale]/miniapp/plans/__tests__/checkout-code-box.test.tsx'
```

Result:

```text
Test Files  7 passed (7)
Tests       47 passed (47)
```

## Lint Result

Command:

```bash
npm --prefix frontend run lint -- \
  src/shared/lib/pricing-display.ts \
  src/widgets/pricing/utils.ts \
  src/widgets/pricing/tier-cards.tsx \
  src/widgets/pricing/feature-matrix.tsx \
  src/app/[locale]/miniapp/plans/page.tsx \
  'src/app/[locale]/(dashboard)/subscriptions/lib/plan-presenter.ts' \
  'src/app/[locale]/(dashboard)/subscriptions/components/PlanCard.tsx' \
  'src/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal.tsx'
```

Result: passed.

## Browser Evidence

Existing local Next dev server was already listening on `127.0.0.1:9001`.

Smoke:

```bash
curl -I -s http://127.0.0.1:9001/en-EN/pricing
```

Result: `HTTP/1.1 200 OK`.

Screenshot artifacts:

| Artifact | Purpose |
|---|---|
| `docs/cybervpn_stage1_launch_docs/evidence/s1-prod-004/pricing-en-EN.png` | English pricing page screenshot |
| `docs/cybervpn_stage1_launch_docs/evidence/s1-prod-004/pricing-ru-RU.png` | Russian pricing page screenshot |
| `docs/cybervpn_stage1_launch_docs/evidence/s1-prod-004/pricing-en-EN-cards.png` | English pricing card screenshot; card opacity forced for headless Motion capture |
| `docs/cybervpn_stage1_launch_docs/evidence/s1-prod-004/pricing-ru-RU-cards.png` | Russian pricing card screenshot; card opacity forced for headless Motion capture |

Headless CDP DOM check for Russian pricing cards:

```json
{"hasRubEstimate":true,"hasChargedUsd":true,"articles":11}
```

Headless CDP DOM check for English pricing cards:

```json
{"hasChargedUsd":true,"hasRubEstimate":false,"articles":11}
```

Note: Chrome CLI screenshots rendered Motion card articles with computed `opacity: 0` in headless mode. The CDP card screenshots inject `article{opacity:1!important;transform:none!important}` only for screenshot capture. DOM evidence confirms the actual card text exists and includes the S1 currency notices.

## What This Closes Locally

| Item | Status |
|---|---|
| Shared S1 local currency display rule | Closed locally |
| Marketing pricing USD source-of-truth display | Closed locally |
| Russian local display estimate with upward rounding | Closed locally |
| Web dashboard plan card display rule | Closed locally |
| Web purchase modal display rule | Closed locally |
| Mini App plan and quote display rule | Closed locally |
| Checkout request currency unchanged | Closed locally |
| Pricing screenshots | Closed locally |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Deployed staging/prod pricing screenshots | Open |
| Provider invoice/quote evidence for enabled payment path | Open |
| Provider minimum amount/currency evidence | Open |
| YooKassa/Digiseller RUB settlement decision and evidence | Open, separate from display-only rule |
| Owner/legal seller production price approval | Open |
| Real payment receipt/invoice copy review | Open |

## Security Review Notes

| Check | Result |
|---|---|
| Billing source of truth | Checkout request currency remains USD for generic checkout |
| Local display | RUB amount is only rendered as approximate display copy |
| External FX calls | None added |
| Secrets | No secrets or provider credentials added |
| Dependencies | No dependency added or downgraded |
| User input | No new user-input parsing path added |
| Targeted secret scan | No API keys, provider credentials or private-key material found in the changed S1-PROD-004 files |
| Targeted dangerous-pattern scan | No `eval`, dynamic `Function`, shell execution, `dangerouslySetInnerHTML`, unsafe raw query or `innerHTML` pattern found in the changed S1-PROD-004 source files |
| Dependency audit | `npm --prefix frontend audit --omit=dev` reports an existing moderate `next -> postcss` advisory; `audit fix --force` proposes a breaking downgrade and was not applied |

## Final Local Validation

| Check | Result |
|---|---|
| Targeted Vitest | `7 passed (7)` files, `47 passed (47)` tests |
| Targeted ESLint | Passed |
| Targeted `git diff --check` | Passed |
| Docker resource use | No Docker containers were started for this task; `docker ps` returned no running containers |
| Local dev server | Existing Next dev server was already listening on `0.0.0.0:9001` and was left unchanged |

## Conclusion

`S1-PROD-004` is locally complete. Pricing surfaces now communicate USD as the billing source of truth and show local RUB only as approximate display information for Russian locale. This is sufficient for local S1 implementation confidence, but paid beta still requires real provider invoice/callback evidence and production price approval.

Next ID to execute: `S1-PROD-006` - add-ons disabled or explicitly enabled for S1.
