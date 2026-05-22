# S2-STAGE-04 Evidence: Public Catalog And Pricing Finalization

**Date:** 2026-05-22
**Stage:** `S2-STAGE-04`
**Status:** Passed targeted local evidence

---

## 1. Scope

This evidence covers the S2 public catalog/pricing gate:

1. public plans are Basic, Plus, Pro and Max;
2. hidden/admin-only plans remain hidden from public surfaces;
3. RU bundle plans remain admin-only and retain `Mihomo (RU bundle)`;
4. public pricing copy no longer renders fake local-currency estimates;
5. Mini App, web pricing widgets and dashboard subscription checkout copy align with the pricing contract.

---

## 2. Code Changes Verified

Changed public/customer pricing copy in:

```text
frontend/src/widgets/pricing/tier-cards.tsx
frontend/src/widgets/pricing/feature-matrix.tsx
frontend/src/app/[locale]/(dashboard)/subscriptions/components/PlanCard.tsx
frontend/src/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal.tsx
```

Added or extended tests in:

```text
frontend/src/widgets/pricing/__tests__/public-pricing-copy.test.tsx
frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PlanCard.test.tsx
frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
backend/tests/unit/pricing/test_checkout_quote.py
```

Added contract document:

```text
docs/cybervpn_stage2_launch_docs/03_STAGE2_PUBLIC_CATALOG_PRICING_CONTRACT.md
```

Security maintenance included in this gate:

```text
backend/pyproject.toml
backend/uv.lock
```

Reason: backend `pip-audit` found `starlette 1.0.0` vulnerable as `PYSEC-2026-161`; the fixed version reported by audit was `1.0.1`. The dependency was upgraded forward only.

---

## 3. Frontend Targeted Tests

Command:

```bash
npm --workspace frontend run test -- --run 'src/widgets/pricing/__tests__/public-pricing-copy.test.tsx' 'src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PlanCard.test.tsx' 'src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx' 'src/app/[locale]/miniapp/plans/__tests__/page.test.tsx' 'src/app/[locale]/miniapp/plans/components/__tests__/PlansClient.test.tsx'
```

Result:

```text
Test Files  5 passed (5)
Tests       43 passed (43)
```

Observed behavior:

1. public pricing widgets do not render `approx` / `display only` copy;
2. dashboard plan cards do not render local estimate copy;
3. dashboard purchase modal does not render local estimate copy;
4. Mini App public plan page tests still pass.

---

## 4. Backend Targeted Tests

Command:

```bash
cd backend
uv run pytest tests/unit/pricing/test_pricing_catalog_seed.py tests/unit/api/v1/test_plans.py tests/unit/pricing/test_checkout_quote.py -q --no-cov
```

Result:

```text
tests/unit/pricing/test_pricing_catalog_seed.py ....                     [ 50%]
tests/unit/api/v1/test_plans.py .                                        [ 62%]
tests/unit/pricing/test_checkout_quote.py ...                            [100%]

8 passed in 0.23s
```

Notes:

1. `--no-cov` was used because this was a targeted subset and the repository coverage threshold is intended for broader backend suites.
2. The add-on quote unit test explicitly enables `stage1_addons_enabled` through test monkeypatching. This keeps production add-ons gated while still proving the quote engine behavior when the later S2 gate enables add-ons.

---

## 5. Contract Checks

| Contract | Evidence |
|---|---|
| Public plan families only | Backend seed/policy tests pass; Mini App public plan tests pass |
| Hidden plans rejected on public checkout | Backend checkout quote tests pass |
| RU plans hidden/admin-only | Backend seed contract documents `ru_start` and `ru_basic` as hidden/admin-only |
| RU plans use `Mihomo (RU bundle)` | Backend seed contains `remnawave_subscription_template: "Mihomo (RU bundle)"` |
| Fake local estimates removed | Frontend pricing/dashboard tests pass |
| Add-ons remain gated | `stage1_addons_enabled` remains false by default in settings |

---

## 6. Security Sweep

| Check | Result |
|---|---|
| `git diff --check` | Passed |
| `npm audit --audit-level=high` | Passed high/critical gate; residual moderate findings only |
| Backend `uvx pip-audit --progress-spinner off --skip-editable .` | Passed after Starlette `1.0.0 -> 1.0.1` |
| Targeted secret scan on changed files | No matches |
| Targeted dangerous-pattern scan on changed files | No matches |

Frontend lint:

```text
npm --workspace frontend run lint
```

Result:

```text
0 errors, 6 existing warnings about unused Mini App colorScheme variables.
```

The warnings are outside the pricing/catalog change surface and are not treated as blockers for this stage.

---

## 7. Residual Risks

| Risk | Handling |
|---|---|
| Admin-edited production prices can drift from documented bootstrap prices | Must be reviewed again before `S2-STAGE-16` canary and `S2-STAGE-17` Go/No-Go |
| Localized marketing copy may still need polishing beyond en/ru | Track under optional `S2-OPT-007`; not a blocker if critical flow copy is correct |
| Referral/promo/gift/autoprolongation are approved for S2 but not fully gated here | Later stages must keep them disabled until evidence passes |
| Add-ons are seeded but not broadly enabled | Later gate must prove abuse/support/payment impact before public enablement |

---

## 8. Exit Decision

`S2-STAGE-04` passes local targeted evidence.

Next stage:

```text
S2-STAGE-05: Auth And Registration Public Readiness
```
