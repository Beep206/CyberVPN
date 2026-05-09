> CyberVPN Launch Program
> Evidence ID: S1-PROD-006
> Date: 2026-05-04
> Status: completed locally; deployed staging/prod flag and UI/API evidence remains required before beta.

# S1-PROD-006 Add-ons Kill Switch Evidence

## Scope

`S1-PROD-006` closes the Stage 1 requirement:

```text
Add-ons disabled or explicitly enabled.
No untested add-on path in production.
Evidence: feature flag evidence.
```

For S1 Controlled Public Beta, add-ons remain implemented as a future catalog capability, but they are disabled by default and must not appear in public B2C flows unless explicitly enabled with evidence.

## S1 Decision

| Item | S1 behavior |
|---|---|
| Default backend flag | `STAGE1_ADDONS_ENABLED=false` |
| Default frontend display flag | `NEXT_PUBLIC_STAGE1_ADDONS_ENABLED` absent / not `true` |
| Public add-on catalog | Empty while disabled |
| Web pricing page | No add-on pill/cards while disabled |
| Telegram Mini App | No add-on controls while disabled |
| Telegram Bot add-on catalog | Empty while disabled |
| Base checkout with add-ons | Rejected while disabled |
| Add-on-only checkout flow | Rejected while disabled |
| Admin catalog management | Still available behind admin role; not a public S1 sale path |

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/config/settings.py` | Adds `stage1_addons_enabled: bool = False` |
| `backend/src/application/services/stage1_plan_policy.py` | Adds S1 add-on policy, public add-on filter and kill-switch assertion |
| `backend/src/application/use_cases/payments/checkout.py` | Rejects checkout add-on lines unless `STAGE1_ADDONS_ENABLED=true` |
| `backend/src/application/use_cases/subscriptions/purchase_addons.py` | Rejects add-on-only purchase flow unless `STAGE1_ADDONS_ENABLED=true` |
| `backend/src/presentation/api/v1/addons/routes.py` | Public `/addons/catalog` returns only enabled S1-approved add-ons; default is empty |
| `backend/src/presentation/api/v1/miniapp/routes.py` | Mini App offers omit add-ons while disabled |
| `backend/src/presentation/api/v1/telegram/routes.py` | Telegram Bot add-on catalog omits add-ons while disabled |
| `frontend/src/widgets/pricing/catalog.ts` | Frontend fallback/API add-ons display is gated by `NEXT_PUBLIC_STAGE1_ADDONS_ENABLED=true` |
| `frontend/src/widgets/pricing/pricing-dashboard.tsx` | Header add-ons pill and add-on FAQ appear only when add-ons are present |
| `frontend/src/widgets/pricing/feature-matrix.tsx` | Add-on cards section renders only when add-ons are present; Dedicated IP is not shown as an add-on when disabled |
| `frontend/src/widgets/pricing/tier-cards.tsx` | Plan card bullets omit add-on-only Dedicated IP copy when the dedicated IP add-on is disabled |
| `frontend/src/widgets/pricing/faq-accordion.tsx` | Add-on FAQ item is hidden while add-ons are absent |
| `frontend/src/app/[locale]/miniapp/plans/page.tsx` | Mini App add-on controls and add-on quote lines are gated by returned add-ons |
| `frontend/messages/*/Pricing.json` | Public pricing subtitle/helper copy is neutral while add-ons are disabled |

## Tests Added / Changed

| File | Coverage |
|---|---|
| `backend/tests/security/test_stage1_addon_policy.py` | Policy defaults, filtering and kill-switch assertion |
| `backend/tests/security/test_stage1_paid_plan_policy.py` | Base checkout rejects add-ons by default and allows them only when flag is enabled |
| `backend/tests/unit/pricing/test_purchase_addons.py` | Add-on-only purchase rejects while disabled and still works with explicit enable |
| `backend/tests/unit/api/v1/test_addons.py` | Public add-on catalog returns empty by default and approved add-ons when enabled |
| `backend/tests/unit/api/v1/test_telegram_plans.py` | Telegram Bot add-on catalog returns empty by default |
| `backend/tests/unit/presentation/api/v1/miniapp/test_routes.py` | Mini App offers omit add-ons by default |
| `frontend/src/app/[locale]/miniapp/plans/components/__tests__/PlansClient.test.tsx` | Mini App add-on controls are hidden when offers contain no add-ons |

## Validation

| Check | Result |
|---|---|
| Backend Ruff | Passed |
| Backend targeted pytest with `--no-cov` | `38 passed` |
| Backend targeted pytest with project coverage enabled | Functional tests passed, but global coverage gate failed at `47.56%` because this narrow task pack does not cover the whole backend |
| Frontend targeted Vitest | `3 passed` files, `17 passed` tests |
| Frontend targeted ESLint | Passed |
| Local browser DOM check on `http://127.0.0.1:9001/en-EN/pricing?stage1=prod006-dom` | Visible text contains none of `2 add-ons`, `Add-ons inherit`, `Add-ons, Not Tariff Sprawl`, `Dedicated IP as add-on` |
| Local pricing screenshot | `docs/cybervpn_stage1_launch_docs/evidence/s1-prod-006/pricing-en-EN-no-addons.png` |

## Remaining Evidence Before Beta

| Evidence | Status |
|---|---|
| Deployed `/api/v1/addons/catalog?channel=web` returns `[]` while disabled | Open |
| Deployed `/api/v1/miniapp/offers` returns `addons: []` while disabled | Open |
| Deployed Telegram Bot add-on catalog returns `[]` while disabled | Open |
| Deployed pricing screenshot has no add-on public sale block while disabled | Open |
| Deployed checkout/add-on payload rejection proof | Open |
| Owner decision and evidence before setting `STAGE1_ADDONS_ENABLED=true` | Open |

## Security Review Notes

| Check | Result |
|---|---|
| Default posture | Fail-closed: public add-ons disabled unless explicitly enabled |
| Sale path bypass | Base checkout and add-on-only checkout reject add-on payloads while disabled |
| Public discovery | Public web/Mini App/Telegram Bot catalogs omit add-ons while disabled |
| Admin access | Admin add-on management remains role-gated and is not made public |
| Secrets | No provider secrets or credentials added |
| Static dangerous pattern scan | No new `eval`, `Function`, `exec`, `dangerouslySetInnerHTML`, unsafe raw query patterns found in changed runtime files |
| Secrets scan | No obvious API keys/tokens/private keys found in changed files |
| Dependencies | No dependency added or downgraded |
| `npm audit --omit=dev` | Existing moderate `next -> postcss` advisory remains; `npm audit fix --force` proposes breaking downgrade and was not applied |

## Enablement Rule

Add-ons may be enabled only after a separate owner decision and evidence pack proves:

- final add-on business rules and prices;
- provider invoice/receipt behavior for add-on basket lines;
- webhook idempotency for add-on payments;
- Remnawave/device entitlement update behavior;
- support/admin handling for add-on refunds and provisioning failures;
- deployed UI/API screenshots and rollback procedure;
- kill switch rollback back to `STAGE1_ADDONS_ENABLED=false`.

## Conclusion

`S1-PROD-006` is locally complete. S1 public add-ons are default-off across backend catalogs, checkout/use cases, Mini App, Telegram Bot catalog and web pricing display. This prevents an untested add-on purchase/provisioning path from entering Controlled Public Beta.

Next ID to execute: `S1-PROD-007` - promo/gift/referral kill switches.
