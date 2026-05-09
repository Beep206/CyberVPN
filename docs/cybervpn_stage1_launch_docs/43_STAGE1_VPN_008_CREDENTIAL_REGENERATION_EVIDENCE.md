# 43. Stage 1 VPN Credential Regeneration Evidence

Task: `S1-VPN-008`  
Status: locally implemented and tested  
Scope: admin/support credential regeneration for Remnawave-backed B2C users.

## Source Contract

Remnawave's current public API specification exposes:

```text
POST /api/users/{uuid}/actions/revoke
```

The request body supports `revokeOnlyPasswords`. When this flag is false, Remnawave can regenerate the subscription short UUID and subscription URL. For S1, CyberVPN uses this endpoint for credential regeneration instead of deleting/recreating the upstream user.

References:

- `https://docs.rw/api/`
- `https://cdn.docs.rw/docs/openapi.json`

## Implemented Backend Contract

| Area | Implementation |
|---|---|
| Permission | `Permission.VPN_CREDENTIAL_REGENERATE` |
| Allowed roles | `owner/super_admin`, `super_admin`, `admin`, `support` |
| Denied roles | `operator`, `viewer` |
| Admin endpoint | `POST /admin/mobile-users/{user_id}/vpn-user/regenerate-credentials` |
| Remnawave operation | `POST /api/users/{uuid}/actions/revoke` |
| Default mode | full credential/subscription regeneration, `revokeOnlyPasswords=false` |
| Optional mode | password-only rotation, `revokeOnlyPasswords=true` |
| Audit action | `customer_vpn_credentials_regenerated` |
| Response policy | no raw subscription URL, short UUID, config link, token, password or provider secret |
| Log policy | only `to_safe_dict()` metadata is logged |

## Implemented Frontend Support Contract

The repository does not yet contain a full production admin customer-detail page. For `S1-VPN-008`, a reusable support/admin widget was added so the future admin page can embed the operation without weakening the backend safety contract.

| Area | Implementation |
|---|---|
| Widget | `CustomerVpnCredentialRegeneration` |
| Allowed UI roles | `owner`, `owner_super_admin`, `super_admin`, `admin`, `support` |
| Denied UI roles | `operator`, `viewer` |
| Request payload | `reason`, `revoke_only_passwords` |
| Endpoint helper | `/admin/mobile-users/{user_id}/vpn-user/regenerate-credentials` |
| UI response policy | renders audit action and safe metadata only |
| Secret policy | no raw `subscription_url`, no raw `short_uuid`, no provider error body |

## Files Changed

| File | Purpose |
|---|---|
| `backend/src/application/use_cases/auth/permissions.py` | Adds dedicated credential regeneration permission and role mapping |
| `backend/src/application/use_cases/subscriptions/stage1_credential_regeneration.py` | Provider-neutral S1 regeneration contract and safe serialization |
| `backend/src/infrastructure/remnawave/user_gateway.py` | Adds Remnawave revoke-subscription API call |
| `backend/src/infrastructure/remnawave/stage1_credential_regeneration_gateway.py` | Maps CyberVPN S1 contract to Remnawave revoke action |
| `backend/src/presentation/api/v1/admin/customer_support.py` | Adds admin/support regeneration route with required audit event |
| `backend/src/presentation/api/v1/admin/customer_support_schemas.py` | Adds request/response schemas |
| `backend/tests/security/test_stage1_credential_regeneration.py` | Local security and contract evidence |
| `frontend/src/widgets/admin-support/customer-vpn-credential-regeneration-model.ts` | Frontend request builder, role gate and safe summary contract |
| `frontend/src/widgets/admin-support/customer-vpn-credential-regeneration.tsx` | Reusable support/admin UI widget for credential regeneration |
| `frontend/src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration-model.test.ts` | Frontend role/payload/secret-safety tests |
| `frontend/src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration.test.tsx` | Frontend user interaction and safe rendering tests |

## Safety Rules

1. Credential regeneration is not tied to generic `USER_UPDATE`.
2. `operator` cannot rotate VPN credentials in S1.
3. A reason is required and stored only as `reason_length`.
4. The audit event is required for the admin route.
5. Audit details do not store raw subscription URLs or config links.
6. API response does not return raw subscription URL or short UUID.
7. Remnawave user is not deleted/recreated for this operation.
8. The frontend widget never renders raw provider error bodies.
9. The frontend widget keeps the action disabled for roles denied by the backend contract.

## Test Evidence

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_credential_regeneration.py -q --no-cov
```

Result:

```text
collected 4 items
backend/tests/security/test_stage1_credential_regeneration.py .... [100%]
4 passed in 0.04s
```

S1 security pack:

```text
backend/tests/security/test_stage1_*.py
200 passed in 12.95s
```

Frontend UI/model evidence:

Command:

```bash
npm --prefix frontend run test:run -- \
  src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration-model.test.ts \
  src/widgets/admin-support/__tests__/customer-vpn-credential-regeneration.test.tsx
```

Result:

```text
Test Files  2 passed (2)
Tests       9 passed (9)
```

Additional frontend checks:

```text
npm --prefix frontend run lint -- src/widgets/admin-support/...
eslint completed successfully

cd frontend && npx tsc --noEmit --pretty false
completed successfully
```

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| Real staging Remnawave credential regeneration smoke | Open |
| Production low-risk admin/support smoke | Open |
| Local support widget UI/model proof | Closed locally by frontend tests |
| Local admin customer-detail integration | Closed locally in `68_STAGE1_ADM_007_CREDENTIAL_REGENERATION_ADMIN_EVIDENCE.md` |
| Deployed admin customer-detail screenshot or Playwright proof | Open; browser/persona proof still required before paid beta |
| Support runbook entry for regenerated credentials delivery | Open |
| Audit log screenshot/redacted DB row from staging | Open |

## Conclusion

`S1-VPN-008` is locally implemented as a backend/API and frontend support-widget contract. It closes the dangerous local parts of the task: role gate, required audit, safe logs, safe UI rendering and no raw config leakage. Real staging/prod Remnawave evidence, deployed admin-page evidence, support runbook evidence and staging audit-log evidence are still required before S1 go-live.
