# 113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE

Backlog ID: `S1-AUTH-001`
Status: completed locally; revalidated on 2026-05-08
Date: 2026-05-08
Scope: public registration/account-creation kill switch for Stage 1 Controlled Public Beta

## Decision

`REGISTRATION_ENABLED=false` must pause public creation of new accounts across the S1 B2C surface. Existing-account login must continue to work so support/admin can recover accounts, users can renew, and operators can avoid turning a registration freeze into a full auth outage.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-016`. The local contract remains valid: public new-account creation is fail-closed across web password, mobile password, magic link/OTP, OAuth, Telegram Mini App/Web, mobile Telegram/OIDC and Telegram Bot bootstrap paths while existing linked accounts can still log in. No deployed staging/production toggle evidence is implied by this local proof.

## Covered Channels

| Channel | Behavior while paused | Evidence |
|---|---|---|
| Web password registration `/api/v1/auth/register` | blocked with 403 before invite or account creation | existing security tests plus S1 regression |
| Mobile password registration `/api/v1/mobile/auth/register` | blocked before repository/device side effects | `test_stage1_registration_kill_switch.py` |
| Magic link / OTP auto-create | blocked with 403 before user creation | `test_stage1_registration_kill_switch.py` |
| Google/GitHub/OAuth new account auto-create | blocked before user/OAuth link/provisioning side effects | `test_stage1_registration_kill_switch.py` |
| Telegram Mini App / Web new account auto-create | blocked before user/provisioning side effects | `test_stage1_registration_kill_switch.py` |
| Mobile Telegram / Telegram OIDC new account auto-create | blocked before user/device side effects | `test_stage1_registration_kill_switch.py` |
| Telegram Bot bootstrap of new backend user | blocked for new user creation; existing Telegram users can still refresh profile/support state | source-level guard in `telegram/routes.py` |

## Local Implementation

Added shared guard:

- `backend/src/application/services/public_registration_policy.py`

Integrated into:

- `backend/src/application/use_cases/auth/oauth_login.py`
- `backend/src/application/use_cases/auth/telegram_miniapp.py`
- `backend/src/application/use_cases/auth/telegram_web_auth.py`
- `backend/src/application/use_cases/mobile_auth/register.py`
- `backend/src/application/use_cases/mobile_auth/telegram_auth.py`
- `backend/src/application/use_cases/mobile_auth/telegram_oidc_auth.py`
- `backend/src/presentation/api/v1/auth/registration.py`
- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/oauth/routes.py`
- `backend/src/presentation/api/v1/mobile_auth/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`

The public error code is:

```json
{
  "code": "REGISTRATION_DISABLED",
  "message": "Public registration is currently paused."
}
```

The response may include `channel` for support/operator diagnostics, but no raw email, Telegram ID, OAuth subject, token, invite token or provider credential is returned.

## Verification

Commands:

```bash
cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_registration_kill_switch.py tests/security/test_registration_security.py -q --no-cov
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_registration_kill_switch.py tests/security/test_registration_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/application/use_cases/auth/test_telegram_miniapp.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/unit/api/v1/test_oauth_magic_link.py tests/unit/api/v1/test_oauth_telegram_linking.py -q --no-cov
PYENV_VERSION=3.13.11 uv run ruff check src/application/services/public_registration_policy.py src/application/use_cases/auth/oauth_login.py src/application/use_cases/auth/telegram_miniapp.py src/application/use_cases/auth/telegram_web_auth.py src/application/use_cases/mobile_auth/register.py src/application/use_cases/mobile_auth/telegram_auth.py src/application/use_cases/mobile_auth/telegram_oidc_auth.py src/presentation/api/v1/auth/registration.py src/presentation/api/v1/auth/routes.py src/presentation/api/v1/oauth/routes.py src/presentation/api/v1/mobile_auth/routes.py src/presentation/api/v1/telegram/routes.py tests/security/test_stage1_registration_kill_switch.py tests/security/test_registration_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/application/use_cases/auth/test_telegram_miniapp.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/unit/api/v1/test_oauth_magic_link.py tests/unit/api/v1/test_oauth_telegram_linking.py
PYENV_VERSION=3.13.11 pip-audit --skip-editable backend
npm audit --omit=dev --audit-level=high
```

Results:

| Check | Result |
|---|---|
| Focused S1 registration/security suite | PASS: 16 passed |
| Auth regression suite | PASS: 83 passed |
| Ruff touched files | PASS |
| Backend runtime dependency audit | PASS: no known vulnerabilities found; local package `cybervpn-backend` skipped because it is not on PyPI |
| Root npm dependency audit | PASS for high/critical issues; one moderate `postcss` advisory remains through the current Next.js dependency path and `npm audit fix --force` proposes a breaking downgrade path |
| High-confidence secret scan over touched S1-AUTH-001 files | PASS: no matches |
| Dangerous-pattern scan over touched S1-AUTH-001 files | PASS: no matches |
| Docker/container usage | Not used; no containers started for this local/no-cost auth task |
| Stale next-step scan for `S1-AUTH-001` as current/next task | PASS: no stale current/next references in source docs after update |

## Documentation / Library References Used

| Reference | Use |
|---|---|
| <https://fastapi.tiangolo.com/tutorial/handling-errors/> | Rechecked FastAPI `HTTPException` handling pattern for controlled 4xx API errors |
| <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | Rechecked `monkeypatch` usage for per-test runtime settings and mocks |

## Remaining Go-Live Evidence

Local S1-AUTH-001 is complete. Before beta go-live, still capture deployed evidence:

1. Production/staging env snapshot showing intended `REGISTRATION_ENABLED` and `REGISTRATION_INVITE_REQUIRED` values.
2. Deployed HTTPS/API proof that `REGISTRATION_ENABLED=false` blocks every public new-account route with 403.
3. Deployed proof that existing users can still log in while registration is paused.
4. Operator runbook proof showing who can toggle registration and how rollback restores the previous value.
5. Alert/support note confirming registration freeze is visible to support/on-call.

## Acceptance

`S1-AUTH-001` is accepted locally because public new account creation can be paused safely without disabling existing account login.

Next ID to execute after `S1-AUTH-001`: `S1-AUTH-002` - email/login password flow.

## 2026-05-09 Ordered Batch Revalidation

`S1-AUTH-001` was re-run as item 8 in the owner-requested ordered batch.

Verification:

```text
cd backend
uv run pytest tests/security/test_stage1_registration_kill_switch.py tests/security/test_registration_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/application/use_cases/auth/test_telegram_miniapp.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/unit/api/v1/test_oauth_magic_link.py tests/unit/api/v1/test_oauth_telegram_linking.py -q --no-cov
Result: 83 passed in 0.55s

uv run ruff check tests/security/test_stage1_registration_kill_switch.py tests/security/test_registration_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/application/use_cases/auth/test_telegram_miniapp.py tests/unit/application/use_cases/mobile_auth/test_telegram_oidc_auth.py tests/unit/api/v1/test_oauth_magic_link.py tests/unit/api/v1/test_oauth_telegram_linking.py
Result: All checks passed
```

Local acceptance remains unchanged. Deployed proof for paused registration, existing-user login and operator toggle/runbook is still required before beta go-live.
