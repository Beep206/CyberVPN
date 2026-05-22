# S2-STAGE-05 Evidence: Auth And Registration Public Readiness

**Date:** 2026-05-22
**Stage:** `S2-STAGE-05`
**Status:** Passed targeted local evidence

---

## 1. Scope

This evidence covers the S2 public auth and registration readiness gate:

1. approved auth methods are documented;
2. gradual public registration posture is documented;
3. registration/login/Telegram/magic-link/OAuth/invite redemption rate-limit coverage is verified;
4. production OAuth cannot be half-enabled without credentials;
5. account deletion and privacy request paths are confirmed;
6. admin 2FA/bootstrap guardrails remain part of the S2 contract.

---

## 2. Code Changes Verified

Changed backend configuration and rate-limit guardrails:

```text
backend/src/config/settings.py
backend/src/presentation/middleware/rate_limit.py
backend/.env.example
```

Added or updated tests:

```text
backend/tests/security/test_rate_limiter.py
backend/tests/unit/config/test_settings.py
backend/tests/security/test_stage1_cryptobot_sandbox_runtime.py
backend/tests/security/test_stage1_cors_cookie_config.py
backend/tests/security/test_stage1_csrf_protection.py
backend/tests/security/test_stage1_swagger_public_off.py
backend/tests/security/test_stage1_admin_access_protection.py
```

Added contract document:

```text
docs/cybervpn_stage2_launch_docs/04_STAGE2_AUTH_REGISTRATION_PUBLIC_READINESS.md
```

---

## 3. Auth Contract Outcome

| Area | Result |
|---|---|
| Email/password | Approved for S2 canary/open registration |
| Telegram identity/linking | Approved under registration policy |
| Magic link/OTP | Approved with rate limits |
| Google OAuth | Conditional: only with production credentials and callback evidence |
| GitHub OAuth | Conditional: only with production credentials and callback evidence |
| Other OAuth providers | Not approved for public S2 login |
| Public signup posture | Gradual: smoke -> invite canary -> open public signup |

Recommended runtime before payment hardening:

```text
REGISTRATION_ENABLED=false
REGISTRATION_INVITE_REQUIRED=true
OAUTH_ENABLED_LOGIN_PROVIDERS=
```

---

## 4. Rate Limit Coverage Outcome

| Endpoint/surface | Result |
|---|---|
| `POST /api/v1/auth/login` | `s1_auth_sensitive` |
| `POST /api/v1/auth/register` | `s1_auth_sensitive` |
| `POST /api/v1/auth/magic-link/verify-otp` | `s1_auth_sensitive` |
| `POST /api/v1/auth/telegram/miniapp` | `s1_auth_sensitive` |
| `POST /api/v1/oauth/google/login/callback` | `s1_auth_sensitive` |
| `POST /api/v1/oauth/github/login/callback` | `s1_auth_sensitive` |
| `POST /api/v1/invites/redeem` | `s1_growth_sensitive` |

---

## 5. Backend Lint

Command:

```bash
cd backend
uv run ruff check src/config/settings.py src/presentation/middleware/rate_limit.py tests/security/test_rate_limiter.py tests/unit/config/test_settings.py
```

Result:

```text
All checks passed!
```

---

## 6. Backend Targeted Tests

Command:

```bash
cd backend
SWAGGER_ENABLED=false uv run pytest tests/security/test_rate_limiter.py tests/unit/config/test_settings.py tests/security/test_stage1_cryptobot_sandbox_runtime.py tests/security/test_stage1_admin_access_protection.py tests/security/test_stage1_cors_cookie_config.py tests/security/test_stage1_csrf_protection.py tests/security/test_stage1_swagger_public_off.py tests/security/test_stage1_oauth_provider_scope.py tests/security/test_registration_security.py -q --no-cov
```

Result:

```text
121 passed in 17.69s
```

Note: `SWAGGER_ENABLED=false` is supplied explicitly because the repository includes production docs-off checks and local developer environments may carry unrelated Swagger flags. Production still forces public docs off regardless of `SWAGGER_ENABLED=true`.

---

## 7. Reviewed User Rights Paths

| Capability | Path | Result |
|---|---|---|
| Web/account delete | `DELETE /api/v1/auth/me` | Exists and revokes sessions/tokens |
| Customer/mobile delete | `DELETE /api/v1/mobile/auth/me` | Exists and revokes VPN access through backend flow |
| Privacy request | `POST /api/v1/auth/me/privacy-requests` | Exists for manual `account_deletion` / `data_export` support handling |

---

## 8. Auth Integration Subset

Local prerequisites used for this run:

```bash
cd infra
docker compose up -d remnawave-db remnawave-redis
docker exec remnawave-redis valkey-cli FLUSHALL
```

Command:

```bash
cd backend
RATE_LIMIT_AUTH_SENSITIVE_REQUESTS=1000 SWAGGER_ENABLED=false uv run pytest tests/security/test_stage1_magic_link_otp_flow.py tests/security/test_stage1_admin_2fa_enforcement.py tests/security/test_stage1_registration_kill_switch.py tests/integration/api/v1/auth/test_magic_link.py tests/integration/api/v1/auth/test_register.py tests/integration/api/v1/oauth/test_oauth_login.py -q --no-cov
```

Result:

```text
40 passed in 1.17s
```

Notes:

1. `RATE_LIMIT_AUTH_SENSITIVE_REQUESTS=1000` was used only for this test batch because the suite performs many same-client auth requests in one process and would otherwise intentionally exhaust the production-like auth bucket.
2. The dedicated rate-limit coverage test still proves the production S2 auth-sensitive bucket assignments.
3. Local Docker services were started only for this integration subset and must be stopped after the evidence run.

---

## 9. Security Sweep

| Check | Result |
|---|---|
| `git diff --check` | Passed |
| `npm audit --audit-level=high` | Passed high/critical gate; residual moderate findings only |
| Backend `uvx pip-audit --progress-spinner off --skip-editable .` | Passed |
| Targeted secret scan on changed files | No real secrets; only static test constants in `test_settings.py` |
| Targeted dangerous-pattern scan on changed files | Only existing subprocess-based fresh-import proof tests with `# noqa: S603` |

---

## 10. Residual Risks

| Risk | Handling |
|---|---|
| Public signup can still create abuse if opened before payment/provisioning gates | Keep registration disabled or invite-only until later S2 gate |
| OAuth production credentials are not proven here | Enable `google`/`github` only after credential/callback smoke evidence |
| Data export remains manual | Acceptable for S2 if public policy/support process stays accurate |
| Bucket names still include `s1_` | Operationally acceptable; names are launch-era internal controls, not customer-facing API |

---

## 11. Exit Decision

`S2-STAGE-05` passes targeted local readiness.

Next stage:

```text
S2-STAGE-06: Payment Production Hardening
```
