# 114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE

Backlog ID: `S1-AUTH-002`  
Status: completed locally; revalidated on 2026-05-08  
Date: 2026-05-08  
Scope: Stage 1 email/login password registration, verification, login, refresh and logout flow

## Decision

For S1 Controlled Public Beta, the web password flow is accepted only if it can prove this chain:

```text
register -> email OTP verification -> login by email or username -> refresh -> logout -> revoked refresh token rejected
```

Registration must not create an authenticated session until email verification succeeds. After verification/login, sessions must use refresh-token persistence, rotation/revocation and HTTP-only cookies.

Revalidated on 2026-05-08 as the active execution step after `S1-AUTH-001`. The local contract remains valid: register -> verify -> login by email/username -> refresh rotation -> logout/replay rejection works against local Docker-backed PostgreSQL/Valkey. This local proof does not imply deployed HTTPS/browser-cookie evidence or real email-provider evidence.

## Covered Behavior

| Area | Local proof |
|---|---|
| Registration pre-verification state | `/api/v1/auth/register` returns inactive/unverified user and no auth cookies |
| Unverified login denial | inactive/unverified email user is rejected before session creation |
| OTP verification | `/api/v1/auth/verify-otp` activates user, returns tokens and sets HTTP-only cookies |
| Email login | verified user can authenticate with email/password |
| Username login | verified user can authenticate with username/password |
| Session persistence | login stores refresh-token-backed session records |
| Refresh rotation | refresh returns a new refresh token and revokes the previous one |
| Logout | logout revokes refresh token and clears auth cookies |
| Replay prevention | revoked refresh token is rejected after logout |
| Cookie security | access/refresh cookies are `HttpOnly`, `Secure`, `SameSite=Lax`, scoped to `/api` and clear with `Max-Age=0` |

## Local Implementation

No production auth logic was changed for this task. The existing implementation already provided the required behavior through:

- `backend/src/presentation/api/v1/auth/registration.py`
- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/auth/cookies.py`
- `backend/src/application/use_cases/auth/login.py`
- `backend/src/application/use_cases/auth/verify_otp.py`
- `backend/src/application/use_cases/auth/refresh_token.py`
- `backend/src/application/use_cases/auth/logout.py`
- `backend/src/presentation/api/v1/auth/session_tokens.py`

Added focused Stage 1 coverage:

- `backend/tests/security/test_stage1_email_password_flow.py`

The new test file contains fast no-Docker security/unit checks plus a Docker-backed HTTP flow test against local PostgreSQL/Valkey.

## Verification

Docker access note:

- Docker Desktop was available from WSL through the Linux `docker` CLI.
- Only `remnawave-db` and `remnawave-redis` were started because this task needs PostgreSQL/Valkey; Remnawave API was mocked in the auth E2E path.
- The containers were intentionally left running after this task because `S1-AUTH-003` also needs local PostgreSQL/Valkey.

Commands:

```bash
docker compose -f infra/docker-compose.yml up -d remnawave-db remnawave-redis
docker ps --filter name=remnawave-db --filter name=remnawave-redis --format '{{.Names}}\t{{.Status}}'

cd backend
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_email_password_flow.py -q --no-cov
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_email_password_flow.py tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow::test_complete_registration_and_login_flow tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow::test_login_after_verification_flow -q --no-cov
PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_email_password_flow.py src/presentation/api/v1/auth/registration.py src/presentation/api/v1/auth/routes.py src/presentation/api/v1/auth/cookies.py src/application/use_cases/auth/login.py src/application/use_cases/auth/verify_otp.py src/application/use_cases/auth/refresh_token.py src/application/use_cases/auth/logout.py src/presentation/api/v1/auth/session_tokens.py

PYENV_VERSION=3.13.11 pip-audit --skip-editable backend
npm audit --omit=dev --audit-level=high
```

Results:

| Check | Result |
|---|---|
| S1-AUTH-002 focused suite | PASS: 5 passed in 0.88s |
| Focused S1 + existing auth integration regression | PASS: 7 passed in 1.17s |
| Ruff touched auth flow files | PASS: all checks passed |
| Backend runtime dependency audit | PASS: no known vulnerabilities found |
| Root npm production dependency audit at high threshold | PASS for high/critical: exit 0; residual moderate `postcss <8.5.10` via `next`, fix currently suggests breaking `npm audit fix --force` |
| High-confidence secret scan over touched S1-AUTH-002 files | PASS: no matches |
| Dangerous-pattern scan over touched S1-AUTH-002 files | PASS: no matches |
| Local DB/Valkey containers | PASS: `remnawave-db` and `remnawave-redis` healthy and kept running for `S1-AUTH-003` |
| Remnawave side effect | Mocked for auth flow; real Remnawave provisioning remains covered by VPN/provisioning tasks |

## Documentation / Library References Used

| Reference | Use |
|---|---|
| <https://fastapi.tiangolo.com/tutorial/testing/> | Confirmed FastAPI test pattern with HTTPX-backed clients and pytest |
| <https://fastapi.tiangolo.com/advanced/response-cookies/> | Confirmed response cookie handling through FastAPI `Response` |
| <https://www.python-httpx.org/advanced/clients/> | Confirmed client cookie persistence behavior for request flows |
| <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | Confirmed `monkeypatch` usage for isolated settings/cookie assertions |

## Remaining Go-Live Evidence

Local S1-AUTH-002 is complete. Before beta go-live, still capture deployed evidence:

1. Deployed HTTPS proof that `register -> verify -> login -> refresh -> logout` works on the S1 domain.
2. Browser proof that auth cookies are `HttpOnly`, `Secure`, `SameSite=Lax` and scoped to approved domains/paths.
3. Deployed proof that unverified users cannot log in before email verification.
4. Deployed proof that revoked refresh tokens cannot be reused after logout.
5. Real email provider or local-mail-equivalent evidence for OTP delivery belongs to `S1-AUTH-003`.
6. Real Remnawave provisioning after trial/payment remains covered by VPN/provisioning tasks, not by this auth-only task.

## Acceptance

`S1-AUTH-002` is accepted locally because the email/password flow has focused unit/security coverage and Docker-backed HTTP E2E proof for registration, OTP activation, login, refresh rotation, logout and session-cookie security.

Next ID to execute after `S1-AUTH-002`: `S1-AUTH-003` - magic link/OTP.

## 2026-05-09 Ordered Batch Revalidation

`S1-AUTH-002` was re-run as item 9 in the owner-requested ordered batch.

Local runtime:

| Service | Result |
|---|---|
| `remnawave-db` | Started through `docker compose -f infra/docker-compose.yml up -d remnawave-db remnawave-redis` |
| `remnawave-redis` | Started for Redis-backed auth/session/rate-limit fixtures |
| Cleanup | Both containers were stopped after `S1-AUTH-003` because this ordered package ended there |

Verification:

```text
cd backend
uv run pytest tests/security/test_stage1_email_password_flow.py -q --no-cov
Result: 5 passed in 0.89s

uv run pytest tests/security/test_stage1_email_password_flow.py tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow::test_complete_registration_and_login_flow tests/integration/api/v1/auth/test_auth_flows.py::TestCompleteAuthFlow::test_login_after_verification_flow -q --no-cov
Result: 7 passed in 1.12s

uv run ruff check tests/security/test_stage1_email_password_flow.py src/presentation/api/v1/auth/registration.py src/presentation/api/v1/auth/routes.py src/presentation/api/v1/auth/cookies.py src/application/use_cases/auth/login.py src/application/use_cases/auth/verify_otp.py src/application/use_cases/auth/refresh_token.py src/application/use_cases/auth/logout.py src/presentation/api/v1/auth/session_tokens.py
Result: All checks passed
```

Local acceptance remains unchanged. Deployed HTTPS/browser cookie proof and real email-provider proof are still required before go-live.
