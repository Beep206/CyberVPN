# S3-STAGE-09 Evidence: Reseller Storefront Contract

**Date:** 2026-05-25
**Stage:** `S3-STAGE-09`
**Status:** Passed for local code/evidence gate
**Stage document:** `docs/cybervpn_stage3_launch_docs/09_STAGE3_RESELLER_STOREFRONT_CONTRACT.md`

---

## 1. Summary

S3-STAGE-09 proves the reseller storefront contract locally:

```text
public storefront preview route exists in OpenAPI
public storefront preview route is hidden when PARTNER_STOREFRONTS_ENABLED=false
preview route returns route, branding, pricing, attribution and analytics contract
partner_code preview resolves reseller owner metadata
preview call does not create attribution touchpoints
ordinary quote after preview remains unowned when no partner_code/code_input is sent
```

This does not enable production reseller storefronts.

---

## 2. Changed Files

```text
backend/src/presentation/api/v1/router.py
backend/src/presentation/api/v1/storefronts/__init__.py
backend/src/presentation/api/v1/storefronts/routes.py
backend/src/presentation/api/v1/storefronts/schemas.py
backend/src/presentation/middleware/partner_disabled_boundary.py
backend/tests/contract/test_s3_storefront_contract_openapi.py
backend/tests/e2e/test_s3_reseller_storefront_contract.py
backend/tests/unit/presentation/middleware/test_partner_disabled_boundary.py
docs/cybervpn_stage3_launch_docs/09_STAGE3_RESELLER_STOREFRONT_CONTRACT.md
docs/evidence/releases/s3-stage-09-reseller-storefront-contract-20260525.md
docs/plans/2026-05-23-cybervpn-s3-stage-roadmap-ru.md
```

---

## 3. Proof Matrix

| Proof | Result |
|---|---|
| Storefront preview route exists | Passed through OpenAPI contract test |
| Storefront preview hidden while disabled | Passed through middleware and e2e |
| Disabled response uses `S3-STAGE-09` | Passed |
| Route contract returns preview/customer paths | Passed |
| Public launch requires `S3-STAGE-15/16/17` | Passed |
| Branding boundary lists allowed/prohibited claims | Passed |
| Pricing boundary uses native storefront pricebook | Passed |
| Partner code resolves reseller attribution contract | Passed |
| Preview records no touchpoint | Passed |
| Ordinary quote remains without partner owner | Passed |

---

## 4. Commands

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
pytest S3 reseller storefront e2e: 1 passed
pytest disabled-boundary middleware: 15 passed
pytest OpenAPI contract: 1 passed
ruff: All checks passed
```

Final hygiene/security review:

```text
git diff --check: passed
S3-09 secret scan: no matches
S3-09 dangerous pattern scan: no matches for eval/exec/os.system/subprocess/raw f-string SQL patterns
docker ps: no running containers reported
npm audit --audit-level=high: passed; 5 moderate advisories remain outside this S3-09 gate
```

---

## 5. Production Notes

Production must keep:

```text
PARTNER_STOREFRONTS_ENABLED=false
```

until S3 rehearsal/canary and owner approval.

The preview API is read-only and must not be treated as public launch approval.

---

## 6. Next

```text
S3-STAGE-10: Partner Reporting And Analytics
```
