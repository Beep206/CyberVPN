# Passkey/WebAuthn API contract handoff

Дата: 2026-06-03
Issue: [CYBA-389](/CYBA/issues/CYBA-389)

## Исполнительное резюме

Backend expose passkey/WebAuthn core ceremonies, persisted admin policy/compliance
surfaces и partner workspace policy/compliance surfaces. Raw browser credential
payloads, challenges, credential public keys and full credential IDs are not
returned by compliance endpoints.

## OpenAPI paths

- `GET /api/v1/auth/passkeys/policy`
- `POST /api/v1/auth/passkeys/registration/options`
- `POST /api/v1/auth/passkeys/registration/verify`
- `POST /api/v1/auth/passkeys/authentication/options`
- `POST /api/v1/auth/passkeys/authentication/verify`
- `GET /api/v1/auth/passkeys`
- `PATCH /api/v1/auth/passkeys/{credential_id}`
- `DELETE /api/v1/auth/passkeys/{credential_id}`
- `POST /api/v1/auth/passkeys/reauthentication/options`
- `POST /api/v1/auth/passkeys/reauthentication/verify`
- `GET /api/v1/security/passkeys/policy`
- `PATCH /api/v1/security/passkeys/policy`
- `GET /api/v1/security/passkeys/compliance`
- `GET /api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy`
- `PATCH /api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy`
- `GET /api/v1/partner-workspaces/{workspace_id}/security/passkeys/compliance`

## Контракты

- `PasskeyPolicyResponse`: capability/policy source for UI surfaces.
- `PasskeyOptionsResponse`: WebAuthn `publicKey`, `challengeId`, expiry.
- `PasskeyCredentialResponse`: authenticated user's sanitized passkey metadata.
- `PasskeyComplianceResponse`: admin realm policy, summary and sanitized rows.
- `UpdateAdminPasskeyPolicyRequest`: persisted admin passkey runtime controls
  for enabled state, ceremony gates, WebAuthn timeout/TTL, reauth TTL,
  dashboard visibility and `adminCountsAsMfa`.
- `PartnerWorkspacePasskeyPolicyResponse`: workspace policy and operator posture.
- `PartnerWorkspacePasskeyComplianceResponse`: workspace policy, operator posture,
  summary and sanitized rows.
- `UpdatePartnerWorkspacePasskeyPolicyRequest`: workspace-owned passkey
  preference and workspace MFA requirement controls.

## Policy storage and enforcement

- Admin policy is stored under `system_config` key `passkeys.admin_policy`.
- Admin policy is an overlay on environment feature gates. If
  `PASSKEY_ENABLED=false` or `PASSKEY_ADMIN_ENABLED=false`, PATCH can store the
  desired policy but effective admin passkeys remain disabled.
- Effective admin policy is used by `/auth/passkeys/policy`,
  registration/authentication/reauthentication option and verify gates,
  challenge TTL, browser timeout, fresh-auth TTL and credential policy snapshots.
- Partner workspace policy uses the existing `partner_workspace_profiles`
  fields `prefer_passkeys` and `require_mfa_for_workspace`. Writes are accepted
  only through the dedicated passkey policy endpoint.
- Admin and partner policy updates create `audit_logs` rows. No raw credential,
  challenge or public-key material is written to audit payloads.

## Hardening delta 2026-06-04

Issue: [CYBA-435](/CYBA/issues/CYBA-435)

- WebAuthn challenge consume is one-time and atomic across supported Redis
  clients: native `getdel`, `execute_command("GETDEL", key)`, then Lua fallback.
  If no atomic consume path is available, verification fails closed.
- `GET /auth/passkeys`, `PATCH /auth/passkeys/{credential_id}` and
  `DELETE /auth/passkeys/{credential_id}` now honor the effective passkey
  global/surface/admin policy before reading or mutating credentials. Grants
  issued before a kill switch do not bypass disabled policy.
- Authentication and reauthentication verify compare browser-supplied
  `response.userHandle` to the stored credential `user_handle` when the browser
  supplies a non-null handle. Missing handles remain accepted for browser and
  authenticator compatibility.
- Partner workspace passkey policy/compliance endpoints are partner web realm
  endpoints. Internal admin override is not accepted on those endpoints; an
  admin override requires a separate Board/CTO-approved route and action string.
- `adminCountsAsMfa=true` is rejected by admin policy PATCH until passkey-as-MFA
  enforcement is implemented and approved. The backend keeps fail-secure TOTP
  behavior instead of exposing a misleading policy state.

## Hardening delta 2026-06-04 CYBA-447

- `PATCH /api/v1/partner-workspaces/{workspace_id}/settings` rejects
  `prefer_passkeys`, `preferPasskeys`, `require_mfa_for_workspace` and
  `requireMfaForWorkspace` with validation guidance to use
  `/api/v1/partner-workspaces/{workspace_id}/security/passkeys/policy`.
- The settings endpoint no longer mutates passkey policy fields under
  `partner.settings.security.update:{workspaceId}`. Mixed payloads containing
  normal settings plus passkey policy fields fail closed before profile writes.

## Generated contracts

`backend/scripts/export_openapi.py` was run and confirmed the passkey paths are
present in `backend/docs/api/openapi.json`. Frontend/admin/partner
`generated/types.ts` and `SDK/python-sdk-production` were not manually edited;
they should be regenerated by the normal OpenAPI client generation owner after
the branch's combined backend OpenAPI export is accepted.

## Миграция и rollback

- Alembic revision: `20260603_passkey_credentials`.
- Down revision: `20260531_messaging_core`.
- Data safety: migration creates `passkey_credentials`; it does not read or
  transform existing customer/payment/VPN provisioning data.
- Rollback: downgrade drops passkey indexes and `passkey_credentials`, removing
  enrolled passkey metadata/public keys for that environment. Rollback must be
  coordinated before enabling passkeys for real users.

## Проверка

- `REMNAWAVE_TOKEN=test-remnawave JWT_SECRET=<synthetic-jwt-secret> CRYPTOBOT_TOKEN=test-cryptobot uv run pytest tests/unit/test_passkey_challenges.py tests/unit/test_passkey_fresh_auth.py -q --no-cov`
- `REMNAWAVE_TOKEN=test-remnawave JWT_SECRET=<synthetic-jwt-secret> CRYPTOBOT_TOKEN=test-cryptobot uv run pytest tests/integration/test_passkey_webauthn_api.py -q --no-cov`
- `REMNAWAVE_TOKEN=test-remnawave JWT_SECRET=<synthetic-jwt-secret> CRYPTOBOT_TOKEN=test-cryptobot uv run pytest tests/contract/test_passkey_openapi_contract.py -q --no-cov`
- `uv run pytest tests/integration/test_passkey_webauthn_api.py tests/contract/test_passkey_openapi_contract.py -q --no-cov`
- `uv run ruff check <targeted passkey backend files>`
- `uv run python -m compileall -q <targeted passkey backend files>`
- `uv run python -m py_compile alembic/versions/20260603_passkey_credentials.py`
- `uv run alembic heads`
- `uv run python scripts/export_openapi.py`

## Documentation evidence

Context7 docs checked: Context7 quota exceeded; fallback primary/vendor docs
and local `webauthn==2.7.1` wheel API inspection were used.
