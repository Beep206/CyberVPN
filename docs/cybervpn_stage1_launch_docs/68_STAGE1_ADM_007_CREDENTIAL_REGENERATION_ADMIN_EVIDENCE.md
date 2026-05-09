# Stage 1 Credential Regeneration Admin Evidence

> Date: 2026-05-04
> Backlog ID: `S1-ADM-007`
> Scope: admin customer-detail integration, OpenAPI/admin client contract, local backend safety proof
> Status: local evidence complete; deployed admin browser/persona and real staging/prod Remnawave proof remain required before paid beta

## Purpose

`S1-ADM-007` connects the already implemented `S1-VPN-008` credential regeneration backend contract to the real admin customer card.

The operation is intentionally constrained:

- it calls `POST /api/v1/admin/mobile-users/{user_id}/vpn-user/regenerate-credentials`;
- it requires a support reason before submit;
- it can optionally request password-only revocation through `revoke_only_passwords`;
- it relies on backend `Permission.VPN_CREDENTIAL_REGENERATE` for the final role gate;
- it invalidates customer detail, VPN, subscription and timeline queries after success;
- it renders only audit-safe result fields and does not render raw subscription URLs, config links, short UUID secrets or protocol secrets from the regeneration result.

## Implementation Summary

| Area | Change |
|---|---|
| Backend OpenAPI | Regenerated `backend/docs/api/openapi.json` so the credential regeneration route is exported |
| Admin generated types | Regenerated `admin/src/lib/api/generated/types.ts` from backend OpenAPI |
| Admin API client | Added typed `customersApi.regenerateVpnCredentials()` |
| Admin customer card | Added `Regenerate credentials` action, reason-gated dialog and safe result summary in `customer-detail.tsx` |
| Admin i18n | Added EN/RU copy for the action, dialog, result summary and labels |
| Admin API contract test | Added customer API test for endpoint path, snake_case payload and safe response fields |
| Admin UI test | Added customer-detail test for dialog submit and safe-result rendering |
| Frontend reusable widget | Fixed credential-regeneration role helper to accept backend role value `owner/super_admin` |

## Safe UI Contract

| Contract item | S1 behavior |
|---|---|
| Trigger surface | Customer detail VPN access panel |
| Required operator input | Support reason, minimum backend contract is 3 characters |
| Optional operator input | `revoke_only_passwords` checkbox |
| Raw credential material in API response | Not present in typed response |
| Raw credential material in admin result summary | Not rendered |
| Query refresh after success | Customer detail, VPN, subscription and timeline |
| Final authorization | Backend permission dependency, not client-only UI logic |
| Audit action | `customer_vpn_credentials_regenerated` from backend route |

## Local Proof Matrix

| Check | Local result |
|---|---|
| Backend route remains role-gated and audit-logged | Passed through existing S1 credential/audit/RBAC tests |
| Admin OpenAPI/generated client includes the credential regeneration endpoint | Passed by regenerated artifacts and API client lint |
| Admin API method posts the expected snake_case payload | Passed |
| Admin customer card has a reason-gated credential regeneration dialog | Implemented and linted |
| Admin customer card safe summary excludes raw subscription URL/short UUID from the action result | Covered by added UI test source; jsdom runner blocker noted below |
| Frontend reusable role helper includes real backend `owner/super_admin` role value | Passed |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Backend OpenAPI export | `cd backend && uv run python scripts/export_openapi.py` | OpenAPI written to `backend/docs/api/openapi.json` |
| Admin API type generation | `cd admin && npm run generate:api-types` | Generated `admin/src/lib/api/generated/types.ts` |
| Admin i18n generation | `cd admin && npm run prepare:i18n` | Generated 2 locale bundles |
| Admin lint | `cd admin && npm run lint -- src/lib/api/customers.ts src/lib/api/__tests__/customers-admin.test.ts src/features/customers/components/customer-detail.tsx src/features/customers/components/__tests__/customer-detail-credential-regeneration.test.tsx` | Passed |
| Admin endpoint contract test | `cd admin && npx vitest run --environment node src/lib/api/__tests__/customers-admin.test.ts -t "regenerates customer VPN credentials"` | `1 passed`, `14 skipped` |
| Admin default jsdom test runner | `cd admin && npm run test:run -- src/features/customers/components/__tests__/customer-detail-credential-regeneration.test.tsx` | Blocked before test import by existing `cssstyle -> @asamuzakjp/css-color` ESM/TLA issue under jsdom; tracked below |
| Backend tests | `cd backend && uv run pytest tests/security/test_stage1_credential_regeneration.py tests/security/test_stage1_admin_audit_log.py tests/security/test_stage1_admin_rbac_matrix.py -q --no-cov` | `17 passed` |
| Frontend tests | `cd frontend && npm run test:run -- src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration-model.test.ts src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration.test.tsx` | `9 passed` |
| Admin/frontend lint for changed support widget/admin files | See lint rows above | Passed |

## Runner Blocker

Admin jsdom tests do not currently start in this workspace before importing test files:

```text
require() cannot be used on an ESM graph with top-level await
From node_modules/cssstyle/lib/parsers.js
Requiring node_modules/@asamuzakjp/css-color/dist/esm/index.js
```

This is not caused by the S1-ADM-007 code path. It also prevents unrelated admin jsdom tests from starting. The added admin UI test is committed as source and linted, while endpoint contract proof is executed under node environment.

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| Real staging Remnawave credential regeneration smoke | Open |
| Deployed admin browser proof for the customer-detail action | Open |
| Deployed admin persona proof for allowed and denied roles | Open |
| Staging/prod audit-log retrieval for `customer_vpn_credentials_regenerated` | Open |
| Support runbook proof for config delivery after regeneration | Open |
| Admin jsdom runner compatibility fix or browser/Playwright proof | Open |

## Security Notes

- No production Remnawave credentials, subscription URL, config link, provider credential, bot token or user secret was added.
- Docker containers were not started for this task.
- The admin UI result summary is intentionally narrower than the customer subscription snapshot and does not expose regenerated credential material.
- The wider pre-existing admin subscription snapshot can still display subscription/config/link fields; this is now tracked as `TD-S1-ADM-009` for a role/reveal/redaction decision before go-live.
- Client-side UI gating is not treated as security authority; the backend permission dependency remains authoritative.
- The `owner/super_admin` role value mismatch in the reusable frontend support-widget model was corrected to match the backend enum.

## Source Notes

| Source | Use |
|---|---|
| React `useState`: <https://react.dev/reference/react/useState> | Confirmed controlled dialog/result state pattern |
| TanStack Query `useMutation`: <https://tanstack.com/query/latest/docs/react/reference/useMutation> | Confirmed mutation object pattern and `onSuccess` handler usage |

## Next ID

Next ID to execute: `S1-SUP-001` - support ticket path.
