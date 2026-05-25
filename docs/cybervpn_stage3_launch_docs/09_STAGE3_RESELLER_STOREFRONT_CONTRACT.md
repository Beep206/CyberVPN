# Stage 3 Reseller Storefront Contract

**Stage:** `S3-STAGE-09`
**Status:** Passed for local code/evidence gate
**Date:** 2026-05-25
**Product stage:** CyberVPN Partner / Reseller Platform
**Prior gate:** `S3-STAGE-08: Partner Codes, Attribution, And Anti-Abuse`

---

## 1. Назначение

S3-STAGE-09 фиксирует контракт reseller storefront до публичного запуска reseller flow.

Цель этапа: иметь read-only preview API, который показывает route model, branding boundaries, pricing boundaries, attribution contract и analytics contract, но не открывает реальный public reseller storefront и не влияет на обычный customer checkout.

Этот этап не запускает партнёрские storefronts в production.

---

## 2. Decision

Production default остается закрытым:

```text
PARTNER_STOREFRONTS_ENABLED=false
```

Public storefront preview route существует в backend, но при выключенном флаге закрыт disabled-boundary:

```text
GET /api/v1/storefronts/{storefront_key}/preview
```

При выключенном флаге ответ:

```json
{
  "detail": {
    "code": "partner_storefronts_disabled",
    "message": "Partner storefronts are not enabled for this release.",
    "stage": "S3-STAGE-09"
  }
}
```

---

## 3. Входит

| Area | S3-STAGE-09 result |
|---|---|
| Storefront route model | `GET /api/v1/storefronts/{storefront_key}/preview` фиксирует preview route contract. |
| Branding boundaries | Response явно перечисляет allowed customizations и prohibited claims. |
| Pricing boundaries | Response показывает native storefront pricebook prices, без customer-visible base + markup. |
| Owner/reseller attribution | Optional `partner_code` раскрывает explicit reseller/affiliate attribution contract. |
| Storefront disabled state | Middleware blocks `/api/v1/storefronts/*` and `/api/v1/storefront-profiles/*` when flag is off. |
| No public route until approval | Route remains hidden in production by default. |
| Storefront analytics | Response фиксирует expected dimensions и то, что preview не пишет touchpoints. |
| B2C isolation | Preview does not create quote, checkout, touchpoint, or commercial binding. |

---

## 4. Backend Changes

### 4.1 Storefront preview API

Added:

```text
backend/src/presentation/api/v1/storefronts/__init__.py
backend/src/presentation/api/v1/storefronts/routes.py
backend/src/presentation/api/v1/storefronts/schemas.py
```

Registered in:

```text
backend/src/presentation/api/v1/router.py
```

Endpoint:

```http
GET /api/v1/storefronts/{storefront_key}/preview
```

Optional query:

```text
partner_code=<active partner code>
```

### 4.2 Response contract

The response contains:

```text
route_contract
branding_boundary
pricing_boundary
attribution_contract
analytics_contract
```

Route contract:

```text
preview_api_path=/api/v1/storefronts/{storefront_key}/preview
customer_entry_path=/s/{storefront_key}
route_status=preview|inactive
public_launch_requires_stages=S3-STAGE-15,S3-STAGE-16,S3-STAGE-17
checkout_side_effects=false
```

Branding boundary:

```text
allowed_customizations:
- approved_logo
- approved_display_name
- approved_support_contact
- approved_locale_copy

prohibited_claims:
- custom_legal_promises
- no_logs_claim_without_approval
- unapproved_refund_terms
- unapproved_security_guarantees
```

Pricing boundary:

```text
display_policy=show native storefront price only; never show base price plus reseller markup
finance_policy=pricebook entries must be approved by finance policy before public launch
```

Attribution contract:

```text
owner_type=direct_store|affiliate|reseller
owner_source=none|explicit_code
partner_account_id
partner_code_id
touchpoint_policy
```

Analytics contract:

```text
preview_records_touchpoint=false
checkout_records_storefront_origin=<PARTNER_ATTRIBUTION_ENABLED>
checkout_records_explicit_code=<PARTNER_ATTRIBUTION_ENABLED>
expected_dimensions=[storefront_id, storefront_key, partner_account_id, partner_code_id, owner_type, owner_source, sale_channel]
```

---

## 5. Route Guard

Updated:

```text
backend/src/presentation/middleware/partner_disabled_boundary.py
```

Storefront prefixes:

```text
/api/v1/storefronts
/api/v1/storefront-profiles
```

Disabled response stage is now:

```text
S3-STAGE-09
```

This keeps public reseller storefront surfaces hidden until explicit S3 production enablement.

---

## 6. B2C Isolation

The preview endpoint is intentionally side-effect free.

It does not:

1. create quote sessions;
2. create checkout sessions;
3. record attribution touchpoints;
4. create customer commercial bindings;
5. change partner code usage;
6. change ordinary B2C checkout behavior.

E2E proof verifies:

```text
preview call does not increase attribution_touchpoints count
ordinary quote without partner_code still has partner_code_id=null
ordinary quote without code_input still has code_resolution=null
```

---

## 7. Data Model Boundary

Current S3-STAGE-09 implementation does not add a new storefront ownership table or new DB columns.

The contract derives:

1. storefront identity from `storefronts`;
2. branding identity from `brands`;
3. pricing from active `pricebook_versions` and `pricebook_entries`;
4. reseller/affiliate attribution preview from optional active `partner_codes`.

Before broad reseller storefront rollout, a later stage may add a canonical storefront ownership relation if required. For S3-STAGE-09 this is deliberately not needed to prove route, pricing, attribution, and disabled-state behavior.

---

## 8. Exit Criteria Check

| Exit criterion | Result |
|---|---|
| Storefront contract approved | Passed: contract documented and exposed via OpenAPI schema. |
| Route guards work | Passed: middleware hides preview route when `PARTNER_STOREFRONTS_ENABLED=false`. |
| Preview does not affect B2C checkout | Passed: no touchpoint side effect, no partner code on ordinary quote. |
| Pricing boundary clear | Passed: response uses native storefront pricebook entries only. |
| Branding/legal boundary clear | Passed: allowed customizations/prohibited claims returned. |
| Reseller attribution contract clear | Passed: active partner code returns reseller owner metadata. |

---

## 9. Validation

Commands:

```bash
cd backend

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/e2e/test_s3_reseller_storefront_contract.py \
  -q --no-cov

SKIP_TEST_DB_BOOTSTRAP=1 .venv/bin/python -m pytest \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  -q --no-cov

.venv/bin/python -m pytest \
  tests/contract/test_s3_storefront_contract_openapi.py \
  -q --no-cov

.venv/bin/python -m ruff check \
  src/presentation/api/v1/storefronts \
  src/presentation/api/v1/router.py \
  src/presentation/middleware/partner_disabled_boundary.py \
  tests/e2e/test_s3_reseller_storefront_contract.py \
  tests/unit/presentation/middleware/test_partner_disabled_boundary.py \
  tests/contract/test_s3_storefront_contract_openapi.py
```

Observed result:

```text
S3 reseller storefront e2e: 1 passed
Disabled-boundary middleware: 15 passed
OpenAPI contract: 1 passed
Ruff targeted check: passed
git diff --check: passed
S3-09 secret scan: no matches
S3-09 dangerous pattern scan: no matches
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this S3-09 gate
```

---

## 10. Production Posture

Before production storefront enablement:

1. keep `PARTNER_STOREFRONTS_ENABLED=false`;
2. complete `S3-STAGE-15` full rehearsal;
3. complete `S3-STAGE-16` production canary;
4. approve public route/domain/DNS policy;
5. approve storefront legal copy and support ownership;
6. approve finance pricing policy;
7. confirm analytics dashboards and alerts for storefront traffic;
8. confirm rollback disables public storefronts without affecting B2C.

---

## 11. Next Stage

```text
S3-STAGE-10: Partner Reporting And Analytics
```
