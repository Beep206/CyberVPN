# S1-FE-006 Growth UI Gates Evidence

> Date: 2026-05-06
> Backlog ID: `S1-FE-006`
> Scope: local/no-cost frontend implementation and evidence for referral/promo/gift UI gating.
> Result: `LOCAL_PASS`

## Purpose

`S1-FE-006` proves that public referral, promo, gift and checkout-code UI surfaces remain hidden or paused by default during Stage 1 Controlled Public Beta.

The key S1 rule is fail-closed: public growth UI is not exposed just because a single feature flag is accidentally set. It becomes visible only after a later explicit evidence approval gate is enabled.

## Implemented Scope

- Added a master public evidence gate: `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED`.
- Referral UI, promo-code UI, gift-code UI and checkout-code UI now require the master evidence gate plus their specific feature flag.
- Web and Mini App referral/gift hub surfaces use `STAGE1_GROWTH_HUB_UI_ENABLED`.
- `STAGE1_GROWTH_HUB_UI_ENABLED` excludes checkout-code-only approval, so enabling checkout-code UI later cannot accidentally expose referral/gift pages.
- Official web checkout promo entry requires both checkout-code UI approval and promo-code UI approval.
- `/referral` renders a paused S1 state instead of mounting the live referral cabinet by default.
- Mini App `/miniapp/referral` renders a paused S1 state and does not call growth/referral/gift hooks by default.
- Dashboard subscription rewards/checkout-code guidance remains hidden by default.
- Customer dashboard referral action/query remains disabled by default through the existing referral-specific gate.
- Mini App profile referral section remains disabled by default through the existing referral-specific gate.

## Files Touched

- `frontend/src/shared/lib/stage1-growth-flags.ts`
- `frontend/src/shared/lib/surface-policy.ts`
- `frontend/src/shared/lib/__tests__/surface-policy.test.ts`
- `frontend/src/app/[locale]/(dashboard)/referral/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/referral/__tests__/page.test.tsx`
- `frontend/src/app/[locale]/(dashboard)/subscriptions/components/CodesSection.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/__tests__/page.test.tsx`

## Gate Matrix

| Surface | Default S1 state | Required later evidence flags |
|---|---|---|
| Dashboard referral nav/action/query | Hidden / not called | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and `NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED=true` |
| Web `/referral` live cabinet | Paused page | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and at least one of referral/promo/gift hub flags approved |
| Subscriptions rewards hub section | Hidden | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and at least one of referral/promo/gift hub flags approved |
| Web checkout promo-code entry | Hidden / not resolved | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true`, `NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED=true` and `NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED=true` |
| Mini App `/miniapp/referral` live hub | Paused page / no growth hooks | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and at least one of referral/promo/gift hub flags approved |
| Mini App plan checkout-code entry | Hidden / not resolved | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and `NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED=true` |
| Mini App profile referral section | Hidden / no referral queries | `NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED=true` and `NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED=true` |

## Local Verification

| Check | Command | Result |
|---|---|---|
| Focused frontend growth-gate tests | `npm --prefix frontend run test:run -- src/shared/lib/__tests__/surface-policy.test.ts src/widgets/__tests__/dashboard-navigation.test.ts src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/CodesSection.test.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx src/app/'[locale]'/'(dashboard)'/referral/__tests__/page.test.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx src/app/'[locale]'/miniapp/referral/__tests__/page.test.tsx src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx src/app/'[locale]'/miniapp/plans/__tests__/checkout-code-box.test.tsx` | `PASS`: 10 files, 40 tests |
| Focused lint | `npm --prefix frontend run lint -- src/shared/lib/stage1-growth-flags.ts src/shared/lib/surface-policy.ts src/shared/lib/__tests__/surface-policy.test.ts src/widgets/dashboard-navigation.ts src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx src/app/'[locale]'/'(dashboard)'/referral/page.tsx src/app/'[locale]'/'(dashboard)'/referral/__tests__/page.test.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/CodesSection.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/CodesSection.test.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/PurchaseConfirmModal.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx src/app/'[locale]'/miniapp/profile/page.tsx src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx src/app/'[locale]'/miniapp/referral/page.tsx src/app/'[locale]'/miniapp/referral/__tests__/page.test.tsx src/app/'[locale]'/miniapp/plans/page.tsx src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx src/app/'[locale]'/miniapp/plans/__tests__/checkout-code-box.test.tsx` | `PASS` |
| Production build | `npm --prefix frontend run build` | `PASS`: Next.js 16.2.4, Cache Components enabled, 2684 static pages generated |
| Production dependency audit | `npm --prefix frontend audit --omit=dev --audit-level=high` | `PASS` for high/critical. Known `postcss` moderate remains through `next`; `npm audit fix --force` is not applied because it proposes a breaking downgrade to `next@9.3.3`. |
| Secret scan | `rg` high-confidence secret patterns over touched frontend files | `PASS`: no matches |
| Static dangerous-pattern scan | `rg` for `dangerouslySetInnerHTML`, `eval`, `new Function`, `innerHTML`, shell/process and obvious SQL template patterns over touched runtime files | `PASS`: no matches |

## Library Documentation Checked

- Official Next.js docs for Client Components and Cache Components were checked because the affected routes include client-side and Cache Components-enabled Next.js surfaces.
- Official Vitest `vi` docs were checked for environment/test helper usage.

## Remaining Go-Live Evidence

This local evidence does not clear go-live by itself. Before S1 go-live, attach:

1. Deployed staging/RC screenshots proving `/referral`, `/subscriptions`, `/miniapp/referral`, `/miniapp/profile` and `/miniapp/plans` keep public growth UI hidden/paused by default.
2. Final deployed env inventory proving all `NEXT_PUBLIC_STAGE1_*GROWTH*`, referral, promo, gift and checkout-code flags remain off unless explicitly approved.
3. Final RC artifact/bundle scan proving no accidental client-side growth enablement.
4. Owner-approved later evidence pack before enabling any public referral, promo, gift or checkout-code flow.

## Acceptance Result

`S1-FE-006` is **completed locally** for implementation, focused tests, lint, production frontend build and local security scans.

This closes the no-cost/local frontend growth UI gating step. Deployed staging/RC screenshots and final public env/artifact evidence remain open go-live requirements.

Next ID to execute: `S1-FE-009` - i18n critical-path validation. `S1-FE-007` and `S1-FE-008` are completed locally through `105_STAGE1_FE_008_PLATFORM_GUIDES_EVIDENCE.md`.
