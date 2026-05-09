# 52. Stage 1 Evidence - S1-PROD-007 Promo/Gift/Referral Kill Switches

Date: 2026-05-04

Backlog ID: `S1-PROD-007`

Decision source: `DEC-S1-018`

Status: completed locally; deployed staging/production evidence is still required before S1 go-live.

## Objective

Ensure S1 controlled public beta starts with public promo, gift, referral, and checkout-code discount flows disabled by default.

S1 allows manual audited support grants, but does not allow:

- public referral sharing/rewards;
- public promo-code validation;
- public gift purchase or gift redemption;
- checkout discounts from promo/referral/gift/partner codes;
- visible public UI entry points for those flows.

## Implemented Contract

Backend defaults are fail-closed:

- `REFERRAL_ENABLED=false`
- `PROMO_CODES_ENABLED=false`
- `GIFT_CODES_ENABLED=false`
- `CHECKOUT_CODE_DISCOUNTS_ENABLED=false`

Backend guards now reject disabled public flows before business logic runs:

- `/referral/status` returns disabled values without reading referral DB config when the global flag is off.
- `/referral/code`, `/referral/stats`, `/referral/recent`, `/referral/rewards` return `403`.
- `/promo/validate` returns `403`.
- `/codes/resolve` returns `403` for checkout code resolution.
- `/gifts/purchase/quote`, `/gifts/purchase/commit`, `/gifts/my`, `/gifts/redeem` return `403`.
- checkout quote calculation rejects `code_input` / `promo_code` unless the S1 checkout-code flag is explicitly enabled.
- Mini App bootstrap does not generate or expose a referral code while referrals are disabled.

Frontend public surfaces are hidden by default:

- dashboard referral navigation item is hidden;
- dashboard rewards/referral action cards are hidden;
- subscriptions rewards/checkout-code guidance is hidden;
- web checkout code controls are hidden;
- Mini App plan checkout code controls are hidden;
- Mini App profile referral section is hidden and does not call referral APIs;
- Mini App referral/rewards page renders a paused state and does not call growth hooks.

## Local Evidence

Backend component/API evidence:

```bash
cd backend
uv run pytest --no-cov tests/security/test_stage1_growth_policy.py
```

Result:

```text
7 passed in 0.04s
```

Backend lint evidence:

```bash
cd backend
uv run ruff check src/application/services/stage1_growth_policy.py src/application/services/config_service.py src/application/use_cases/payments/checkout.py src/application/use_cases/subscriptions/purchase_addons.py src/presentation/api/v1/codes/routes.py src/presentation/api/v1/gifts/routes.py src/presentation/api/v1/miniapp/routes.py src/presentation/api/v1/payments/routes.py src/presentation/api/v1/promo_codes/routes.py src/presentation/api/v1/referral/routes.py tests/security/test_stage1_growth_policy.py
```

Result:

```text
All checks passed!
```

Frontend feature evidence:

```bash
cd frontend
npm run test:run -- src/shared/lib/__tests__/surface-policy.test.ts src/widgets/__tests__/dashboard-navigation.test.ts src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/CodesSection.test.tsx src/app/'[locale]'/miniapp/plans/__tests__/page.test.tsx src/app/'[locale]'/miniapp/plans/components/__tests__/PlansClient.test.tsx src/app/'[locale]'/miniapp/plans/__tests__/checkout-code-box.test.tsx src/app/'[locale]'/miniapp/profile/__tests__/page.test.tsx src/app/'[locale]'/miniapp/referral/__tests__/page.test.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
```

Result:

```text
Test Files  10 passed (10)
Tests  39 passed (39)
```

Frontend lint evidence:

```bash
cd frontend
npm run lint -- src/shared/lib/stage1-growth-flags.ts src/shared/lib/surface-policy.ts src/widgets/dashboard-navigation.ts src/widgets/customer-cabinet/customer-cabinet-dashboard.tsx src/app/'[locale]'/'(dashboard)'/referral/page.tsx src/app/'[locale]'/'(dashboard)'/subscriptions/components/CodesSection.tsx src/app/'[locale]'/miniapp/plans/page.tsx src/app/'[locale]'/miniapp/profile/page.tsx src/app/'[locale]'/miniapp/referral/page.tsx
```

Result:

```text
eslint completed with exit code 0
```

## Remaining Evidence Before Go-Live

This local evidence does not replace deployed staging/production evidence. Before S1 go-live, capture redacted proof that:

- production/staging env vars are explicitly set to disabled defaults;
- deployed public APIs return expected disabled responses;
- deployed web and Mini App builds do not show promo/gift/referral public UI;
- support/admin manual grant path remains audited and does not require public gift/referral/promo flows;
- any later enablement has kill switch, limits, anti-abuse, idempotency, payment/refund tests, support workflow, and legal copy evidence.

## Security Review Notes

| Check | Result |
|---|---|
| Default posture | Fail-closed: all public promo/gift/referral/checkout-code flows disabled unless explicitly enabled |
| Public API bypass | Public API routes reject disabled flows before use cases/repositories run |
| Checkout bypass | Base checkout and add-on quote paths reject `code_input` / `promo_code` while disabled |
| Public discovery | Dashboard and Mini App public entry points are hidden by default |
| Admin/support grants | Public flows are disabled; manual support/admin grants remain separate and must stay audited |
| Secrets | No provider secrets or credentials added; secret scan findings were existing password variable names in Mini App profile form, not hardcoded secrets |
| Static dangerous pattern scan | No new `eval`, `Function`, `exec`, `dangerouslySetInnerHTML`, unsafe raw query patterns found in changed runtime files |
| Dependencies | No dependency added or downgraded |
| `npm audit --omit=dev` | Existing moderate `next -> postcss` advisory remains; `npm audit fix --force` proposes breaking downgrade and was not applied |

## Next ID

Next ID to execute: `S1-TG-001` - create/define staging Telegram Bot command, menu, onboarding and support surface.
