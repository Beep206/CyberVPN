# Stage 2 Public Catalog And Pricing Finalization

**Stage:** `S2-STAGE-04`
**Status:** Approved implementation baseline
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 public pricing/catalog contract before wider B2C release work continues.

The goal is to make the customer-facing catalog predictable: public users see only the public B2C plan families, hidden/admin-only plans stay hidden, Russian bundle plans keep their Remnawave template rule, and pricing copy does not show fake local currency estimates.

---

## 2. Source Of Truth

| Area | Source |
|---|---|
| Backend catalog seed | `backend/src/application/services/pricing_catalog_seed.py` |
| Public plan policy | `backend/src/application/services/stage1_plan_policy.py` |
| Public plan API tests | `backend/tests/unit/api/v1/test_plans.py` |
| Quote policy tests | `backend/tests/unit/pricing/test_checkout_quote.py` |
| Frontend public pricing widgets | `frontend/src/widgets/pricing/` |
| Telegram Mini App plans page | `frontend/src/app/[locale]/miniapp/plans/` |
| Dashboard subscription checkout UI | `frontend/src/app/[locale]/(dashboard)/subscriptions/components/` |

The admin may later edit operational prices through approved tooling, but public release behavior must still obey this document unless a later `S2-STAGE-*` explicitly changes it.

---

## 3. Public B2C Plan Families

Only these plan families are public for S2:

| Plan code | Display name | Devices | Traffic policy | Server pool | Support | Dedicated IP |
|---|---:|---:|---|---|---|---|
| `basic` | `Basic` | 2 | fair use / unlimited display | shared | standard | eligible as add-on |
| `plus` | `Plus` | 5 | fair use / unlimited display | shared plus | standard | eligible as add-on |
| `pro` | `Pro` | 10 | fair use / unlimited display | premium shared | priority | eligible as add-on |
| `max` | `Max` | 15 | fair use / unlimited display | premium + exclusive | VIP | 1 included |

Public durations:

```text
30 days
90 days
180 days
365 days
```

Public sale channels:

```text
web
miniapp
telegram_bot
admin
```

The public catalog order is:

```text
Basic -> Plus -> Pro -> Max
```

---

## 4. S2 Public Prices

Billing currency remains USD for S2 public catalog display and quote source of truth.

| Plan | 30 days | 90 days | 180 days | 365 days |
|---|---:|---:|---:|---:|
| Basic | `$5.99` | `$14.99` | `$27.99` | `$49.99` |
| Plus | `$8.99` | `$22.99` | `$39.99` | `$79.00` |
| Pro | `$11.99` | `$29.99` | `$49.99` | `$89.00` |
| Max | `$14.99` | `$36.99` | `$59.99` | `$99.00` |

Public UI must not show copy such as:

```text
Approx ...
display only
Примерно ...
только для отображения
```

Reason: S2 does not have a committed local-currency settlement contract. Showing fake local estimates creates support and payment-dispute risk.

---

## 5. Hidden And Admin-Only Plans

These plans are allowed to exist in the catalog but must not appear in public web, Mini App, Telegram Bot checkout, or public plan API output:

| Plan code | Display name | Visibility | Sale channels | Purpose |
|---|---|---|---|---|
| `start` | `Start` | hidden | admin only | direct/admin entry plan |
| `ru_start` | `Россия Старт` | hidden | admin only | RU bundle controlled distribution |
| `ru_basic` | `Россия Базовый` | hidden | admin only | RU bundle controlled distribution |
| `test` | `Test` | hidden | admin only | experimental/internal validation |
| `development` | `Development` | hidden | admin only | internal development |

Public checkout must reject hidden plans on public sale channels.

---

## 6. Russia Bundle Plans

The owner added Russian hidden plans during S1 stabilization. Their S2 contract is:

| Plan code | Display name | Devices | Traffic | Template |
|---|---:|---:|---|---|
| `ru_start` | `Россия Старт` | 1 | 30 GB total | `Mihomo (RU bundle)` |
| `ru_basic` | `Россия Базовый` | 2 | 30 GB per device, 60 GB total | `Mihomo (RU bundle)` |

Hard rules:

1. RU plans remain hidden/admin-only until a later owner-approved public-market decision.
2. RU plans must use the Remnawave subscription template `Mihomo (RU bundle)`.
3. RU plans must not be shown in the public Basic/Plus/Pro/Max catalog.
4. RU plans must not use dedicated IP add-ons by default.
5. RU plans must remain compatible with `.org` subscription delivery.

---

## 7. Trial Contract

S2 keeps the S1 trial posture unless a later stage changes it:

| Field | Value |
|---|---|
| Trial duration | 3 days |
| Device limit | 1 |
| Traffic limit | 2 GB |
| Public copy | Trial is separate from paid checkout |
| Repeat trial | controlled by backend policy |

Trial copy must not imply automatic paid renewal.

---

## 8. Invite, Referral, Promo, Gift And Add-On Visibility

### Invite redemption

Invite code redemption remains a separate flow from paid checkout. Public UI may show an invite activation section, but it must not be confused with payment discounts.

### Referral, promo and gift

Referral, promo and gift flows are approved for gated S2 implementation, but public enablement still requires their later S2 gates:

| Feature | Public state at S2-STAGE-04 | Required later gate |
|---|---|---|
| Referral | disabled/hidden unless explicitly enabled by later gate | `S2-STAGE-13` |
| Promo checkout discounts | disabled/hidden unless payment/abuse evidence is complete | `S2-STAGE-06`, `S2-STAGE-13` |
| Gift purchase/redeem | disabled/hidden unless payment/support/abuse evidence is complete | `S2-STAGE-06`, `S2-STAGE-09`, `S2-STAGE-13` |
| Autoprolongation | not part of pricing display until lifecycle evidence exists | `S2-STAGE-07` |

### Add-ons

Seeded add-ons:

| Add-on | Price | Public gate |
|---|---:|---|
| `extra_device` | `$6.00` | hidden unless `stage1_addons_enabled=true` and later S2 controls are accepted |
| `dedicated_ip` | `$24.00` | hidden unless `stage1_addons_enabled=true`, location handling is supported and later S2 controls are accepted |

`S2-STAGE-04` validates display and quote behavior, but it does not broadly enable add-ons in production.

---

## 9. UX Copy Rules

Public S2 catalog surfaces must follow these rules:

1. customer-facing plan names use one language per current locale surface;
2. public catalog shows only Basic, Plus, Pro and Max;
3. public catalog does not show hidden/test/development/RU plans;
4. public catalog does not show fake local-currency estimates;
5. checkout copy uses the backend quote as source of truth;
6. quote copy must show billing amount and currency clearly;
7. invite code copy is separate from checkout discount copy;
8. recurring/autoprolongation copy must not appear before the lifecycle gate passes.

---

## 10. Acceptance Evidence

Completed checks for this stage:

| Check | Result |
|---|---|
| Backend pricing seed unit tests | Passed |
| Backend public plan API policy test | Passed |
| Backend checkout quote tests | Passed with add-on policy explicitly enabled in the add-on unit test |
| Mini App plan page tests | Passed |
| Dashboard plan card checkout copy tests | Passed |
| Dashboard purchase modal copy tests | Passed |
| Public pricing widgets copy tests | Passed |

Commands and outputs are recorded in:

```text
docs/evidence/releases/s2-stage-04-public-catalog-20260522.md
```

---

## 11. No-Go Conditions

Do not proceed to public release if any of these become true:

1. hidden/admin-only plans appear in public catalog output;
2. hidden/admin-only plans can be purchased through public checkout;
3. RU plans lose the `Mihomo (RU bundle)` template rule;
4. public pricing shows fake local currency estimates;
5. the Mini App and web catalog disagree on public plan families;
6. trial copy suggests automatic renewal;
7. promo/referral/gift/autoprolongation are publicly enabled before their later S2 evidence gates;
8. quote totals shown to users differ from backend quote totals.

---

## 12. Exit Decision

`S2-STAGE-04` is complete when:

1. this catalog contract is committed;
2. public pricing copy no longer shows fake local estimates;
3. backend policy tests prove public/hidden plan separation;
4. Mini App and web/dashboard surfaces pass targeted catalog tests;
5. add-ons/growth/autoprolongation remain gated unless a later stage enables them;
6. the next stage remains `S2-STAGE-05: Auth And Registration Public Readiness`.
