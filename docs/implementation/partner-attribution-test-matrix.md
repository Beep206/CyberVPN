# Partner Attribution Test Matrix

Task: `PARTNER-ATTRIBUTION-HARDENING`

Status: Partial. This matrix records the tests executed for the implemented slice and the required tests still missing for the full specification.

## Executed Targeted Tests

| Area | Command | Result |
| --- | --- | --- |
| Frontend public capture route | `npm run test:run -w frontend -- 'src/app/p/[publicToken]/route.test.ts'` | Passed, 6 tests |
| Backend attribution capture/security slice | `cd backend && python -m pytest tests/integration/test_partner_attribution_v2.py tests/unit/presentation/test_auth_realm_hosts.py tests/unit/config/test_settings.py::TestS1CorsAndCookieSettings::test_s1_production_cors_origins_are_accepted_and_normalized tests/security/test_stage1_csrf_protection.py::test_stage1_csrf_allows_partner_cookie_auth_unsafe_request_from_approved_origin -q --tb=short --no-cov` | Passed, 10 tests |
| Backend resolver precedence regression | `cd backend && python -m pytest tests/integration/test_order_attribution_resolution.py::test_order_attribution_prefers_reseller_binding_over_passive_click -q --tb=short --no-cov` | Passed, 1 test |
| Frontend i18n generation | `npm run prepare:i18n -w frontend` | Passed |
| Backend touched-file lint/format | Touched-file Ruff check and format check | Passed |
| Frontend touched-file lint | `npm exec -w frontend -- eslint 'src/app/p/[publicToken]/route.ts' 'src/app/p/[publicToken]/route.test.ts' src/lib/api/partner-attribution.ts` | Passed |

## Failing Or Incomplete Required Gates

| Area | Command | Current Result |
| --- | --- | --- |
| Backend full format gate | `cd backend && python -m ruff format --check .` | Failed: repository-wide baseline would reformat 241 unrelated files |
| Backend full mypy gate | `cd backend && python -m mypy src --ignore-missing-imports --no-strict-optional` | Failed: 601 repository-wide type errors in 96 files |
| Frontend full test gate | `npm run test:run -w frontend` | Failed: unrelated existing test fixture/mock failures |
| Frontend full typecheck | `npm exec -w frontend -- tsc --noEmit --pretty false` | Failed: unrelated existing test fixture/type issues |
| Migration runtime gate | PostgreSQL upgrade/downgrade/re-upgrade | Not run |
| OpenAPI/generated clients | Export and regenerate frontend/admin/partner clients twice | Not run |
| Admin/partner builds | Required consumer builds | Not run |
| Worker durability tests | Outbox/worker/DLQ/idempotency tests | Not implemented |
| E2E | Full user-visible referral flow | Not run |

## Missing Business-State Tests

- Redis rate limiting and metric emission.
- Persistent partner-code link CRUD, QR binding, destination tamper resistance, and owner isolation.
- Centralized eligibility policy across all call sites.
- Claim concurrency on real PostgreSQL.
- Quote/order safety net without the React provider.
- Immutable commission snapshot and Decimal rounding.
- Durable payment-to-earning outbox processing, retries, DLQ, duplicate webhook prevention, and legacy cutover.
- Partner finance summary by currency.
- Partner portal runtime loading/empty/error/retry/a11y/localization behavior.
